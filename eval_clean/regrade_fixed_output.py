#!/usr/bin/env python3
"""Fixed-output re-grading (cross-grading) for SciCode-Verified.

Takes the ORIGINAL-benchmark cached generations (run tag orig1, WITH background) and
re-grades them UNCHANGED against the CLEANED tests + cleaned h5 targets. Same model
outputs, new grader — isolates the grading-layer-only contribution of the benchmark
corrections:

    orig1     original code  x  original grader   -> published "before" score
    regrade1  orig1 code     x  CLEANED grader    -> THIS script (grading layer only)
    run4      fresh code     x  CLEANED grader    -> full "after" score (grading + information)

Zero API cost: only re-runs cached *.code.py (the harness's authoritative per-step
artifact — run_deepseek_eval.run_problem re-reads code.py on resume, and raw.json's
extracted_code is byte-identical where present; three OpenRouter models were generated
locally so only their code.py were synced to sichuan2).

Grading recipe is byte-identical to run_deepseek_eval.score_step: per problem,
cumulative code = CLEANED required_dependencies + each step's cached code (SKIP steps
carry the injected gold), script = cum + process_hdf5_to_tuple('<sid>', n, CLEANED_H5)
+ CLEANED test_cases, executed under the two era envs (sci2024, cp312) with the
official 1800 s/env timeout, PASS if ANY env passes (OR, short-circuit). Hung steps
are killed by process group so they can never stall the run.

Signature-changed steps (def-line or return_line differs between data_original and
the cleaned jsonl) are graded anyway but FLAGGED — their failures may be artifacts
(old code, new signature expected by the cleaned tests).

Outputs (never touches orig1/run4/SSOT; resume-safe via per-step score.json):
  eval_clean/ds_runs/regrade1/crossgrade_<model>/with_bg/<pid>/<sid>.score.json
  eval_clean/ds_runs/regrade1/crossgrade_<model>/with_bg/results.json
  eval_clean/ds_runs/regrade1/signature_changes.json
  eval_clean/ds_runs/regrade1/comparison.json   (orig1 -> crossgrade -> run4 + flags)

Usage (sichuan2, /data1/sihan/scicode-verified):
  python3 eval_clean/regrade_fixed_output.py --workers 48
  python3 eval_clean/regrade_fixed_output.py --models deepseek-v4-flash --only 11,37   # smoke
"""
import os, sys, json, re, time, signal, hashlib, argparse, subprocess, collections
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT      = Path(__file__).resolve().parent.parent
SRC       = ROOT / "SciCode" / "src"
H5        = str(ROOT / "scicode_verified" / "test_data_cleaned.h5")
DATA      = ROOT / "scicode_verified" / "problems_test.jsonl"
MANIFEST  = ROOT / "scicode_verified" / "manifest.json"
ORIG_DATA = ROOT / "eval_clean" / "data_original" / "problems_test.jsonl"
ORIG_JSONL_MD5 = "d2d1ae6032a4acff2e728f98b2d089cd"   # pinned pristine upstream text

SOURCE_RUN, RUN_TAG, BG = "orig1", "regrade1", "with_bg"
RUNS = ROOT / "eval_clean" / "ds_runs"
OUT  = RUNS / RUN_TAG
TMP  = OUT / "_tmp"
SKIP = {("13", 5), ("62", 0), ("76", 2)}   # official harness skip list (pid, step_index)

# Same two era envs as the canonical runs (run_deepseek_eval.DEFAULT_ENVS on sichuan2),
# same order, same OR short-circuit.
ENVS = [("2024", "/home/xcai/miniconda3/envs/sci2024/bin/python"),   # numpy 1.26 / scipy 1.13
        ("2025", "/home/xcai/miniconda3/envs/cp312/bin/python")]     # numpy 2.4 / scipy 1.17
TIMEOUT = 1800   # official per-step per-env cap (matches run_deepseek_eval._run_script)
SUBENV = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
          "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"}
HEAVY = {"73", "46", "50", "62", "13"}   # schedule first (long MC tests / historical hangs)


