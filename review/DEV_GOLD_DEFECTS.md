# SciCode Dev-Set Gold-Grounded Defects

**Exhibit for: "SciCode needs data cleaning."**
Reproduced 2026-06-15, env `numpy 2.2.6 / scipy 1.x`, harness `audit/gold_self_test.py`.

## Why the dev set is the strongest exhibit

The 15-problem dev split ships the **official reference solution (`ground_truth_code`) for all 50 sub-steps**. That removes every escape hatch: a defect here is not "a model misread the prompt" — it is the **benchmark's own reference solution failing or only-accidentally-passing its own tests**. Each finding below is demonstrated by running the official gold code itself.

## Method (two layers — the second is essential)

1. **Gold self-test** — run each problem's cumulative gold against its own `test_cases`/targets (the official scorer's exact assembly). A failure = definitively broken data. → caught **78.3, 70.8**.
2. **Static red-flag scan + isolation re-run** — scan gold for non-determinism (`time.time`, `np.random`) and tests for extreme-magnitude inputs; re-run suspect stochastic steps in isolation. → caught **47.4, 44.3**, which the self-test *passes*.

**Key point: the gold self-test is only a LOWER BOUND.** Targets are generated *by* the gold, so a buggy/non-deterministic gold can still "pass" by reproducing its own artifact. 2 of the 4 defects are invisible to self-testing alone.

## The 4 defects (4 / 15 dev problems = 27%)

### 78.3 — `Chaotic_Dynamics_Pendulum` · non-determinism (wall-clock)
The gold selects the "optimal" timestep by
```python
combined_metric = gte_norm * np.sqrt(elapsed_time)   # elapsed_time = time.time() measurement
```
then returns the trajectory at that dt. **Which dt wins depends on how fast the machine runs**, so the output *shape itself* is machine-dependent. With `num_timesteps=2`, dt∈{0.001→traj `(10001,2)`, 10→traj `(2,2)`}.
**Proof:** gold's own run produces `(10001,2)` while the frozen target is `(2,2)` → `ValueError: operands could not be broadcast together (10001,2) (2,2)`. **Gold fails its own test.** No deterministic correct answer exists.

### 70.8 — `neutrino_oscillation` · numerical ill-conditioning
Tests 0–2 match to Δ~1e-15. **Test 3** uses a realistic baseline `L = 1.611792e22` with the Hamiltonian scaled by `1e-9`, so the oscillation phase `H·L ~ 1e13` exceeds float64's ~15–16 significant digits.
**Proof:** the gold's OWN output is `0.665031` where the stored target is `0.665132` — `max|Δ| = 1.8e-4`, beyond `np.allclose` default tol (rtol 1e-5). **Gold fails its own test 3.** The target is not reproducible at the asserted precision.

### 47.4 — `Internal_Energy` (LJ MCMC) · unseeded / non-isolated RNG  *(self-test MISSED)*
The MCMC gold draws `np.random.randint/normal/random` with **no seed inside the function**. Only **test 0** sets `np.random.seed(1024)`; **test 1 and test 2 set no seed** and pass *only* because the official harness runs all tests in one process, so they inherit the global RNG state left after test 0's 1000-step run.
**Proof:**
```
test1 in sequential context (after test0):  PASS   max|Δ| = 9e-13
test1 isolated (same seed 1024, alone):     FAIL   max|Δ| ≈ 3950
test1 unseeded:                             FAIL   max|Δ| ≈ 3930
```
The stored targets are artifacts of one specific execution trace; any reordering / isolation / numpy-RNG change breaks them.

### 44.3 — `two_mer_entropy` · gold violates its own documented contract  *(self-test MISSED)*
The header documents input `d0` = "concentration of 2-mers at time 0". The gold's first line **overwrites it**:
```python
d0 = np.ones((Z, Z)).flatten()*0.01   # the passed-in d0 is discarded
```
Test 0 passes `d0 = 0.5`, but the target reflects `0.01`, so any implementation that *honors the documented input* fails.
**Proof (test 0, d0=0.5):**
```
gold (ignores d0, uses 0.01)  vs target : PASS  (Δ 4e-16)
faithful (uses d0=0.5)        vs target : FAIL  (Δ 0.571)
gold vs faithful                        : Δ 0.571   → d0 is provably ignored
```
The benchmark **rewards the reference bug and penalizes a spec-faithful solution.**

## Taxonomy

| Defect class | Steps | Detectable by gold-self-test? |
|---|---|---|
| Non-determinism (wall-clock / unseeded RNG) | 78.3, 47.4 | 78.3 yes; 47.4 **no** |
| Numerical ill-conditioning (extreme magnitudes) | 70.8 | yes |
| Gold violates documented contract | 44.3 | **no** |

## Implication for the 65-problem test split

The test split ships **no** gold, so the airtight gold-self-test is unavailable there — yet the *same defect classes* occur. The full per-problem agent review (`review/DEFECT_REGISTRY.md`) independently flags the identical dev set (44, 47, 70, 78) and finds confirmed blocker steps in **34/80 problems (42.5%)**. The dev set, where we *can* prove each defect with the official solution, is the rigorous foundation for that broader claim.

## Reproduce

```bash
python3 audit/gold_self_test.py --data data/problems_dev.jsonl   # 48 pass / 2 fail (78.3, 70.8)
# 47.4 / 44.3 require the isolation / faithful-impl checks shown above (this session's snippets).
```
