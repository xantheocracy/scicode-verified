---
name: scicode-cleaning-review
description: Fresh-agent QA review of ONE problem's cleaning output before it is accepted. Checks the cleaned data for solution/target leakage, schema purity, general_tests sync, target-patch validity, fix correctness, and audit-log honesty. Use after a problem has been cleaned (cleaning/problems|targets|log/<id>).
---

# SciCode Cleaning Review Protocol — v1

You are a FRESH, independent QA reviewer of a single problem's CLEANING output. You did NOT do the cleaning and must not trust the cleaner's claims — **reproduce and check everything yourself**. Your job is to decide whether the cleaning is acceptable for delivery, and to list concrete required fixes if not.

The cleaning pipeline produces three artifacts per touched problem:
- `cleaning/problems/<id>.json` — the **publishable** cleaned problem (goes back into problems_*.jsonl). Must contain ONLY canonical fields, no leakage.
- `cleaning/targets/<id>.json` — **internal** regenerated target patch (applied to a copy of test_data.h5; never shipped in the problem JSON).
- `cleaning/log/<id>.md` — **internal** human changelog.

A quarantined (废题) problem has only `cleaning/log/<id>.md` (status QUARANTINE) and NO `problems/` or `targets/` file.

## Inputs you compare against
- Original problem: `review/problems/<id>.json` (has `split`; dev has `ground_truth_code`).
- Audit record: `review/findings/<id>.json`, `review/verdicts/<id>.json` (what defects were supposed to be fixed).
- Targets (original frozen): via `python3 -c` using `scicode.parse.parse.process_hdf5_to_tuple('<step>', n, 'SciCode/eval/data/test_data.h5')` (sys.path SciCode/src).
- Test runner: `python3 review/tools/steptest.py` (joint mode = official scoring) — but for regenerated targets the h5 is NOT yet patched, so verify by running a reference implementation yourself in `cleaning/_reviewwork/<id>/` against the target PATCH file, not the stale h5.

## Canonical publishable schema (allow-list)
Top level ONLY: `problem_name, problem_id, problem_description_main, problem_background_main, problem_io, required_dependencies, sub_steps, general_solution, general_tests`.
Each sub_step ONLY: `step_number, step_description_prompt, step_background, ground_truth_code, function_header, test_cases, return_line`.

## Checks (run every one; each → pass / fail with evidence)

**A. Leakage — the most important check.** The publishable `cleaning/problems/<id>.json` must not hand the solver anything the original didn't.
1. **No metadata keys**: no `_*` keys, no `split`, nothing outside the allow-list (top level AND every sub_step). Any stray key = fail.
2. **No target values anywhere** in the problem JSON (regenerated targets belong only in the patch file).
3. **No solution/algorithm leakage in prompt-visible fields**: diff `problem_description_main`, `step_description_prompt`, `function_header`, `step_background`, `problem_io` against the original. Any NEW text that reveals how to implement (algorithm steps, the convention the target uses, formulas not in the original, "use reorthogonalization", specific constants chosen by the reference impl) = fail. Allowed: fixing typos, fixing a wrong formula to the correct one, stating a *genuinely necessary* unit/convention that a competent solver still has to implement. Be strict: when in doubt, flag it.
4. **ground_truth_code**: for test-split problems it must stay absent/null (never add gold). For dev, it may be edited only if the fix required it; check it wasn't expanded with hints.

**B. Schema & consistency.**
5. **general_tests sync**: `general_tests` must equal the LAST sub_step's `test_cases` exactly (deep equal). A desync (e.g. test_cases updated but general_tests still holds the old/broken input) = fail.
6. **test_cases well-formed**: each is runnable Python; the function under test is called with the documented signature; no dead/contradictory leftovers introduced.

**C. Fix correctness — reproduce independently.**
7. **Original defect is really gone**: re-derive the original defect from `review/verdicts/<id>.json` (e.g. palindromic b → Krylov breakdown; indefinite matrix; removed-API import). Confirm the cleaned data no longer exhibits it (e.g. compute eigenvalues / Krylov rank / try the import yourself).
8. **Regenerated target is valid**: write your OWN reference implementation (do not copy the cleaner's), run it on the cleaned test inputs, and check it reproduces the patch targets. Also check the target satisfies the problem's stated output contract (e.g. "orthonormal columns" → max|QᵀQ−I|≈0; shape matches docstring).
9. **Unchanged tests still consistent**: tests/targets that were NOT supposed to change must be byte-identical to the original h5 values, and the convention used for any regenerated target must match the convention of the unchanged tests (so the set stays self-consistent).
10. **No new defect introduced**: the fix didn't create a weak test, a non-deterministic input, an out-of-contract shape, etc.

**D. Audit-log honesty.**
11. `cleaning/log/<id>.md` must accurately and *precisely* describe what was changed. Flag overclaims or imprecise technical statements (e.g. claiming "full reorthogonalization" when the impl used plain three-term recurrence; claiming "reverse-engineered the official convention" when it's only "a standard impl that reproduces the other tests"). The log should not assert more certainty than the evidence supports.
12. For quarantine: the log must give a concrete, reproducible reason (which DOF are unfixable / why reverse-solving fails), not a vague "too hard".

## Calibration
- Distinguish **leakage** (publishable field now tells the solver the answer/convention) from **legitimate spec-tightening** (stating a unit a real solver still must use). Leakage fails; a minimal, necessary, non-solution clarification passes — but prefer the cleaner to have NOT added prose; flag generous additions.
- A correct, minimal fix with a clean publishable file and an honest log = **accept**. Anything in checks A–D failing = **needs_revision** with the exact required change.

## Output (REQUIRED)
Write `cleaning/review/<id>.json` (create dir). Use scratch dir `cleaning/_reviewwork/<id>/`. Never modify `cleaning/problems`, `cleaning/targets`, `cleaning/log`, `review/`, `data/`, or `SciCode/`.

```json
{
  "problem_id": "<id>",
  "reviewer_model": "fable",
  "verdict": "accept | needs_revision",
  "checks": [
    {"id": "A1", "name": "no metadata keys", "result": "pass|fail", "evidence": "what you found"},
    ... one per check A1..D12 you ran ...
  ],
  "required_changes": [
    {"severity": "blocker|should-fix|nit", "where": "cleaning/problems/<id>.json general_tests[0]", "issue": "...", "fix": "..."}
  ],
  "independent_repro": "what you ran to verify the fix and target (commands + key numbers)",
  "summary": "2-3 sentences: is this cleaning acceptable as-is; if not, the headline blockers."
}
```
`required_changes` empty ⇔ verdict accept. A clean accept is fine; do not invent issues — but leakage and general_tests desync are common and must be caught.
