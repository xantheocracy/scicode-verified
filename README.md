<div align="center">

# SciCode-Verified

**A human-verified benchmark for scientific code generation**

[Paper](https://arxiv.org/abs/2608.04975) ·
[Dataset](https://github.com/flyingwagner/scicode-verified/releases/tag/data) ·
[Run the benchmark](#run-it) ·
[Evaluation protocol](#evaluation-protocol) ·
[Audit trail](CLEANING_LOG.md) ·
[Upstream SciCode](https://github.com/scicode-bench/SciCode)

[![arXiv](https://img.shields.io/badge/arXiv-2608.04975-b31b1b.svg)](https://arxiv.org/abs/2608.04975)
[![Dataset](https://img.shields.io/badge/dataset-v2-4c6ef5)](https://github.com/flyingwagner/scicode-verified/releases/tag/data)
[![Problems](https://img.shields.io/badge/problems-64-7950f2)](scicode_verified/problems_test.jsonl)
[![Scored subproblems](https://img.shields.io/badge/scored_subproblems-287-9c36b5)](scicode_verified/manifest.json)
[![License](https://img.shields.io/badge/license-Apache--2.0-2f9e44)](eval_clean/vendor/LICENSE)

</div>

SciCode-Verified is an independent, human-in-the-loop correction of the
[SciCode](https://github.com/scicode-bench/SciCode) test benchmark. It preserves the scientific
reasoning challenge while repairing contradictions, missing conventions, incorrect frozen
targets, non-deterministic tests, and other defects that can reject valid solutions.

<table>
  <tr>
    <td align="center"><strong>262</strong><br>verified corrections</td>
    <td align="center"><strong>63 / 64</strong><br>problems changed</td>
    <td align="center"><strong>192 / 262</strong><br>defects that reject correct code</td>
    <td align="center"><strong>155 / 287</strong><br>affected subproblems</td>
  </tr>
</table>

## How one defect becomes a benchmark-wide failure

<img src="assets/paper-defect-mechanism.png" width="100%" alt="A benchmark defect propagating through cumulative subproblems and causing a false whole-problem failure">

SciCode subproblems are cumulative, and a whole problem passes only when every scored
subproblem passes. One defective specification, frozen answer, or test can therefore propagate
downstream and erase an otherwise correct solution. The audit found this score-suppressing
failure mode in **58 of 64 main problems**.

## Matched re-evaluation

<img src="assets/paper-before-after.png" width="100%" alt="Paper figure comparing original SciCode and SciCode-Verified accuracy for twelve frontier model snapshots">

In the manuscript's matched twelve-model-snapshot evaluation, changing only the benchmark data moves the
observed frontier from **45.3–60.3% to 83.7–98.3%** on subproblems, and from
**9.4–26.6% to 68.8–92.2%** on whole problems. The model output protocol, evaluation harness,
with-background condition, pass@1 setting, and multi-environment-OR grading are held fixed.

> SciCode-Verified is not an easier rewrite. Corrections state what is required to make each
> task well posed and its grading faithful. Weak tests are tightened; the scientific
> derivations and algorithms remain the model's responsibility.

## Reproducible by construction

Every accepted correction is recorded in a ledger, propagated from a single source of truth,
and checked against the released JSONL, HDF5, and manifest. See
[`CLEANING_LOG.md`](CLEANING_LOG.md) for the complete audit and
[`analysis/README.md`](analysis/README.md) for release statistics.

## Run it

Clone the repository and install the small runtime:

```bash
git clone https://github.com/flyingwagner/scicode-verified.git
cd scicode-verified
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip openai h5py numpy scipy matplotlib sympy
```

Download the released grading targets and verify their checksum:

```bash
gh release download data --repo flyingwagner/scicode-verified --dir scicode_verified
md5sum scicode_verified/test_data_cleaned.h5
# 2b41a7df40ddc23ce651ec05b8ecb6f8
```

Run a one-problem smoke test:

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

Runs are resumable. Generated code, raw responses, per-step scores, and aggregate results are
saved under `eval_clean/ds_runs/`. OpenRouter models work with the same entry point by setting
`OPENROUTER_API_KEY` and passing the raw model slug to `--model`.

For generation-only runs, cached re-grading, provider configuration, and original-versus-
verified comparisons, see [`eval_clean/README.md`](eval_clean/README.md).

## Evaluation protocol

| | Canonical setting |
|---|---|
| Evaluation set | 64 main problems / 287 scored subproblems |
| Sampling | pass@1 |
| Whole-problem score | Pass only if every scored subproblem passes |
| Context | With and without background reported separately |
| Step construction | Cumulative: step *k* receives code from steps `1..k-1` |
| Timeout | 1,800 seconds per step and environment |
| Environment drift | Pass if correct in either pinned 2024-era or 2025-era scientific Python |
| Integrity | Dataset hashes must match `scicode_verified/manifest.json` |

The release excludes original test problem 2 because its specification does not determine a
unique, verifiable answer. The remaining 64 problems are the exact matched set used in the
before/after evaluation above.

## Repository map

| Path | What it contains |
|---|---|
| [`scicode_verified/`](scicode_verified/) | Released benchmark, source problems, target patches, and manifest |
| [`eval_clean/`](eval_clean/) | Portable generation, scoring, and re-grading harness |
| [`analysis/`](analysis/) | Machine-readable defect and evaluation analyses |
| [`ledger/`](ledger/) | Per-change provenance and focused defect investigations |
| [`tools/`](tools/) | Dataset assembly and release verification gate |

The large `test_data_cleaned.h5` is distributed through
[GitHub Releases](https://github.com/flyingwagner/scicode-verified/releases/tag/data), not Git.
The evaluator verifies its hash before running.

## Attribution

SciCode-Verified is derived from SciCode and redistributed under the Apache License 2.0. The
vendored upstream notice and license are in [`eval_clean/vendor/`](eval_clean/vendor/). If you
use this release, please cite both the original SciCode benchmark and SciCode-Verified.

```bibtex
@article{hu2026scicodeverified,
  title         = {{SciCode-Verified}: How Benchmark Defects Underestimated the Scientific-Coding Ability of Language Models},
  author        = {Hu, Sihan and Huang, Lyuhan and Deng, Youjin and Chen, Kun},
  year          = {2026},
  eprint        = {2608.04975},
  archivePrefix = {arXiv},
  primaryClass  = {cs.SE},
  url           = {https://arxiv.org/abs/2608.04975}
}
```