def _md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def check_data():
    """Refuse to grade against stale/edited data (verify-with-human invariant 5)."""
    man = json.loads(MANIFEST.read_text())
    if _md5f(DATA) != man["problems_test_jsonl_md5"]:
        sys.exit(f"FATAL: {DATA} md5 != manifest")
    if _md5f(H5) != man["h5_md5"]:
        sys.exit(f"FATAL: {H5} md5 != manifest")
    if _md5f(ORIG_DATA) != ORIG_JSONL_MD5:
        sys.exit(f"FATAL: {ORIG_DATA} md5 != pinned pristine value")
    print(f"data OK: cleaned jsonl+h5 match manifest ({man['version']}, {man['n_problems']} problems); "
          f"original jsonl matches pin.", flush=True)


# ---------------- signature diff (original vs cleaned) ----------------
def _deflines(h):
    return [re.sub(r"\s+", " ", l.strip()) for l in (h or "").splitlines()
            if l.strip().startswith(("def ", "class "))]


def _norm(x):
    return re.sub(r"\s+", " ", (x or "").strip())


def signature_diff(clean_probs, orig_probs):
    """Per step: did the callable signature (def/class line) or return_line change?
    Docstring-only header edits are recorded separately (harmless for cross-grading)."""
    co = {str(p["problem_id"]): p for p in orig_probs}
    def_changed, ret_changed, doc_only = [], [], []
    for p in clean_probs:
        pid = str(p["problem_id"])
        osubs = {s["step_number"]: s for s in co[pid]["sub_steps"]}
        for s in p["sub_steps"]:
            sid = s["step_number"]; o = osubs[sid]
            if _deflines(s["function_header"]) != _deflines(o["function_header"]):
                def_changed.append(sid)
            elif (s["function_header"] or "") != (o["function_header"] or ""):
                doc_only.append(sid)
            if _norm(s["return_line"]) != _norm(o["return_line"]):
                ret_changed.append(sid)
    flagged = sorted(set(def_changed) | set(ret_changed), key=lambda x: [int(t) for t in x.split(".")])
    return {"def_line_changed": def_changed, "return_line_changed": ret_changed,
            "flagged": flagged, "docstring_only_changed": doc_only}


# ---------------- grading (byte-identical recipe to run_deepseek_eval.score_step) ----------------
def build_script(cumcode, test_cases, step_id):
    s = [cumcode, "", f"import sys; sys.path.insert(0, r'{SRC.as_posix()}')",
         "from scicode.parse.parse import process_hdf5_to_tuple",
         f"targets = process_hdf5_to_tuple('{step_id}', {len(test_cases)}, r'{H5}')"]
    for i, tc in enumerate(test_cases):
        s += [f"target = targets[{i}]", tc]
    return "\n".join(s)


def run_under(py, path):
    """Run one grading script under one env. Kill the whole process GROUP on timeout so a
    hung step (e.g. problem 73) can never stall the run or leak orphan processes."""
    p = subprocess.Popen([py, str(path)], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, env=SUBENV, start_new_session=True)
    try:
        return p.wait(timeout=TIMEOUT) == 0
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except Exception:
            pass
        p.wait()
        return False


def grade_task(t):
    """t = (safe_model, pid, sid, cum, test_cases). Resume-safe: cached verdict wins."""
    safe, pid, sid, cum, tcs = t
    sf = OUT / f"crossgrade_{safe}" / BG / pid / f"{sid}.score.json"
    if sf.exists():
        return safe, pid, sid, json.loads(sf.read_text()), True
    sp = TMP / f".s_{safe}_{sid}_{time.time_ns()}.py"
    sp.write_text(build_script(cum, tcs, sid))
    per_env = {}
    try:
        for lab, py in ENVS:
            per_env[lab] = run_under(py, sp)
            if per_env[lab]:
                break   # OR short-circuit, same as the canonical runs
    finally:
        sp.unlink(missing_ok=True)
    rec = {"step_id": sid, "passed": any(per_env.values()), "per_env": per_env,
           "failed_all_envs": not any(per_env.values()) and len(per_env) == len(ENVS)}
    sf.parent.mkdir(parents=True, exist_ok=True)
    sf.write_text(json.dumps(rec))
    return safe, pid, sid, rec, False


