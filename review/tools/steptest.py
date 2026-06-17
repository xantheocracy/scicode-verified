#!/usr/bin/env python3
"""Assemble and run ONE SciCode sub-step's test_cases against the frozen h5 targets.

This mirrors the official scorer exactly: it builds a script of
  required_dependencies + <your code> + target-loading + test_case asserts
and runs it. Each test case is run as a SEPARATE subprocess so you can see
which test index fails.

Usage:
  python3 review/tools/steptest.py --problem 5 --step 5.2 --code my_impl.py
  python3 review/tools/steptest.py --problem 1 --step 1.3 --use-gold       # dev split only

--code FILE   : file containing ALL function defs needed (this step + any
                previous-step functions it calls). Dependencies are prepended
                automatically; you may still repeat imports safely.
--use-gold    : use cumulative official ground_truth_code for steps 1..k
                (only available for dev-split problems).
--timeout N   : per-test timeout seconds (default 120; official harness uses 1800).
--test N      : run only test index N (1-based). Default: all.
--isolate     : run each test case in its OWN subprocess (diagnostic mode).
                DEFAULT is joint mode = official harness behavior: all test
                cases concatenated into ONE script sharing a namespace, so
                variables defined in test i are visible to test i+1. Official
                pass/fail is determined by joint mode; use --isolate only to
                localize which test fails (beware NameError false-fails for
                tests that rely on earlier tests' variables).

Exit code 0 iff all executed tests pass.
"""
import sys, json, argparse, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROB_DIR = ROOT / "review" / "problems"
H5 = ROOT / "SciCode" / "eval" / "data" / "test_data.h5"
SRC = ROOT / "SciCode" / "src"
SKIPPED = {"13.6", "62.1", "76.3"}  # officially skipped: no h5 target exists


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--problem", required=True)
    ap.add_argument("--step", required=True)
    ap.add_argument("--code")
    ap.add_argument("--use-gold", action="store_true")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--test", type=int, default=0)
    ap.add_argument("--isolate", action="store_true")
    a = ap.parse_args()

    if a.step in SKIPPED:
        print(f"REFUSED: step {a.step} is officially skipped by the SciCode harness "
              f"and has NO target in the h5. It cannot be auto-tested.")
        sys.exit(3)

    prob = json.loads((PROB_DIR / f"{a.problem}.json").read_text())
    steps = {s["step_number"]: s for s in prob["sub_steps"]}
    if a.step not in steps:
        print(f"ERROR: step {a.step} not found. Steps: {list(steps)}"); sys.exit(2)
    step = steps[a.step]
    tests = step["test_cases"]

    if a.use_gold:
        if prob["split"] != "dev":
            print("ERROR: --use-gold only works on dev-split problems (test split has no gold)."); sys.exit(2)
        idx = [s["step_number"] for s in prob["sub_steps"]].index(a.step)
        code = "\n\n".join((s.get("ground_truth_code") or "") for s in prob["sub_steps"][: idx + 1])
    elif a.code:
        code = Path(a.code).read_text()
    else:
        print("ERROR: provide --code FILE or --use-gold"); sys.exit(2)

    header = (
        f"{prob['required_dependencies']}\n\n{code}\n\n"
        f"import sys\nsys.path.insert(0, r'{SRC.as_posix()}')\n"
        f"from scicode.parse.parse import process_hdf5_to_tuple\n"
        f"targets = process_hdf5_to_tuple('{a.step}', {len(tests)}, r'{H5.as_posix()}')\n"
    )

    def exec_script(script, label, timeout):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(script); path = f.name
        try:
            r = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=timeout)
            if r.returncode == 0:
                print(f"{label}: PASS"); return True
            tail = "\n".join((r.stderr or r.stdout).strip().splitlines()[-8:])
            print(f"{label}: FAIL\n--- traceback tail ---\n{tail}\n---")
            return False
        except subprocess.TimeoutExpired:
            print(f"{label}: TIMEOUT (> {timeout}s)"); return False
        finally:
            Path(path).unlink(missing_ok=True)

    if a.isolate or a.test:
        run_idx = [a.test - 1] if a.test else range(len(tests))
        n_pass = sum(
            exec_script(header + f"\ntarget = targets[{i}]\n" + tests[i],
                        f"test {i+1}/{len(tests)} [isolated]", a.timeout)
            for i in run_idx
        )
        total = len(list(run_idx))
        print(f"\nRESULT step {a.step} (isolated): {n_pass}/{total} tests pass"
              f"\nNOTE: official scoring uses joint mode; an isolated NameError may pass officially.")
        sys.exit(0 if n_pass == total else 1)

    # joint mode = official harness behavior: one script, shared namespace
    body = "".join(f"\ntarget = targets[{i}]\n" + tests[i] + "\n" for i in range(len(tests)))
    ok = exec_script(header + body, f"step {a.step} all {len(tests)} tests [joint=official]",
                     a.timeout * len(tests))
    print(f"\nRESULT step {a.step}: {'PASS' if ok else 'FAIL'} (official joint scoring)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
