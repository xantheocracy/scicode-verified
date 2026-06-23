#!/usr/bin/env python3
"""Evaluate DeepSeek V4 Pro Max and Flash Max on the CLEANED SciCode test set.

Runs exactly the four target configurations:
    {Pro Max, Flash Max}  x  {without background, with background}
faithful to the official SciCode prompt + cumulative scoring, scored against the cleaned h5.

"Pro Max" / "Flash Max" = models deepseek-v4-pro / deepseek-v4-flash at reasoning_effort="max"
(both verified against the live API; valid efforts are low|medium|high|max|xhigh).

Setup:
    export DEEPSEEK_API_KEY=sk-...
    python3 eval_clean/run_deepseek_eval.py
    # quick check first:   python3 eval_clean/run_deepseek_eval.py --only 58,73,22

Multi-version OR grading (robust to numpy/scipy API drift):
    Grading is output-based (np.allclose to gold), so a step's verdict shouldn't depend on
    which library version happens to expose the function name the model called (scipy 1.14
    dropped integrate.simps->simpson, cumtrapz->cumulative_trapezoid; numpy 2.0 dropped
    np.trapz->trapezoid). Pass --envs to grade each saved step under several pinned envs and
    PASS if it's correct in ANY of them (the OR) -- API-era-agnostic, no false passes:
        python3 eval_clean/run_deepseek_eval.py --run run4 \
            --envs 2024:/path/envs/sci2024/bin/python 2025:/path/envs/cp312/bin/python
    Short-circuits on the first passing env; add --full-envs for the per-env breakdown.
    Each <step>.score.json records {"passed", "per_env": {label: bool}}.
"""
import os, sys, json, re, subprocess, argparse, time, collections
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ===================== the two target configs (verified vs the live API) =====================
# The DeepSeek API exposes exactly two models: deepseek-v4-pro and deepseek-v4-flash.
# "Pro Max" / "Flash Max" = those models run at reasoning_effort="max"
# (valid efforts: low | medium | high | max | xhigh).
PRO_MAX   = "deepseek-v4-pro"       # "DeepSeek V4 Pro Max"
FLASH_MAX = "deepseek-v4-flash"     # "DeepSeek Flash Max"
REASONING_EFFORT = "max"            # the "Max" in both names
# Providers expose the SAME deepseek-v4-{pro,flash} and BOTH accept reasoning_effort=max,
# so the only difference is endpoint + key -> fair apples-to-apples ("降智") comparison.
PROVIDERS = {
    "deepseek": ("https://api.deepseek.com", "DEEPSEEK_API_KEY"),                                  # 官方
    "ali":      (os.environ.get("ALI_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"), "ALI_API_KEY"),  # 阿里云 DashScope
}
PROVIDER = "deepseek"               # overridden by --provider
BASE_URL, KEY_ENV = PROVIDERS[PROVIDER]
# =============================================================================================

MAX_TOKENS = None      # per-call output cap; None = API default. Set via --max-tokens.
VERBOSE_STEPS = False   # print one line per sub-step (default: only per-problem). Set via --verbose-steps.

# Multi-ENVIRONMENT OR grading (pass-if-any across library versions). Default: a single env =
# the current interpreter. Set multiple via --envs to make grading robust to numpy/scipy API
# drift (simps->simpson, trapz->trapezoid, interp2d removal, ...): a step PASSES if its saved
# code is correct in ANY listed env. Output-based (np.allclose to gold) so accepting a renamed-
# but-identical API is safe (no false passes). Short-circuits on the first passing env unless
# --full-envs (breakdown mode runs them all).
GRADING_ENVS = None    # list[(label, python_path)]; set in main()
FULL_ENVS = False      # run every env per step even after one passes (breakdown). Set via --full-envs.
# Thread caps so many parallel grading subprocesses don't oversubscribe the box via BLAS.
SUBENV = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
          "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"}

ROOT = Path(__file__).resolve().parent.parent
SRC  = ROOT / "SciCode" / "src"
H5   = str(ROOT / "scicode_verified" / "test_data_cleaned.h5")   # verified cleaned dataset
DATA = ROOT / "scicode_verified" / "problems_test.jsonl"
MANIFEST = ROOT / "scicode_verified" / "manifest.json"