# ---------------- main ----------------
def discover_models():
    base = RUNS / SOURCE_RUN
    return sorted(d.name[len("original_"):] for d in base.iterdir()
                  if d.name.startswith("original_") and (d / BG).is_dir())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="", help="comma-separated safe model names "
                    "(default: all original_* dirs under ds_runs/orig1)")
    ap.add_argument("--only", default="", help="comma-separated problem ids (smoke test; "
                    "results.json/comparison.json are only written on FULL runs)")
    ap.add_argument("--workers", type=int, default=48)
    a = ap.parse_args()

    check_data()
    for lab, py in ENVS:
        if not os.path.exists(py):
            sys.exit(f"FATAL: grading env missing: {lab} -> {py}")
    TMP.mkdir(parents=True, exist_ok=True)

    clean_probs = [json.loads(l) for l in open(DATA)]
    orig_probs  = [json.loads(l) for l in open(ORIG_DATA)]
    all_pids = [str(p["problem_id"]) for p in clean_probs]
    if a.only:
        keep = set(a.only.split(","))
        clean_probs = [p for p in clean_probs if str(p["problem_id"]) in keep]
    full_run = {str(p["problem_id"]) for p in clean_probs} == set(all_pids)

    sig = signature_diff([json.loads(l) for l in open(DATA)], orig_probs)
    (OUT / "signature_changes.json").write_text(json.dumps(sig, indent=2))
    flagged = set(sig["flagged"])
    print(f"signature-changed steps (flagged): {len(flagged)} -> {sig['flagged']}", flush=True)
    print(f"docstring-only header changes (not flagged): {len(sig['docstring_only_changed'])}", flush=True)

    models = a.models.split(",") if a.models else discover_models()
    print(f"models: {models}", flush=True)

    # -- assemble all tasks (cumulative code exactly as run_deepseek_eval.run_problem) --
    tasks, meta = [], {}   # meta[safe] = {"skip": {pid: [sid...]}, "missing": [(pid,sid)...]}
    for safe in models:
        indir = RUNS / SOURCE_RUN / f"original_{safe}" / BG
        if not indir.is_dir():
            sys.exit(f"FATAL: {indir} missing")
        meta[safe] = {"skipped_steps": [], "missing_generation": []}
        for prob in clean_probs:
            pid = str(prob["problem_id"])
            cdir = indir / pid
            cum = prob["required_dependencies"]
            for k, sub in enumerate(prob["sub_steps"]):
                sid = sub["step_number"]
                cf = cdir / f"{sid}.code.py"
                code = cf.read_text() if cf.exists() else ""
                if not code.strip() and (pid, k) not in SKIP:
                    # empty/absent generation: graded anyway (fails naturally), counted
                    meta[safe]["missing_generation"].append(sid)
                cum += "\n\n" + code   # harness appends unconditionally
                if (pid, k) in SKIP:
                    meta[safe]["skipped_steps"].append(sid)
                    continue           # gold-injected, never scored
                tasks.append((safe, pid, sid, cum, sub["test_cases"]))
    # schedule known-heavy problems first so their (possibly hung) steps overlap the rest
    tasks.sort(key=lambda t: (t[1] not in HEAVY, t[1], t[2]))
    print(f"{len(tasks)} step-gradings across {len(models)} models "
          f"({a.workers} workers, OR over {[l for l, _ in ENVS]}, {TIMEOUT}s/env cap)", flush=True)

    verdicts = collections.defaultdict(dict)   # safe -> (pid,sid) -> rec
    done = cached = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for fut in as_completed([ex.submit(grade_task, t) for t in tasks]):
            safe, pid, sid, rec, was_cached = fut.result()
            verdicts[safe][(pid, sid)] = rec
            done += 1; cached += was_cached
            if done % 50 == 0 or done == len(tasks):
                el = time.time() - t0
                print(f"  {done}/{len(tasks)} ({cached} cached) [{el/60:.1f} min]", flush=True)

    # -- aggregate per model (results.json in the standard schema) --
    print()
    for safe in models:
        results, flag_report = [], {}
        for prob in clean_probs:
            pid = str(prob["problem_id"])
            steps = {}
            for k, sub in enumerate(prob["sub_steps"]):
                sid = sub["step_number"]
                if (pid, k) in SKIP:
                    steps[sid] = None
                    continue
                rec = verdicts[safe].get((pid, sid))
                steps[sid] = bool(rec["passed"]) if rec else None
                if sid in flagged:
                    flag_report[sid] = steps[sid]
            scored = [ok for ok in steps.values() if ok is not None]
            results.append({"problem_id": pid, "steps": steps,
                            "n_steps_scored": len(scored), "n_steps_ok": sum(scored),
                            "problem_correct": bool(scored) and all(scored)})
        ts = sum(r["n_steps_scored"] for r in results)
        so = sum(r["n_steps_ok"] for r in results)
        po = sum(r["problem_correct"] for r in results)
        summary = {"run_tag": RUN_TAG, "dataset": "cleaned", "crossgrade": True,
                   "source_run": SOURCE_RUN, "source_generations": "original-benchmark prompts",
                   "model": safe.replace("__", "/"), "with_background": True,
                   "problems": len(results), "problems_correct": po,
                   "steps_total": ts, "steps_correct": so,
                   "step_accuracy": round(so / ts, 4) if ts else 0,
                   "problem_accuracy": round(po / len(results), 4) if results else 0,
                   "missing_generation_steps": meta[safe]["missing_generation"],
                   "signature_changed_steps": sorted(flag_report),
                   "signature_changed_verdicts": flag_report}
        print(f"[{safe}] crossgrade: {so}/{ts} steps ({summary['step_accuracy']:.1%}), "
              f"{po}/{len(results)} problems"
              + (f" | missing gens: {len(meta[safe]['missing_generation'])}"
                 if meta[safe]["missing_generation"] else ""), flush=True)
        if full_run:
            od = OUT / f"crossgrade_{safe}" / BG
            od.mkdir(parents=True, exist_ok=True)
            (od / "results.json").write_text(json.dumps(
                {"summary": summary,
                 "results": sorted(results, key=lambda r: int(r["problem_id"]))}, indent=2))

    if not full_run:
        print("\n(partial --only run: per-model results.json / comparison.json NOT written)")
        return

    # -- comparison: orig1 -> crossgrade -> run4, + flagged-step and flip analysis --
    comparison = {"run_tag": RUN_TAG, "bg": BG, "envs": [l for l, _ in ENVS],
                  "signature_flagged_steps": sig["flagged"], "models": {}}
    for safe in models:
        entry = {}
        orig_res = json.loads((RUNS / SOURCE_RUN / f"original_{safe}" / BG / "results.json").read_text())
        entry["orig1"] = {k: orig_res["summary"][k] for k in
                          ("steps_correct", "steps_total", "problems_correct", "problems")}
        cg = json.loads((OUT / f"crossgrade_{safe}" / BG / "results.json").read_text())
        entry["crossgrade"] = {k: cg["summary"][k] for k in
                               ("steps_correct", "steps_total", "problems_correct", "problems")}
        r4p = RUNS / "run4" / f"cleaned_{safe}" / BG / "results.json"
        if r4p.exists():
            r4 = json.loads(r4p.read_text())
            entry["run4"] = {k: r4["summary"][k] for k in
                             ("steps_correct", "steps_total", "problems_correct", "problems")}
        else:
            entry["run4"] = None
        # per-step flips orig1 -> crossgrade (same code, different grader)
        flips = {"fail_to_pass": [], "pass_to_fail": []}
        orig_steps = {}
        for r in orig_res["results"]:
            for sid, ok in r["steps"].items():
                if ok is not None:
                    orig_steps[sid] = ok
        for r in cg["results"]:
            for sid, ok in r["steps"].items():
                if ok is None or sid not in orig_steps:
                    continue
                if ok and not orig_steps[sid]:
                    flips["fail_to_pass"].append(sid)
                elif orig_steps[sid] and not ok:
                    flips["pass_to_fail"].append(sid)
        entry["flips_orig1_to_crossgrade"] = flips
        entry["flagged_step_verdicts"] = {sid: {"orig1": orig_steps.get(sid),
                                                "crossgrade": cg["summary"]["signature_changed_verdicts"].get(sid)}
                                          for sid in sig["flagged"] if sid in orig_steps}
        comparison["models"][safe] = entry
    (OUT / "comparison.json").write_text(json.dumps(comparison, indent=2))

    print("\n==== orig1 -> crossgrade (grading layer only) -> run4 (full re-run) ====")
    print(f"{'model':<36}{'orig1':>14}{'crossgrade':>14}{'run4':>14}")
    for safe, e in comparison["models"].items():
        def fmt(x):
            return f"{x['steps_correct']}/{x['steps_total']} p{x['problems_correct']}" if x else "-"
        print(f"{safe:<36}{fmt(e['orig1']):>14}{fmt(e['crossgrade']):>14}{fmt(e['run4']):>14}")
    print(f"\noutputs: {OUT}/crossgrade_<model>/{BG}/results.json, "
          f"{OUT}/comparison.json, {OUT}/signature_changes.json")


if __name__ == "__main__":
    main()
