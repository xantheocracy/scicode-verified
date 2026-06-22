---
name: scicode-finding-verify
description: LIGHTWEIGHT correctness check of SciCode first-pass review findings. This round only asks "is each flagged defect actually correct?" — confirm / refute / uncertain. It does NOT re-do the review or re-author fixes. Be cheap: most findings are trivial and verifiable by reading. Use after scicode-problem-review.
---

# SciCode Finding Verification — v2 (lightweight triage)

You check whether a first-pass reviewer's flagged defects are **correct**. That's it. You are NOT re-reviewing the problem and NOT writing new fix proposals — the first pass already recorded a `suggested_fix` for each finding. Your output per finding is a verdict: **confirmed / refuted / uncertain**, plus (only when needed) a one-line reason.

**Spend tokens in proportion to doubt.** Most findings are trivial (a typo, a truncated sentence, a zero-param header, a removed import) and are verifiable by *reading*. Do not run code, re-implement solutions, or open the h5 unless a specific claim genuinely requires it. A whole problem should usually cost a handful of tool calls, not dozens.

## Inputs
- First-pass findings (what you audit): `review/findings/<ID>.json` — each finding has `step_number, defect_type (D1–D12), severity, confidence, evidence, suggested_fix`.
- Problem data: `review/problems/<ID>.json`.
- First-pass scratch (REUSE it, don't redo): `review/work/<ID>/` may already hold the reviewer's implementations and reproductions.
- Only if you must run something: `python3 review/tools/steptest.py --problem <ID> --step <N.k> --code f.py` (joint mode = official scoring). Defect taxonomy reference: `.claude/skills/scicode-problem-review/SKILL.md` (read only if a defect code is unclear).

## How to check, by tier — pick the cheapest that settles it

**Tier A — read-only (most findings).** For D1 (signature), D10 (doc contradiction), D12 (dependency drift), truncated/corrupted text, and obvious D8 (e.g. "target is all zeros so zeros pass"): the finding quotes specific text or a specific fact. **Verify the quote is accurate against `review/problems/<ID>.json` and the logic follows.** Examples: D1 → does the header's param count really mismatch the test call? (read both). D10 → do the two quoted sentences really contradict? (read both). D12 → is the imported name actually gone in this env? (one `python -c "import X"` at most). No solution code, no steptest.

**Tier B — at most one quick command.** For D4 (unstated convention), D8 (weak test), D9 (cross-step/order): usually one check settles it — e.g. for D8 "trivial impl passes", write a 3-line stub and run steptest once; for D4, if the reviewer already left a passing/failing impl in `review/work/<ID>/`, just re-run it rather than re-deriving. One steptest invocation, reusing prior scratch.

**Tier C — reproduce (rare; only disputed numeric targets).** For D6/D7/D2 where the *target value itself* is claimed wrong/irreproducible AND it's blocker/major: do ONE reproduction, **reusing `review/work/<ID>/` scratch** if present. Do not re-derive a full reference implementation from scratch if the reviewer already did — confirm their key number, don't rebuild their work.

## Verdict rules
- **confirmed**: the quote/logic checks out (Tier A) or your one reproduction reproduces the reviewer's key result (Tier B/C).
- **refuted**: the quote is inaccurate, the "missing" info is actually present/derivable, the claimed convention is wrong, or the number doesn't reproduce. Say in one line why. Refuting a false alarm is the main value you add — look for it actively, especially on D4 "ambiguity" claims (often resolvable from docstring/var-names/test magnitudes) and on severity inflation. **Weigh CUMULATIVE CONTEXT:** the first pass systematically over-flagged D4s by ignoring that problems are cumulative — before confirming a "convention unstated" defect, check whether a prior step already built the operator/object to reuse, or a neighboring step handles the complementary case (so this step's scope is implied). If the cumulative structure makes the target's choice the natural one, refute or downgrade to minor (e.g. 13.8: reuse partial_derivs_vec from 13.1; outer faces only because 13.7 did the inner symmetry faces).
- **uncertain**: you couldn't settle it cheaply and it would need real compute / the authors' reference / domain expertise. Say in one line what would settle it. Don't burn tokens forcing a verdict.
- **Severity recalibration**: if the defect is real but the first pass over/under-stated severity, note `revised_severity`. (A genuine defect that only a pedantic reading hits is `minor`, not `blocker`.)

## Don't
- Don't re-author fixes — the first pass's `suggested_fix` stands; only flag (one line) if you think that proposed fix is *wrong*.
- Don't hunt for new defects beyond a quick sanity glance. If something glaring was obviously missed, add it to `missed_defects` in one line — but this is not a re-review; do not go looking hard.
- Don't run heavy simulations. If a claim needs >1 min of compute to check, mark it `uncertain` and move on.
- Never modify `review/problems/`, `review/findings/`, `data/`, or `SciCode/`. Scratch (if any) in `review/work/<ID>/verify/`.

## Output (REQUIRED) — write `review/verdicts/<ID>.json` BEFORE your final summary
```json
{
  "problem_id": "<ID>",
  "verifier_model": "fable",
  "n_confirmed": 0, "n_refuted": 0, "n_uncertain": 0,
  "verdicts": [
    {"step_number": "N.k", "defect_type": "D1..D12",
     "verdict": "confirmed|refuted|uncertain",
     "tier": "A|B|C",
     "revised_severity": "blocker|major|minor|null",
     "fix_kind": "prompt_edit|doc_edit|header_edit|test_edit|tolerance_change|target_regen|step_drop|env_pin|null",
     "one_liner": "verdict reason; for refuted/uncertain say WHY in this line"}
  ],
  "missed_defects": [],
  "summary": "1-2 sentences: how many confirmed/refuted/uncertain, and is the problem fixable to fair."
}
```
`fix_kind` = the category of the first pass's suggested_fix you agree applies (copy its intent; don't redesign). Keep `one_liner` short. An empty `missed_defects` is expected and fine.
