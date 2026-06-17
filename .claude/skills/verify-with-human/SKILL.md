---
name: verify-with-human
description: Use when correcting or cleaning a dataset/artifact through human-in-the-loop, one-item-at-a-time review, where every change the human approves MUST provably land in the released artifact and the consumer (eval/training) must be guaranteed to use the corrected version. Establishes decision-as-data, single-source-of-truth, derive-only artifacts, a bidirectional verify gate, and manifest-bound consumption — the discipline that prevents "reviewed but never landed / shipped stale" desync bugs.
version: 1.0.0
author: hsh
license: MIT
tags: [Data Cleaning, Human-in-the-loop, Dataset Release, Verification, Reproducibility]
dependencies: []
---

# Verify-With-Human: per-item review that provably lands

A discipline for human-reviewed correction of a dataset (or any structured
artifact set) where the failure you are guarding against is **not** wrong
judgement — it is the *gap between a decision and its materialization*: the
human approves a change, but it never reaches the released file, or it reaches
one artifact (e.g. the target) while a coupled artifact (e.g. the prompt) stays
stale, or the consumer silently runs on the old data.

> War stories this prevents: a text fix lived only in a per-problem file and the
> release was built by copying a *stale* sibling; a target patch landed in the
> binary while its prompt did not; an eval ran for hours against an h5 that
> predated the fix. Each looked "done" and wasn't.

## When to use

- Cleaning/correcting a benchmark, dataset, or config set with a human approving
  changes item by item.
- Any time approved edits must be auditable AND guaranteed present in the output.
- Re-releasing a versioned artifact where "did the fix actually ship?" must be
  answerable mechanically, not by memory.

Skip for: one-off edits with no release artifact, or fully-automated transforms
with no human gate.

## The five invariants (rigid — do not relax)

1. **Single source of truth (SSOT).** Each item has exactly one canonical,
   human-readable source file holding its full state. All other forms are
   *derived*. Never edit a derived artifact by hand; never build a release by
   copying a sibling that might be stale.
2. **Decision-as-data.** Every approved change is recorded as a structured
   ledger entry — `{id, field, before, after, verdict, reason, round}` — at the
   moment of approval, and applied to the SSOT immediately. Decisions never live
   only in conversation or memory.
3. **Derive-only.** The released artifacts (flattened jsonl, binary blobs, etc.)
   are ALWAYS regenerated from the SSOT by a deterministic, idempotent script.
   Re-running from a clean baseline + ledger yields byte-identical output.
4. **Bidirectional verify gate.** A script asserts, and blocks release unless:
   - *forward*: every ledger `after` is present in the SSOT and its `before` is
     gone → catches missed/incorrect edits;
   - *reverse*: every field that changed vs the previous release has a matching
     ledger entry → catches stray/accidental edits;
   - *coupling*: artifacts that must move together either both changed or both
     unchanged (e.g. a "prompt-only" round must leave targets/binary md5
     untouched);
   - *integrity*: syntax-parse any code fields; re-run the gold/self-test on
     affected items.
5. **Manifest-bound consumption.** A `manifest.json` records the md5 of every
   released file. The consumer (eval/training) verifies file md5 == manifest at
   startup and **errors out** on mismatch. You can never silently run on stale data.

If any invariant cannot hold, stop and surface it — do not ship.

## Canonical layout

```
<release_dir>/
  items/<id>.json         # SSOT: full per-item state, canonical field order
  patches/<id>.json       # SSOT for any coupled binary-derived data (optional)
  <release>.jsonl         # DERIVED from items/*.json — never hand-edited
  <binary blobs>          # DERIVED — usually gitignored, rebuilt by script
  manifest.json           # version + md5 of every released file + ledger hash
ledger/<round>.jsonl      # decision-as-data, one entry per approved change
tools/
  apply_decision.py       # apply one ledger entry to the SSOT (idempotent)
  assemble.py             # SSOT -> released jsonl + refresh manifest
  verify.py               # the bidirectional gate (D below)
```

## The per-item review loop (report-then-approve, one item at a time)

For each item, in order:

1. **Report.** Show the human the current state and, per candidate change, the
   exact `current → proposed` text with a reason and a nature tag. One item per
   turn. Do not batch silently.
2. **Decide.** The human gives a verdict per change (keep / tighten-to-X /
   move-elsewhere / delete / revert). Ambiguity → ask, don't guess.
3. **Land immediately.** On approval: write the ledger entry AND apply it to the
   SSOT `items/<id>.json` in the same turn. Never let approved changes queue up
   in memory across items.
4. **Eyeball.** Surface the applied diff (a viewer or a focused re-render) so the
   human confirms before moving on.
5. Next item.

Never edit without an explicit in-turn approval. Approval of one item does not
authorize the next.

## Release: run the gate, then ship

After all items are reviewed:

1. `assemble.py` — regenerate the released jsonl (and binaries if in scope) from
   the SSOT; refresh `manifest.json`.
2. `verify.py` — run the full bidirectional gate (invariant 4). **Red light =
   no release.** Fix the SSOT/ledger, re-assemble, re-verify.
3. Bump the version, commit the SSOT + ledger + manifest together (the ledger is
   the audit trail of *why* every byte changed).

## Checklist to instantiate on a new project

- [ ] Define the SSOT file schema and pick its canonical field order.
- [ ] Decide which artifacts are *coupled* (must move together) vs independent.
- [ ] Write `assemble.py` (SSOT → release, idempotent) and prove it reproduces
      the current release byte-for-byte before changing anything.
- [ ] Write `verify.py` with all four gate checks; make it exit non-zero on fail.
- [ ] Add the manifest md5 check to the consumer's startup.
- [ ] Only then begin the per-item review loop.

## Reference implementation

SciCode-Verified (`~/code/ML/SciCode_refine`): SSOT = `scicode_verified/problems/<id>.json`
+ `scicode_verified/targets/<id>.json`; derived = `problems_test.jsonl` +
`test_data_cleaned.h5` (rebuilt by `eval_clean/build_clean_h5.py`, a single flat
pass — no layered/nested builds, which were themselves a desync source). The
"prompt-only" round must leave `targets/` md5 unchanged (coupling check).