def _check_manifest():
    """Refuse to run on stale data: assert jsonl/h5 md5 == manifest (verify-with-human
    invariant 5). Set ALLOW_UNVERIFIED_DATA=1 to bypass (not recommended)."""
    import hashlib, json as _json
    if os.environ.get("ALLOW_UNVERIFIED_DATA") == "1":
        print("WARNING: skipping manifest data check (ALLOW_UNVERIFIED_DATA=1)"); return
    if not MANIFEST.exists():
        sys.exit(f"FATAL: {MANIFEST} missing — run tools/assemble.py to generate it.")
    man = _json.loads(MANIFEST.read_text())
    def md5f(p):
        h = hashlib.md5()
        with open(p, "rb") as f:
            for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
        return h.hexdigest()
    if md5f(DATA) != man.get("problems_test_jsonl_md5"):
        sys.exit(f"FATAL: {DATA} md5 != manifest — data is stale/edited. Run tools/assemble.py + tools/verify.py.")
    if man.get("h5_md5") and os.path.exists(H5) and md5f(H5) != man["h5_md5"]:
        sys.exit(f"FATAL: {H5} md5 != manifest — h5 is stale. Rebuild via eval_clean/build_clean_h5.py.")
    print(f"manifest OK: dataset {man.get('version')} ({man.get('n_problems')} problems), data md5 verified.")
# Match the OFFICIAL SciCode harness: WITH background -> multistep_template (background is provided);
# WITHOUT background -> background_comment_template (the model must first generate the scientific
# background as a '# Background: ' comment, then code). Selected per-config in build_prompt.
TEMPLATE_BG   = (ROOT / "SciCode" / "eval" / "data" / "multistep_template.txt").read_text()
TEMPLATE_NOBG = (ROOT / "SciCode" / "eval" / "data" / "background_comment_template.txt").read_text()
SKIP = {("13", 5), ("62", 0), ("76", 2)}   # steps the official harness skips

def extract_code(resp):
    if not resp: return ""
    if "```" in resp:
        s = resp.split("```python")[1].split("```")[0] if "```python" in resp else resp.split("```")[1].split("```")[0]
    else:
        s = resp
    return re.sub(r"^\s*(import .*|from .*\s+import\s+.*)", "", s, flags=re.MULTILINE)

def build_prompt(prob, k, prev_codes, with_bg):
    # DELIBERATE deviation from the official harness: it trims each previous step's code to the
    # last 120 lines (whole section <=18000 chars) to fit context; we include the FULL previous
    # code. On long (many-step) problems that trimming can cut off correct prior code the next
    # step must call -> unfair. deepseek-v4's context easily holds the full prior code, so we keep
    # it complete. (Cost: our long-problem prompts aren't byte-identical to the official harness's.)
    lines = []
    for i in range(k):
        sp = prob["sub_steps"][i]["step_description_prompt"]
        if with_bg: sp += "\n" + prob["sub_steps"][i]["step_background"]
        lines += [sp, prev_codes[i], "------"]
    cur = prob["sub_steps"][k]
    nsp = cur["step_description_prompt"] + ("\n" + cur["step_background"] if with_bg else "")
    template = TEMPLATE_BG if with_bg else TEMPLATE_NOBG
    return template.format(problem_steps_str="\n\n".join(lines[:-1]) if lines else "",
                           next_step_str=f"{nsp}\n\n{cur['function_header']}\n\n{cur['return_line']}",
                           dependencies=prob["required_dependencies"])

def gen(client, prompt, model, retries=8):
    # STREAMING: reasoning/content tokens flow incrementally so the TCP connection is never
    # idle -> stateful middleboxes (NAT/LB) can't silently reap it mid-think (the dead-socket hang).
    extra = {} if MAX_TOKENS is None else {"max_tokens": MAX_TOKENS}
    for a in range(retries):
        try:
            stream = client.chat.completions.create(
                model=model, reasoning_effort=REASONING_EFFORT, timeout=1800,
                messages=[{"role": "user", "content": prompt}],
                stream=True, stream_options={"include_usage": True}, **extra)
            content, reasoning, usage, finish = [], [], None, None
            for chunk in stream:
                if getattr(chunk, "usage", None): usage = chunk.usage.model_dump()
                if not chunk.choices: continue
                d = chunk.choices[0].delta
                if getattr(d, "content", None): content.append(d.content)
                rc = getattr(d, "reasoning_content", None)
                if rc: reasoning.append(rc)
                if chunk.choices[0].finish_reason: finish = chunk.choices[0].finish_reason
            return {"content": "".join(content),
                    "reasoning_content": "".join(reasoning) or None,
                    "finish_reason": finish, "usage": usage}
        except Exception as e:
            if a == retries - 1: raise
            s = str(e).lower()
            is_rate = "429" in s or "rate" in s or "limit" in s or type(e).__name__ == "RateLimitError"
            time.sleep(min(90, (12 if is_rate else 3) * (2 ** a)))   # exp backoff; longer on rate-limit

