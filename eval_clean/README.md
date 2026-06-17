# Cleaned SciCode test-set eval pipeline

This directory wires the SciCode `inspect_ai` eval to the **cleaned** benchmark: the cleaned problem
prompts/tests plus the patched answer targets. Run it exactly like the original eval, but pointed here
via `--data-dir` and `--h5py-file` (the eval already supports both flags).

## Contents
- `data/problems_test.jsonl` — **cleaned** 64 test problems (schema-pure: no `split`, gold null).
- `data_original/problems_test.jsonl` — the **same 64 problem IDs** with the *original* content, for an
  apples-to-apples comparison.
- `test_data_cleaned.h5` — copy of `SciCode/eval/data/test_data.h5` with the regenerated/patched targets
  applied (29 problems have changed targets).
- `run_cleaned_eval.sh` — runs `inspect_ai/run_eval.py` against either variant.
- `build_h5.py` — rebuilds `test_data_cleaned.h5` from `cleaning/targets/*.json` (idempotent; re-run if
  targets change).

## The eval set: 64 of 65 test problems
- **60** cleaned by this effort (incl. all 15 HEAVY + 14 SIMPLE + the recovered hard problem **22**),
  each independently reviewed (`cleaning/review/<id>.json`, all `accept`).
- **12** — expert-cleaned (kunchen). NOT yet integrated; currently uses the ORIGINAL problem/targets.
  To integrate, apply `cleaning/_investigate/12_expert_return/` (mixing 0.5→0.3 + regenerated targets).
- **25, 26, 56** — audit found no scoring defects; original content used as-is (fair).
- **2** (Gaussian_Beam_Focus) — **excluded** (废题: structurally underdetermined, unreproducible).

Of the 64: **59** have changed prompts/tests, **29** have changed answer targets.

## How to run
The eval needs the SciCode eval env (`inspect_ai` + the `scicode` package) and your model provider
credentials (the original used gpt-5 via OpenRouter). Point `PYTHON` at that env.

```bash
# from the repo root (SciCode_refine/)
export OPENROUTER_API_KEY=...                 # or whatever --load-api-key expects
PYTHON=/path/to/scicode-env/bin/python3 \
  bash eval_clean/run_cleaned_eval.sh         # -> eval_clean/results_cleaned/

# optional: same 64 problems on ORIGINAL data, to measure the delta
EVAL_VARIANT=original PYTHON=/path/to/scicode-env/bin/python3 \
  bash eval_clean/run_cleaned_eval.sh         # -> eval_clean/results_original/
```
Override `SERVICE`, `MODEL_NAME`, `REASONING`, `MAX_TOKENS`, `SPLIT`, `OUTPUT_DIR` via env vars.

The score (`Problem Correctness`, `Total Correct` / `Total Steps`) for each problem is written under
`OUTPUT_DIR`. Compare `results_cleaned` vs `results_original` per problem: the cleaning should turn
previously-failing-but-correct steps into passes (and remove a handful of false passes where a defect
let a wrong solution through).

## Re-scoring existing generations (no new API calls)
The repo already has a GPT-5 (90K) run at `SciCode/eval/inspect_ai/GPT5-90K_results/`. To compare
without regenerating, re-run inspect_ai's scorer on that log with `--h5py-file test_data_cleaned.h5`
and `--data-dir eval_clean/data` (inspect_ai `score`/re-grade), or extract its per-step code and feed
`SciCode/eval/scripts/test_generated_code.py` the cleaned h5. (The eval env is not installed on this
machine, so this was not run here.)

## Validation done here
- Every cleaned `function_header` and `test_case` `ast.parse`-compiles; `general_tests` mirrors each
  problem's last sub-step; no `split`/metadata keys; gold withheld (null).
- `process_hdf5_to_tuple` from `test_data_cleaned.h5` returns the patched values for every changed step
  (incl. complex targets in 22.3, the added tests in 45.3/79.1, and the re-indexed 73.9).

## Running with the DeepSeek API (no inspect_ai needed)
`run_deepseek_eval.py` evaluates **DeepSeek V4 Pro Max and Flash Max × {without, with background}**
(the four target configs) on the cleaned data + cleaned h5. It uses the installed `openai` client against
DeepSeek's OpenAI-compatible endpoint, reproduces the official SciCode prompt + cumulative scoring, and is
resumable (per-step code cached under `ds_runs/`).

The API exposes two models, `deepseek-v4-pro` and `deepseek-v4-flash`; **"Max" is the `reasoning_effort`**
(`low|medium|high|max|xhigh`), not part of the model name. Both are already wired at the top of the script
(`PRO_MAX`, `FLASH_MAX`, `REASONING_EFFORT="max"`) and verified against the live API — no edits needed.

```bash
export DEEPSEEK_API_KEY=sk-...
python3 eval_clean/run_deepseek_eval.py --only 58,73,22   # quick sanity check first
python3 eval_clean/run_deepseek_eval.py --workers 8        # full: all 4 configs x 64 problems
```
It prints a combined summary (step/problem accuracy for each model × background) and writes per-problem
detail to `ds_runs/cleaned_<model>/<bg>/results.json`. (Smoke-tested: a known-correct solution scores 5/5
on problem 58 against the cleaned h5.)
