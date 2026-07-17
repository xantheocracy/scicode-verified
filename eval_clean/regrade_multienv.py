#!/usr/bin/env python3
"""Multi-ENVIRONMENT re-grading (pass-if-any across library versions).

Re-runs each already-saved model step under several pinned scientific-Python envs and
marks the step PASSED if it passes in ANY env (the OR). This makes grading robust to
numpy/scipy API drift (e.g. simps->simpson, trapz->trapezoid, interp2d removal): a step
is "correct" if its code produces the right output in SOME reasonable environment, rather
than being penalized for matching one frozen library version.

It reuses the EXACT cumulative-code + target-loading recipe of
run_deepseek_eval.score_step (identical verdict per env). Generation is unchanged; this
only re-runs existing *.code.py, so there are NO API calls and NO cost.

Envs are `label:python_executable` pairs. Example (on sichuan2):
  python3 eval_clean/regrade_multienv.py --run run3 --models pro,flash --workers 32 \
     --envs 2024:/home/xcai/miniconda3/envs/sci2024/bin/python \
            2025:/home/xcai/miniconda3/envs/cp312/bin/python

Writes per step: <cdir>/<sid>.multienv.json = {"step_id","per_env":{label:bool},"passed":any}.
Prints, per model: each env's solo accuracy, the OR accuracy, and a breakdown of how many
steps pass only-in-one-env (the API-era artifacts).
"""
import os, sys, json, time, argparse, subprocess, collections
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_deepseek_eval as R   # reuse SRC, H5, DATA, ROOT, SKIP, PRO_MAX, FLASH_MAX

SUBENV = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
          "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"}


def build_script(cumcode, test_cases, step_id):
    s = [cumcode, "", f"import sys; sys.path.insert(0, r'{R.SRC.as_posix()}')",
         "from scicode.parse.parse import process_hdf5_to_tuple",
         f"targets = process_hdf5_to_tuple('{step_id}', {len(test_cases)}, r'{R.H5}')"]
    for i, tc in enumerate(test_cases):
        s += [f"target = targets[{i}]", tc]
    return "\n".join(s)


def run_under(py, path):
    try:
        p = subprocess.run([py, str(path)], capture_output=True, text=True,
                           timeout=1800, env=SUBENV)
        return p.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="run3")
    ap.add_argument("--models", default="pro,flash",
                    help="comma-separated REGISTRY keys (pro,flash,gpt-5.5,...) or raw vendor/model slugs")
    ap.add_argument("--dataset", choices=["cleaned", "original"], default="cleaned",
                    help="grade against the cleaned (default) or the pristine ORIGINAL data/h5; "
                         "reads run dirs with the matching 'cleaned_'/'original_' prefix")
    ap.add_argument("--bg", choices=["with_bg", "no_bg"], default="with_bg")
    ap.add_argument("--envs", nargs="+", required=True, help="label:python_path ...")
    ap.add_argument("--workers", type=int, default=32)
    a = ap.parse_args()

    if a.dataset == "original":
        R.DS_TAG, R.DATA, R.H5 = "original", R.ORIG_DATA, R.ORIG_H5

    envs = [(e.split(":", 1)[0], e.split(":", 1)[1]) for e in a.envs]
    labels = [l for l, _ in envs]
    sel = [R.REGISTRY[m][0] if m in R.REGISTRY else m for m in a.models.split(",")]
    probs = [json.loads(l) for l in open(R.DATA)]
    tmp = R.ROOT / "eval_clean" / "_multienv_tmp"; tmp.mkdir(parents=True, exist_ok=True)

    for model in sel:
        safe = model.replace("/", "__")
        outdir = R.ROOT / "eval_clean" / "ds_runs" / a.run / f"{a.dataset}_{safe}" / a.bg
        tasks, order = [], {}
        for prob in probs:
            pid = str(prob["problem_id"]); cdir = outdir / pid
            if not cdir.exists():
                continue
            cum = prob["required_dependencies"]; order[pid] = []
            for k, sub in enumerate(prob["sub_steps"]):
                sid = sub["step_number"]; order[pid].append((sid, k))
                cf = cdir / f"{sid}.code.py"
                if cf.exists():
                    cum += "\n\n" + cf.read_text()
                if (pid, k) in R.SKIP:
                    continue
                if cf.exists():
                    tasks.append((pid, sid, cum, sub["test_cases"], cdir))
        print(f"[{model}] {len(tasks)} steps x {len(envs)} envs ({', '.join(labels)})", flush=True)

        per_step = {}   # (pid,sid) -> {label: bool}

        def work(t):
            pid, sid, cum, tcs, cdir = t
            sp = tmp / f".s_{safe}_{sid}_{time.time_ns()}.py"
            sp.write_text(build_script(cum, tcs, sid))
            try:
                r = {lab: run_under(py, sp) for lab, py in envs}
            finally:
                sp.unlink(missing_ok=True)
            (cdir / f"{sid}.multienv.json").write_text(
                json.dumps({"step_id": sid, "per_env": r, "passed": any(r.values())}))
            return (pid, sid), r

        done = 0
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            for fut in as_completed([ex.submit(work, t) for t in tasks]):
                key, r = fut.result(); per_step[key] = r; done += 1
                if done % 25 == 0 or done == len(tasks):
                    print(f"  [{model}] {done}/{len(tasks)}", flush=True)

        # ---- aggregate ----
        env_steps_ok = {l: 0 for l in labels}; or_steps_ok = 0; n_steps = 0
        env_prob_ok = {l: 0 for l in labels}; or_prob_ok = 0; n_prob = 0
        combo = collections.Counter()  # frozenset of passing labels -> count
        for prob in probs:
            pid = str(prob["problem_id"])
            if pid not in order:
                continue
            n_prob += 1
            ok_or = True; ok_env = {l: True for l in labels}; any_scored = False
            for sid, k in order[pid]:
                if (pid, k) in R.SKIP:
                    continue
                r = per_step.get((pid, sid))
                if r is None:
                    continue
                any_scored = True; n_steps += 1
                if any(r.values()):
                    or_steps_ok += 1
                else:
                    ok_or = False
                for l in labels:
                    if r[l]:
                        env_steps_ok[l] += 1
                    else:
                        ok_env[l] = False
                combo[frozenset(l for l in labels if r[l])] += 1
            if any_scored:
                if ok_or:
                    or_prob_ok += 1
                for l in labels:
                    if ok_env[l]:
                        env_prob_ok[l] += 1

        print(f"\n===== {model} (run={a.run}) =====")
        for l in labels:
            print(f"  env {l:6}: main {env_prob_ok[l]}/{n_prob}={env_prob_ok[l]/n_prob*100:.2f}%"
                  f"  | step {env_steps_ok[l]}/{n_steps}={env_steps_ok[l]/n_steps*100:.2f}%")
        print(f"  OR(any) : main {or_prob_ok}/{n_prob}={or_prob_ok/n_prob*100:.2f}%"
              f"  | step {or_steps_ok}/{n_steps}={or_steps_ok/n_steps*100:.2f}%")
        print("  step pass-set breakdown (which envs a step passed in):")
        for s, c in sorted(combo.items(), key=lambda kv: -kv[1]):
            tag = "+".join(sorted(s)) if s else "NONE"
            print(f"    {tag:20}: {c}")
        # artifact count = steps that pass under OR but NOT under the newest env alone
        newest = labels[-1]
        artifacts = sum(c for s, c in combo.items() if s and newest not in s)
        print(f"  >>> steps correct under OR but FAILING on '{newest}' alone "
              f"(API-era artifacts vs newest env): {artifacts}")


if __name__ == "__main__":
    main()