def _run_script(py, path):
    try:
        p = subprocess.run([py, str(path)], capture_output=True, text=True,
                           timeout=1800, env=SUBENV)   # match official SciCode per-step timeout
        return p.returncode == 0
    except subprocess.TimeoutExpired:
        return False

def score_step(cumcode, test_cases, step_id, tmpdir, envs):
    """Grade the cumulative step under each env in `envs`; PASS if ANY env passes (the OR).
    Short-circuits on the first passing env unless FULL_ENVS (breakdown mode runs them all).
    Returns {"passed": bool, "per_env": {label: bool}} — per_env holds only the envs run."""
    script = [cumcode, "", f"import sys; sys.path.insert(0, r'{SRC.as_posix()}')",
              "from scicode.parse.parse import process_hdf5_to_tuple",
              f"targets = process_hdf5_to_tuple('{step_id}', {len(test_cases)}, r'{H5}')"]
    for i, tc in enumerate(test_cases):
        script += [f"target = targets[{i}]", tc]
    f = tmpdir / f".score_{step_id}_{time.time_ns()}.py"; f.write_text("\n".join(script))
    per_env = {}
    try:
        for label, py in envs:
            per_env[label] = _run_script(py, f)
            if per_env[label] and not FULL_ENVS:
                break   # OR short-circuit: one passing env is enough
    finally:
        f.unlink(missing_ok=True)
    return {"passed": any(per_env.values()), "per_env": per_env}

def run_problem(prob, client, model, with_bg, outdir):
    pid = str(prob["problem_id"]); cdir = outdir / pid; cdir.mkdir(parents=True, exist_ok=True)
    prev, cum, steps = [], prob["required_dependencies"], {}
    for k, sub in enumerate(prob["sub_steps"]):
        sid = sub["step_number"]; cf = cdir / f"{sid}.code.py"
        if (pid, k) in SKIP:
            # Match official harness: these steps (13.6/62.1/76.3) are NEVER generated or scored.
            # Inject the GOLD reference code (SciCode/eval/data/<sid>.txt) so downstream cumulative
            # code builds on the correct version, not a model guess.
            gold = (ROOT / "SciCode" / "eval" / "data" / f"{sid}.txt").read_text()
            code = re.sub(r"^\s*(import .*|from .*\s+import\s+.*)", "", gold, flags=re.MULTILINE)
            cf.write_text(code)
            prev.append(code); cum += "\n\n" + code
            steps[sid] = None
            if VERBOSE_STEPS:
                print(f"    {sid} ({k+1}/{len(prob['sub_steps'])}): gold (not generated, not scored)", flush=True)
            continue
        if cf.exists():
            code = cf.read_text()
        else:
            prompt = build_prompt(prob, k, prev, with_bg)
            resp = gen(client, prompt, model)
            code = extract_code(resp["content"])
            cf.write_text(code)
            # full generation trajectory for inspection / re-scoring
            (cdir / f"{sid}.raw.json").write_text(json.dumps({
                "step_id": sid, "model": model, "with_background": with_bg,
                "reasoning_effort": REASONING_EFFORT, "prompt": prompt,
                "response": resp["content"], "reasoning_content": resp["reasoning_content"],
                "finish_reason": resp["finish_reason"], "usage": resp["usage"],
                "extracted_code": code}, indent=2, ensure_ascii=False))
        prev.append(code); cum += "\n\n" + code
        sf = cdir / f"{sid}.score.json"   # cache the verdict so resume skips re-scoring already-done steps
        if sf.exists():
            cached = json.loads(sf.read_text())
            steps[sid] = cached.get("passed")
            # Multi-env resume (new-format caches only): a cached FAIL might pass under a grading
            # env added since it was scored. Grade ONLY the not-yet-tried envs and merge — OR is
            # monotonic, so a cached PASS (or a legacy cache without per_env) is reused as-is.
            if "per_env" in cached and steps[sid] is False:
                missing = [(l, p) for (l, p) in GRADING_ENVS if l not in cached["per_env"]]
                if missing:
                    res = score_step(cum, sub["test_cases"], sid, cdir, missing)
                    pe = {**cached["per_env"], **res["per_env"]}
                    steps[sid] = any(pe.values())
                    sf.write_text(json.dumps({"step_id": sid, "passed": steps[sid], "per_env": pe}))
        else:
            res = score_step(cum, sub["test_cases"], sid, cdir, GRADING_ENVS)
            steps[sid] = res["passed"]
            sf.write_text(json.dumps({"step_id": sid, "passed": steps[sid], "per_env": res["per_env"]}))
        if VERBOSE_STEPS:
            mark = "ok" if steps[sid] else "X"
            print(f"    {sid} ({k+1}/{len(prob['sub_steps'])}): {mark}", flush=True)
    scored = [ok for ok in steps.values() if ok is not None]
    return {"problem_id": pid, "steps": steps, "n_steps_scored": len(scored),
            "n_steps_ok": sum(scored), "problem_correct": bool(scored) and all(scored)}

