<div align="center">

# SciCode-Verified

### A human-verified benchmark for scientific code generation

[![Dataset](https://img.shields.io/badge/dataset-v2-4c6ef5)](https://github.com/flyingwagner/scicode-verified/releases/tag/data)
[![Problems](https://img.shields.io/badge/problems-64-7950f2)](scicode_verified/problems_test.jsonl)
[![Scored subproblems](https://img.shields.io/badge/scored_subproblems-287-9c36b5)](scicode_verified/manifest.json)
[![License](https://img.shields.io/badge/license-Apache--2.0-2f9e44)](eval_clean/vendor/LICENSE)

[Download](https://github.com/flyingwagner/scicode-verified/releases/tag/data) ·
[Quick start](#quick-start) ·
[Evaluation protocol](#evaluation-protocol) ·
[Audit trail](#audit-trail) ·
[Upstream SciCode](https://github.com/scicode-bench/SciCode)

</div>

SciCode-Verified is an independent, human-in-the-loop correction of the
[SciCode](https://github.com/scicode-bench/SciCode) test benchmark. It keeps the scientific
tasks difficult while fixing contradictions, missing conventions, incorrect frozen targets,
non-deterministic tests, and other defects that can mis-score a valid solution.

The release contains the same **64 evaluable test problems and 287 scored subproblems** used in
our matched before/after experiments. Problem 2 from the original 65-problem test split is
excluded because its specification does not determine a unique verifiable answer.

## Why verification matters

| Release-level finding | Count |
|---|---:|
| Confirmed defects corrected | **264** |
| Problems changed | **63 / 64** |
| Defects that reject a correct solution | **192 / 264** |
| Scored subproblems touched by score-suppressing defects | **155 / 287** |
| Subproblems with incorrect tests or frozen gold | **71 / 287** |

SciCode scores a main problem only when every scored subproblem passes. A single defective
subproblem can therefore erase an otherwise correct multi-step solution.

Across the completed matched, with-background evaluations as of **2026-07-28**, changing only
the benchmark data moves the observed frontier from **45.3–60.6% to 83.7–98.3%** on subproblems
and from **9.4–26.6% to 68.8–92.2%** on whole problems. The evaluation harness, model outputs
protocol, and pass@1 setting are held fixed.

> **SciCode-Verified is not an easier rewrite.** Corrections specify only what is required to
> make each task well posed and its grading faithful. Weak tests are tightened; scientific
> derivations and algorithms remain the model's responsibility.

## Quick start

### 1. Clone and install the runtime

```bash
git clone https://github.com/flyingwagner/scicode-verified.git
cd scicode-verified

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install openai h5py numpy scipy matplotlib sympy
```

### 2. Download the released grading data

```bash
gh release download data \
  --repo flyingwagner/scicode-verified \
  --dir scicode_verified

md5sum scicode_verified/test_data_cleaned.h5
# expected: 2b41a7df40ddc23ce651ec05b8ecb6f8
```

The release contains:

| Asset | Purpose |
|---|---|
| `problems_test.jsonl` | Canonical prompts, steps, function headers, and tests |
| `test_data_cleaned.h5` | Frozen grading targets |
| `manifest.json` | Version and content hashes used by the harness |

The evaluator checks the JSONL and HDF5 files against `manifest.json` before running and exits on
a mismatch.

### 3. Run a one-problem smoke test

```bash
export DEEPSEEK_API_KEY="..."

python eval_clean/run_deepseek_eval.py \
  --model pro \
  --dataset cleaned \
  --background on \
  --run smoke \
  --only 58 \
  --workers 1
```

Runs are resumable. Generated code, raw responses, per-step scores, and the aggregate
`results.json` are written under:

```text
eval_clean/ds_runs/<run>/<dataset>_<model>/<with_bg|no_bg>/
```

For an OpenRouter model, pass its raw slug:

```bash
export OPENROUTER_API_KEY="..."

python eval_clean/run_deepseek_eval.py \
  --model vendor/model \
  --dataset cleaned \
  --background on \
  --run my-model
```

See [`eval_clean/README.md`](eval_clean/README.md) for generation-only runs, cached re-grading,
original-vs-verified comparisons, and provider configuration.

## Evaluation protocol

| Choice | Canonical setting |
|---|---|
| Unit of evaluation | 64 main problems / 287 scored subproblems |
| Sampling | pass@1 |
| Main-problem score | pass only if every scored subproblem passes |
| Context conditions | with background and without background are reported separately |
| Step construction | cumulative: step *k* receives code from steps `1..k-1` |
| Timeout | 1,800 seconds per step and environment |
| Scientific Python drift | pass if correct in either pinned 2024-era or 2025-era environment |
| Integrity | dataset hashes must match `scicode_verified/manifest.json` |

For the paper-compatible two-environment grading protocol, pass both interpreters explicitly:

```bash
python eval_clean/run_deepseek_eval.py \
  --model vendor/model \
  --background on \
  --run reproducible-run \
  --envs \
    2024:/path/to/scipy-2024/bin/python \
    2025:/path/to/scipy-2025/bin/python \
  --full-envs
```

`--generate-only` can separate API generation from CPU-heavy grading. Re-run the same command
without `--generate-only`; cached generations are reused and no model API calls are made.

## What is in this repository

| Path | Role |
|---|---|
| [`scicode_verified/`](scicode_verified/) | Released dataset, source-of-truth problem files, target patches, and manifest |
| [`eval_clean/`](eval_clean/) | Portable generation, scoring, and re-grading harness |
| [`analysis/`](analysis/) | Machine-readable defect and evaluation analyses |
| [`ledger/`](ledger/) | Per-change provenance and focused defect investigations |
| [`tools/`](tools/) | Dataset assembly and release verification gate |
| [`CLEANING_LOG.md`](CLEANING_LOG.md) | Full audit method, rounds, taxonomy, and release history |

The large `test_data_cleaned.h5` is distributed through
[GitHub Releases](https://github.com/flyingwagner/scicode-verified/releases/tag/data), not Git.
Minimal byte-identical upstream components required by the evaluator are vendored under
[`eval_clean/vendor/`](eval_clean/vendor/).

## Audit trail

The release follows a **source → derive → verify → publish** discipline:

1. Edit only `scicode_verified/problems/<id>.json` and
   `scicode_verified/targets/<id>.json`.
2. Record each accepted correction in `ledger/<round>.jsonl`.
3. Regenerate `problems_test.jsonl` and `manifest.json` with `tools/assemble.py`.
4. Run the bidirectional gate:

```bash
python tools/assemble.py
python tools/verify.py --scope full --round <ROUND>
```

The gate checks that every recorded decision reached the release, every release change has a
record, derived files match their source, prompt-only rounds do not alter targets, and all
executable fields parse.

For the release-specific statistics, start with [`analysis/README.md`](analysis/README.md).
For the complete 80-problem audit history, see [`CLEANING_LOG.md`](CLEANING_LOG.md).

## Rebuilding from upstream

Normal evaluation does **not** require an upstream SciCode checkout. Rebuilding the corrected
HDF5 or reproducing the original-benchmark side does:

```bash
git clone https://github.com/scicode-bench/SciCode.git SciCode
python eval_clean/build_clean_h5.py
```

The rebuilt file must match `manifest.json`:

```text
2b41a7df40ddc23ce651ec05b8ecb6f8  test_data_cleaned.h5
```

## Attribution and license

SciCode-Verified is derived from SciCode and redistributed under the Apache License 2.0. The
vendored upstream notice and license are in [`eval_clean/vendor/`](eval_clean/vendor/). If you use
this release, please cite both the original SciCode benchmark and SciCode-Verified.
