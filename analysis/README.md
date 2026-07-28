# Analysis artifacts

Machine-readable statistics behind the SciCode-Verified analysis. Release-level counts use the
64-problem, 287-scored-subproblem v2 dataset; they should not be confused with the broader
80-problem audit history in `CLEANING_LOG.md`.

| File | What it is |
|---|---|
| `defects.json` | The 264-defect release taxonomy: problem, step, affected fields, direction, rationale, and provenance. |
| `flawed_steps.json` | Per-subproblem footprint: 155/287 scored subproblems across 58/64 problems carry a score-suppressing defect; 71 touch tests or frozen gold. |
| `flips.json` | Per-model fail→pass / pass→fail step sets between the original-benchmark run (orig1) and the corrected-benchmark run (run4) for GPT-5.5, Gemini 3.5 Flash, Claude Opus 4.8, GLM-5.2; union/intersection included. |
| `or_gain.json` | Per-model steps whose verdict multi-environment OR grading changes vs the 2024 stack alone (7–9 per model), with error text and whole-problem effects; extracted from the per-step grading caches. |
| `regrade_summary.json` | Fixed-output re-grading: each model's original-run generations re-scored, unchanged, against the corrected tests/gold. Separates the grading-layer share (20–35% of the step gain) from the specification-layer share. |

Regenerate the subproblem footprint using only committed release files:

```bash
python analysis/make_flawed_steps.py
```

The flip, environment, and fixed-output summaries were derived from evaluation caches under
`eval_clean/ds_runs/`. Those raw per-step model outputs are too large to commit wholesale; the
JSON summaries in this directory are the released analysis records.
