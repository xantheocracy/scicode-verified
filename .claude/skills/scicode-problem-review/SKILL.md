---
name: scicode-problem-review
description: Protocol for deep-reviewing ONE SciCode benchmark problem for data defects (signature mismatches, unsolvable steps, ambiguous units/conventions, broken targets). Use when auditing SciCode problem quality.
---

# SciCode Problem Review Protocol — v3
<!-- v2: updated after batch 1 (problems 1-20, 75 findings). Changes: Check 0 (dependency drift, D12); joint-vs-isolate test modes; pattern library from batch-1 recurrences; trivial-impl probe codified; duplicate-target check. -->
<!-- v3: updated after batch 2 (problems 21-30, 36 findings). Added 5 patterns: conjugate/inverse-direction targets, exact ==0 asserts, float-noise targets, out-of-contract test inputs, target magnitude vs atol. -->

You are reviewing ONE SciCode problem for **benchmark data defects**. SciCode scores a model per sub-step by running `assert np.allclose(f(...), target)` where `target` is a frozen numeric value in an h5 file. Your goal: find every way the `(prompt, test_cases, target)` triple could **wrongly score a competent solver** — either failing a correct solution (false negative) or passing a wrong one (false positive).

Known defect examples from prior measurement (what you are hunting for):
- A sub-step that is **factually impossible** to solve from the prompt as written.
- `function_header` parameter count/order **does not match** how `test_cases` call the function.
- **Units not specified** (or convention ambiguous), so a correct-but-differently-unit'd implementation fails the frozen target.

## Inputs

