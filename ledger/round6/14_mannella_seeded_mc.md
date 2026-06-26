# DEFERRED (round6 / MC-test-redesign track) — #14.1 seeded exact-reproduction over-specification

**Status:** DEFERRED, NOT fixed. Found during the R7 no-bg-underspecification review (2026-06-26).
**Do NOT fix in a prompt-only round — the fix is target-touching (changes test_cases).**

## Problem
`14` Brownian_motion_in_the_optical_tweezer, step **14.1** `harmonic_mannella_leapfrog`.
Test is a **seeded exact-reproduction** check:
```
np.random.seed(0); assert np.allclose(harmonic_mannella_leapfrog(...), target)
```
This pins not just the physics but the gold's exact **RNG-consumption protocol** — one
`np.random.normal(0, sqrt(dt))` draw per step, placed in the v-update, scaled by `sqrt(2/taup)*vrms`
(Mannella leapfrog). A physically-correct integrator with a *different but valid* noise discretization
fails, because it consumes the seeded random stream in a different order/count.

## Evidence (verified from code, deepseek-v4-pro)
- gold `review/work/14/step_14.1.py`: 1 draw/step, `dW = np.random.normal(0, sqrt(dt))`
  (its own comment: "one legacy np.random.normal draw per step").
- with-bg run1: 1 draw/step (transcribes the background's exact Mannella scheme) -> reproduces the
  seeded gold trajectory -> PASS (with-bg 14.1 = P/P/P).
- no-bg run1: **2 draws/step** (two half-step kicks). Its TOTAL noise variance is CORRECT
  (2 * (vrms*sqrt(dt/taup))^2 = 2*vrms^2*dt/taup = the gold single-kick variance), i.e. the
  fluctuation-dissipation physics is right — but the seeded trajectory differs -> FAIL
  (no-bg 14.1 = F/P/F).
- So with-bg passes 14.1 only by COPYING the gold's exact RNG protocol from step_background, not by
  "understanding the physics better." The test rewards transcription of an implementation detail.

## Why deferred (not an R7 prompt fix)
- with-bg passes 14.1 AND 14.2 cleanly (3/3) -> **no with-bg false-fail** (paper's core concern is
  unaffected); no urgency.
- The proper fix is to make 14.1 **statistical/tolerance-based** like 14.2 (which compares the MSD to
  the analytical formula within 5% and is RNG-protocol-agnostic). That changes test_cases (and the
  frozen target), so it belongs to the dedicated **MC-test-redesign round**, not a prompt-only round.

## Related
Same class as the seeded-MC over-specification in problems **46, 50** (see memory
scicode-mc-test-redesign-track). Keep the pin (current seeded test) until the redesign round; redo
14.1 + 46 + 50 together as one target-touching MC round.