def run_config(model, with_bg, probs, workers, run_tag):
    from openai import OpenAI
    key = os.environ.get(KEY_ENV)
    if not key: sys.exit(f"set {KEY_ENV}")
    client = OpenAI(api_key=key, base_url=BASE_URL)
    outdir = ROOT / "eval_clean" / "ds_runs" / run_tag / f"cleaned_{model}" / ("with_bg" if with_bg else "no_bg")
    outdir.mkdir(parents=True, exist_ok=True)
    label = f"[{run_tag}] {PROVIDER}:{model} {'WITH' if with_bg else 'WITHOUT'} background"
    print(f"\n=== {label} : {len(probs)} problems ===")
    results = []; total = len(probs)
    # LPT scheduling: submit longest problems first so the big ones overlap with the many short
    # ones instead of becoming a serial tail at the end (single problem can't be split across workers).
    order = sorted(probs, key=lambda p: -len(p["sub_steps"]))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(run_problem, p, client, model, with_bg, outdir): p for p in order}
        for done, fu in enumerate(as_completed(futs), 1):
            p = futs[fu]
            try:
                r = fu.result()
            except Exception as e:
                print(f"  [{done}/{total}] prob {p['problem_id']}: ERROR {type(e).__name__}: {str(e)[:100]}", flush=True)
                continue
            results.append(r)
            so = sum(x["n_steps_ok"] for x in results); st = sum(x["n_steps_scored"] for x in results)
            po = sum(x["problem_correct"] for x in results)
            print(f"  [{done}/{total}] prob {r['problem_id']:>3}: {r['n_steps_ok']}/{r['n_steps_scored']} steps "
                  f"{'OK' if r['problem_correct'] else 'x '}  | running: {po}/{len(results)} probs solved, "
                  f"{so}/{st} steps {round(100*so/st) if st else 0}%", flush=True)
    if FULL_ENVS and len(GRADING_ENVS) > 1:   # per-env breakdown (only complete when all envs run)
        labels = [l for l, _ in GRADING_ENVS]
        env_ok = {l: 0 for l in labels}; tot = 0; or_ok = 0; combo = collections.Counter()
        for r in results:
            for sfp in (outdir / r["problem_id"]).glob("*.score.json"):
                pe = json.loads(sfp.read_text()).get("per_env") or {}
                if not pe: continue
                tot += 1
                if any(pe.values()): or_ok += 1
                for l in labels:
                    if pe.get(l): env_ok[l] += 1
                combo[frozenset(l for l in labels if pe.get(l))] += 1
        if tot:
            print(f"  --- per-env step breakdown ({label}) ---")
            for l in labels:
                print(f"    env {l:>10}: {env_ok[l]}/{tot} = {100*env_ok[l]/tot:.1f}%")
            print(f"    OR(any)    : {or_ok}/{tot} = {100*or_ok/tot:.1f}%")
            for s, c in sorted(combo.items(), key=lambda kv: -kv[1]):
                print(f"      passed-in[{'+'.join(sorted(s)) if s else 'NONE'}]: {c}")
    ts = sum(r["n_steps_scored"] for r in results); to = sum(r["n_steps_ok"] for r in results)
    po = sum(r["problem_correct"] for r in results)
    summary = {"run_tag": run_tag, "model": model, "with_background": with_bg,
               "reasoning_effort": REASONING_EFFORT, "max_tokens": MAX_TOKENS,
               "problems": len(results), "problems_correct": po, "steps_total": ts,
               "steps_correct": to, "step_accuracy": round(to / ts, 4) if ts else 0,
               "problem_accuracy": round(po / len(results), 4) if results else 0}
    (outdir / "results.json").write_text(json.dumps({"summary": summary,
        "results": sorted(results, key=lambda r: int(r["problem_id"]))}, indent=2))
    return summary

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma-separated problem ids for a quick check")
    ap.add_argument("--workers", type=int, default=4, help="problems run in parallel within a config")
    ap.add_argument("--model", choices=["pro", "flash"], default=None,
                    help="only this model (default: both)")
    ap.add_argument("--background", choices=["on", "off"], default=None,
                    help="only with/without background (default: both)")
    ap.add_argument("--run", default="run1",
                    help="run tag -> ds_runs/<run>/... ; SAME tag resumes & reuses cached gens, "
                         "use a NEW tag for an independent repeat run (no overwrite)")
    ap.add_argument("--max-tokens", type=int, default=None, help="per-call output cap (default: API default)")
    ap.add_argument("--verbose-steps", action="store_true",
                    help="also print one line per sub-step (default: only per-problem progress)")
    ap.add_argument("--provider", choices=list(PROVIDERS), default="deepseek",
                    help="API endpoint: deepseek (official) or ali (DashScope). Same model+effort, different endpoint.")
    ap.add_argument("--envs", nargs="+", default=None,
                    help="multi-version OR grading: space-separated 'label:python_path' envs. A step "
                         "PASSES if its code is correct in ANY env -> robust to numpy/scipy API drift. "
                         "Default: a single env = the current interpreter. e.g. --envs "
                         "2024:/opt/conda/envs/sci2024/bin/python 2025:/opt/conda/envs/cp312/bin/python")
    ap.add_argument("--full-envs", action="store_true",
                    help="grade under EVERY --envs env per step (no short-circuit) and print a per-env "
                         "breakdown; default stops at the first passing env (faster).")
    a = ap.parse_args()
    _check_manifest()   # refuse to run on stale/edited data (verify-with-human invariant 5)
    global MAX_TOKENS, VERBOSE_STEPS, PROVIDER, BASE_URL, KEY_ENV, GRADING_ENVS, FULL_ENVS
    MAX_TOKENS = a.max_tokens
    VERBOSE_STEPS = a.verbose_steps
    PROVIDER = a.provider
    BASE_URL, KEY_ENV = PROVIDERS[PROVIDER]
    FULL_ENVS = a.full_envs
    if a.envs:
        GRADING_ENVS = []
        for e in a.envs:
            if ":" not in e: sys.exit(f"--envs entry '{e}' must be 'label:python_path'")
            lab, py = e.split(":", 1)
            if not os.path.exists(py): sys.exit(f"--envs python not found: {py}")
            GRADING_ENVS.append((lab, py))
    else:
        GRADING_ENVS = [("default", sys.executable)]
    print("grading envs (OR, pass-if-any): " + ", ".join(f"{l}->{p}" for l, p in GRADING_ENVS)
          + (" [FULL: every env per step]" if FULL_ENVS else " [short-circuit on first pass]"))
    probs = [json.loads(l) for l in open(DATA)]
    if a.only:
        keep = set(a.only.split(",")); probs = [p for p in probs if str(p["problem_id"]) in keep]
    models = {"pro": PRO_MAX, "flash": FLASH_MAX}
    sel_models = [models[a.model]] if a.model else [PRO_MAX, FLASH_MAX]
    sel_bg = {"on": [True], "off": [False]}.get(a.background, [False, True])
    summaries = []
    for model in sel_models:
        for with_bg in sel_bg:
            summaries.append(run_config(model, with_bg, probs, a.workers, a.run))
    print("\n==================== COMBINED SUMMARY (cleaned test set) ====================")
    print(f"{'model':<24}{'background':<12}{'steps':>12}{'step_acc':>10}{'problems':>11}{'prob_acc':>10}")
    for s in summaries:
        print(f"{s['model']:<24}{'with' if s['with_background'] else 'without':<12}"
              f"{str(s['steps_correct'])+'/'+str(s['steps_total']):>12}{s['step_accuracy']:>10}"
              f"{str(s['problems_correct'])+'/'+str(s['problems']):>11}{s['problem_accuracy']:>10}")
    print(f"\nper-problem detail + trajectories: eval_clean/ds_runs/{a.run}/cleaned_<model>/<bg>/"
          "  (results.json, <pid>/<step>.raw.json)")

if __name__ == "__main__":
    main()