- **Problem file**: `review/problems/<ID>.json` — one JSON object:
  - `problem_name, problem_id, split` (`dev`|`test`), `problem_description_main`, `problem_background_main`, `problem_io`, `required_dependencies`, `sub_steps[]`, `general_tests` (= duplicate of last step's test_cases; ignore), `general_solution` (dev only).
  - `sub_steps[i]`: `step_number, step_description_prompt, step_background, function_header, return_line, test_cases[]`, `ground_truth_code` (**dev split only**; `null` on test split).
- **Frozen targets**: `SciCode/eval/data/test_data.h5`.
- **Test runner** (use this; do not hand-roll): from project root
  `python3 review/tools/steptest.py --problem <ID> --step <N.k> --code your_impl.py [--use-gold] [--test i] [--isolate] [--timeout 120]`
  - `--use-gold` (dev only) runs the official cumulative gold through that step's tests.
  - `--code FILE` runs YOUR file (must contain this step's function + any previous-step functions it calls; dependencies are auto-prepended).
  - **Default = joint mode = official harness behavior**: all test cases concatenated into ONE script with a shared namespace (variables from test i are visible to test i+1). The OFFICIAL pass/fail verdict is joint mode's verdict.
  - `--isolate` runs each test in its own subprocess — diagnostic only, to localize which test fails. A NameError that appears ONLY under --isolate is not an official failure (but IS a minor D9 finding: test-case cross-contamination).
  - Exit 0 = pass. Prints PASS/FAIL with traceback tails.
- To inspect a target's raw shape/value:
  ```python
  import sys; sys.path.insert(0, 'SciCode/src')
  from scicode.parse.parse import process_hdf5_to_tuple
  t = process_hdf5_to_tuple('<step_number>', <n_tests>, 'SciCode/eval/data/test_data.h5')
  ```

## Known facts — do NOT re-report these as new discoveries
- Steps **13.6, 62.1, 76.3** are officially skipped by the harness; they have **no h5 target** (steptest refuses them). Review their prompt text statically only.
- Confirmed defects already on file: **78.3** (output shape depends on `time.time()` wall-clock → non-deterministic), **70.8** (test 4 ill-conditioned, default `np.allclose` tol too tight), and all batch-1 findings in `review/findings/{1..20}.json` (problems 1–20 are DONE — see `review/SUMMARY_batch1.md`).
- Problems **2 and 28**: `required_dependencies` import `scipy.integrate.simps`, removed in scipy ≥ 1.14 → crashes before any solver code runs (D12).
- Environment is numpy 2.2.6 / scipy 1.15.2; gold was authored under numpy 1.x. Treat tiny numeric misses (relative < ~1e-6) as fragility, not wrong targets.
- Gold passing does NOT mean defect-free: e.g. 19.1's header is `def tensor():` (no params) while tests call `tensor([0,1],[0,1])` — gold redefines the function, but the header is what a model is told to implement. The header/prompt is the contract under review.

## Defect taxonomy (use these codes)

| Code | Name | Definition |
|---|---|---|
| D1 | signature_mismatch | `function_header` params vs how `test_cases` actually call it (arity/order/defaults) |
| D2 | unsolvable_step | Required equation/definition/constant not derivable from prompt+background+docstring+previous steps |
| D3 | ambiguous_units | Unit system / scale unstated and ≥2 reasonable choices give different numbers |
| D4 | ambiguous_convention | Sign, normalization, ordering, indexing, endpoint, or definition convention unstated |
| D5 | nondeterministic | Output depends on timing, unseeded randomness, dict/set order, hardware |
| D6 | fragile_tolerance | Correct solutions fail `np.allclose` default tol due to ill-conditioning / chaotic dynamics |
| D7 | target_anomaly | h5 target shape/dtype/value inconsistent with the spec'd return (or plain wrong) |
| D8 | test_weakness | Wrong implementations would also pass (degenerate/trivial target, unconstraining tests) |
| D9 | dependency_break | Step k's test relies on prior-step behavior the prior step's spec doesn't guarantee |
| D10 | prompt_contradiction | Docstring/description/background contradict each other |
| D11 | missing_target | h5 target absent for a scored step (other than 13.6/62.1/76.3) |
| D12 | dependency_drift | `required_dependencies` (or an API the spec forces) is broken on modern library versions — crashes before any solver code runs |

Severity: **blocker** = no correct solution can pass (or any wrong one passes); **major** = solvable only by guessing the authors' unstated choice; **minor** = cosmetic/doc issue unlikely to flip scores.

## Procedure — per sub-step, in order

0. **Dependency-drift check (D12)** — once per problem, FIRST: `python3 -c "exec(open(...).read())"` the `required_dependencies` string. If it crashes on the current environment, that is a blocker for the whole problem (the harness prepends it to every step's script). Also flag imports that are deprecated-but-working.
1. **Signature check (D1)**: extract the params from `function_header`; find every call of the function in this and later steps' `test_cases` and in later steps' prompts; compare arity/order. Watch for the recurring **empty-header pattern**: `def f():` with zero params while tests call `f(a, b)` (seen in 11.1, 11.3, 19.1).
2. **Spec completeness read (D2/D3/D4/D10)**: list every symbol, constant, unit, and convention an implementation needs; verify each is defined *somewhere reachable* (step prompt, docstring, problem description, background, a previous step). For every physical quantity ask: is the unit system derivable? Calibration rule: it is only a defect if a competent domain scientist could NOT infer the intended choice — docstrings, variable names, and test-case magnitudes often disambiguate; check them before flagging. **CUMULATIVE CONTEXT (critical, easy to miss):** problems are cumulative — by step N the solver has already built steps 1..N-1. Before flagging a "convention" as unstated, check whether (a) a prior step already built the operator/object this step should reuse (reusing it is the natural choice, not an ad-hoc new scheme), or (b) a neighboring step handles the complementary case so this step's scope is implied by elimination. If the cumulative structure makes the target's choice the consistent one, it is the intended design → minor or no-defect, NOT major. (Worked example: 13.8 outgoing_wave's "unstated discretization" is fixed by reusing partial_derivs_vec from 13.1 and applying only on outer faces because 13.7 already did the inner/symmetry faces.)
3. **Determinism scan (D5)**: anything timing-, randomness-, order-, or hardware-dependent in what the prompt requires or the test asserts? (random without seed, `time.*`, iteration over sets/dicts, optimization with random init, …)
4. **Target inspection (D7/D8/D11)**: load the h5 targets; check count == len(test_cases), shape/dtype plausible vs the documented return, and look for degenerate targets (all-zeros, empty, nan) that a wrong solution would match. Also compare targets **pairwise across the step's tests**: identical targets for different inputs expose decoy parameters or copy-pasted tests (problem 2: d=4 and d=2 give bit-identical targets). For any degenerate target, run the **trivial-impl probe**: does `np.zeros`/`np.ones`/identity pass? (problems 7.1, 10.10: all-zero targets, zeros() passes).
5. **Dynamic verification**:
   - **dev split**: `steptest --use-gold`. Expected pass. On fail, root-cause it (defect in test/target/gold? version drift?).
   - **test split**: implement the step yourself in `review/work/<ID>/step_<N.k>.py` — best literal-reading expert attempt — and run steptest. **PASS** → step is solvable and consistent; record it. **FAIL** → investigate before concluding: try the plausible alternative interpretations (other unit scale, other sign/normalization, other return shape). If an alternative passes, that's confirmed **D3/D4** (report WHICH interpretation the target actually encodes — that's the fix). If nothing passes after honest attempts, report suspected **D2/D7** with your attempts as evidence.
6. **Test-strength spot check (D8)**: would an obviously-wrong implementation pass? (e.g., return zeros / identity / unsorted)

## Pattern library — recurring defects confirmed in batch 1 (check each explicitly)

- **Empty/short header (D1)**: `def tensor():` called as `tensor(a, b)`. Check every header against every call.
- **1-based vs 0-based indexing (D4)**: quantum-info style problems follow QETLAB's 1-based subsystem indices without saying so (11.4/11.8/11.9). Probe both bases if any index params exist.
- **Order/sign conventions (D4)**: row ordering of generated lattices/grids (10.2), sign of pairwise displacement vectors (10.3), whether reciprocal vectors include the 2π factor (10.6). If the docstring doesn't pin it, try both and see which matches the target.
- **Cross-step order sensitivity (D9)**: step k's test compares order-INsensitively (set/sorted/`cmp_tuple_or_list`) but step k+1 consumes step k's output positionally → a spec-compliant step-k implementation breaks step k+1 (10.7). When a step's test is order-insensitive, check downstream consumers.
- **Mid-stage targets (D9/D7)**: a target that matches an INTERMEDIATE internal stage of the reference algorithm rather than the documented final output (13.12: ICN integrator's second intermediate stage). If your correct implementation misses, diff against plausible intermediate states.
- **Hidden seeds & statistical asserts (D5/D6)**: tests that call `np.random.seed(...)` around stochastic solver code (14.1 — solver's own RNG consumption pattern becomes part of the spec), or unseeded statistical acceptance bands (14.2 — inherently flaky).
- **Tolerance blind spots (D8/D6)**: parts of the target numerically too small relative to `np.allclose` rtol·|target| to constrain anything (15.1 diagonal imaginary parts; 16.2 second-order eigenvalue shifts below tol).
- **Corrupted constants in prompt (D2/D10)**: physical constants stated wrongly/corrupted in the text (15.2 "reduced Planck's constant" value). Dimension-check every numeric constant the prompt supplies.
- **Test-case cross-contamination (minor D9)**: a test case referencing variables defined only in an earlier test case of the same step — passes officially (joint script) but is a data smell; report minor.
- **Conjugate / inverse-direction targets (D7)**: when a formula has two "sides" or directions (re-expansion, transforms, adjoints), the reference code may have contracted the wrong side — targets bit-match the conjugate/inverse of the correct value (22.3). Cross-validate with an independent method (quadrature projection, direct definition) before trusting either.
- **Exact `== 0` asserts (D7/D6)**: a test gating on a float being exactly zero is fragile, and the zero may itself be an artifact of the reference code's unjustified pruning (22.3 test 4: physical value 0.2177j, gold returns 0 via l ≥ |m| pruning).
- **Float-noise targets (D6)**: targets dominated by roundoff amplification (finite differences with 1/δ² scaling, catastrophic cancellation) encode the AUTHOR's evaluation order, not mathematics — algebraically equivalent reformulations fail (30.3). If your correct impl misses by ~the discretization-noise scale, test an alternative evaluation order.
- **Out-of-contract test inputs (D4)**: tests feeding shapes/types outside the documented contract (29.1: docstring says "N*1 array", tests pass 4×2 and 3×2×2), with an unstated generalization (flattened norm) required to pass.
- **Target magnitude vs atol (D8)**: any target with |value| ≪ 1e-8 is unconstraining under default `np.allclose` (atol=1e-8) — zeros pass (21.2: target 4.36e-27). Check every target's magnitude against the tolerance actually applied.
- **Mixed-precision constants (D2/D3)**: targets reproducible only with a specific inconsistent constant set (21.3: 2-sig-fig e together with 10-digit CODATA ħ). When constants matter, grid-search standard constant sets and report which one the target encodes.

**Time-boxing**: cover ALL steps with checks 1–4 (cheap, static). Run check 5 on: every step flagged by 1–4, every dev step (gold is one command), and on test split at minimum the first step, the last step (it integrates everything), and any step a later step depends on heavily. Cap each test run at 120s (`--timeout`); note if a test looks like it needs the official 1800s. For huge problems (e.g. 15 steps) prefer breadth over perfection.

## Rules

- Work scratch files go in `review/work/<ID>/`. **Never modify** `review/problems/`, `data/`, or anything under `SciCode/`.
- Be calibrated, not alarmist: a missing unit that is obvious from context (e.g., docstring says "in nm") is NOT a defect. Cross-check against the test-case input magnitudes before flagging D3.
- Quote exact prompt/docstring text in evidence. Findings must be actionable.

## Output (REQUIRED)

Write `review/findings/<ID>.json`:

```json
{
  "problem_id": "<ID>",
  "split": "dev|test",
  "reviewer_model": "fable",
  "steps_reviewed": <int>,
  "steps": [
    {"step_number": "N.k", "static_ok": true,
     "dynamic_status": "pass|fail|partial|skipped|not_attempted",
     "notes": "one line"}
  ],
  "findings": [
    {"step_number": "N.k", "defect_type": "D1..D11", "severity": "blocker|major|minor",
     "confidence": "high|medium|low",
     "evidence": "exact quotes + test output proving it",
     "suggested_fix": "concrete change to prompt/test/target"}
  ],
  "overall_assessment": "2-4 sentences: is this problem fair to score as-is?"
}
```

An empty `findings` list is a perfectly good outcome — do not invent issues to seem useful.
