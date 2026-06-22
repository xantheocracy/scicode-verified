#!/usr/bin/env python3
"""Step-level PARALLEL re-scorer against the fixed h5.

run_deepseek_eval.py parallelizes at the PROBLEM level and scores a problem's steps
serially (a leftover from the generate+score loop) -> wall time is bounded by the
longest single problem's serial chain, not by core count. But all *.code.py already
exist, so every (model, problem, step) score is INDEPENDENT. This driver builds the
exact same cumulative code + reuses run_deepseek_eval.score_step VERBATIM (identical
verdicts), then dispatches every step across all cores. Existing *.score.json caches
are reused (skip) unless --force.

    python3 eval_clean/regrade_parallel.py --workers 64            # both models
    python3 eval_clean/regrade_parallel.py --models flash --force  # one model, ignore cache
"""
import os, sys, json, argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_deepseek_eval as R   # reuse score_step, SKIP, DATA, ROOT, PRO_MAX, FLASH_MAX


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="run1")
    ap.add_argument("--workers", type=int, default=64)
    ap.add_argument("--models", default="pro,flash")
    ap.add_argument("--force", action="store_true", help="ignore existing *.score.json caches")
    a = ap.parse_args()

    models = {"pro": R.PRO_MAX, "flash": R.FLASH_MAX}
    sel = [models[m] for m in a.models.split(",")]
    probs = [json.loads(l) for l in open(R.DATA)]

    summaries = []
    for model in sel:
        outdir = R.ROOT / "eval_clean" / "ds_runs" / a.run / f"cleaned_{model}" / "with_bg"
        tasks = []            # (pid, sid, cum, test_cases, cdir)
        order = {}            # pid -> [(sid, k)]
        for prob in probs:
            pid = str(prob["problem_id"]); cdir = outdir / pid
            if not cdir.exists():
                continue
            cum = prob["required_dependencies"]; order[pid] = []
            for k, sub in enumerate(prob["sub_steps"]):
                sid = sub["step_number"]; order[pid].append((sid, k))
                cf = cdir / f"{sid}.code.py"
                if cf.exists():
                    cum += "\n\n" + cf.read_text()      # cumulative incl. THIS step's code
                if (pid, k) in R.SKIP:
                    continue
                sf = cdir / f"{sid}.score.json"
                if sf.exists() and not a.force:
                    continue
                if cf.exists():
                    tasks.append((pid, sid, cum, sub["test_cases"], cdir))
        print(f"[{model}] {len(tasks)} steps to (re)score across {a.workers} workers", flush=True)

        def work(t):
            pid, sid, cum, tcs, cdir = t
            ok = R.score_step(cum, tcs, sid, cdir)
            (cdir / f"{sid}.score.json").write_text(json.dumps({"step_id": sid, "passed": ok}))
            return ok
        done = 0
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            for fut in as_completed([ex.submit(work, t) for t in tasks]):
                fut.result(); done += 1
                if done % 25 == 0 or done == len(tasks):
                    print(f"  [{model}] {done}/{len(tasks)}", flush=True)

        # aggregate identically to run_deepseek_eval.run_config
        results = []
        for prob in probs:
            pid = str(prob["problem_id"]); cdir = outdir / pid
            if not cdir.exists():
                continue
            steps = {}
            for sid, k in order[pid]:
                if (pid, k) in R.SKIP:
                    steps[sid] = None; continue
                sf = cdir / f"{sid}.score.json"
                steps[sid] = json.loads(sf.read_text()).get("passed") if sf.exists() else None
            scored = [v for v in steps.values() if v is not None]
            results.append({"problem_id": pid, "steps": steps, "n_steps_scored": len(scored),
                            "n_steps_ok": sum(scored), "problem_correct": bool(scored) and all(scored)})
        ts = sum(r["n_steps_scored"] for r in results); to = sum(r["n_steps_ok"] for r in results)
        po = sum(r["problem_correct"] for r in results)
        summary = {"model": model, "with_background": True, "problems": len(results),
                   "problems_correct": po, "steps_total": ts, "steps_correct": to,
                   "step_accuracy": round(to / ts, 4) if ts else 0,
                   "problem_accuracy": round(po / len(results), 4) if results else 0}
        (outdir / "results.json").write_text(json.dumps(
            {"summary": summary, "results": sorted(results, key=lambda r: int(r["problem_id"]))}, indent=2))
        summaries.append(summary)
        print(f"[{model}] DONE: {po}/{len(results)} problems, {to}/{ts} steps "
              f"(step_acc {summary['step_accuracy']}, prob_acc {summary['problem_accuracy']})", flush=True)

    print("\n==================== PARALLEL REGRADE SUMMARY (fixed h5) ====================")
    for s in summaries:
        print(f"{s['model']:<22} problems {s['problems_correct']}/{s['problems']}  "
              f"steps {s['steps_correct']}/{s['steps_total']}  "
              f"step_acc {s['step_accuracy']}  prob_acc {s['problem_accuracy']}")


if __name__ == "__main__":
    main()
