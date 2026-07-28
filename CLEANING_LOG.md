# SciCode-Verified — Cleaning Log

A consolidated, human-readable record of how the **SciCode** benchmark was
audited and corrected into **SciCode-Verified**. The machine-readable,
per-change audit trail lives alongside this file in [`ledger/`](ledger/)
(one JSONL entry per approved edit: `{id, field, before, after, verdict,
reason, round}`); this document is the narrative that ties those rounds
together. Everything here was reproduced from the data — never taken on trust.

**Released artifact (v2):** 64 problems · `scicode_verified/problems_test.jsonl`
+ `scicode_verified/test_data_cleaned.h5` (md5 `2b41a7df40ddc23ce651ec05b8ecb6f8`)
+ `scicode_verified/manifest.json`. Prebuilt data:
[GitHub Release `data`](https://github.com/flyingwagner/scicode-verified/releases/tag/data).

**Scope note.** This log covers the complete 80-problem audit and therefore reports 397 findings
across the development and test splits. The public v2 evaluation release contains 64 problems;
its release-specific taxonomy contains 264 confirmed corrections across 63 problems. Of those,
192 can suppress a correct solution, touching 155 of the 287 scored subproblems. See
[`analysis/`](analysis/) for the release-level machine-readable counts.

---

## 1. Why SciCode needed cleaning — the airtight dev-set exhibit

SciCode scores a model per sub-step with `assert np.allclose(f(inputs),
target)`, where `target` is a frozen numeric value, and it uses **cumulative,
all-or-nothing** scoring: one wrong step fails every downstream step of the
problem. That makes the benchmark acutely sensitive to *data* defects — a wrong
target or an unstated convention silently mis-scores a competent solver.

The **15-problem dev split** ships the official reference solution
(`ground_truth_code`) for all 50 sub-steps, which removes every escape hatch: a
defect there is not "a model misread the prompt" — it is **the benchmark's own
reference solution failing, or only-accidentally-passing, its own tests.** Four
such defects (4/15 dev problems = 27%), each proven by running the official gold
itself:

| Step | Problem | Class | Proof |
|---|---|---|---|
| **78.3** | Chaotic_Dynamics_Pendulum | non-determinism (wall-clock) | gold picks dt via `time.time()` → output *shape* is machine-dependent; gold's own run is `(10001,2)` vs frozen target `(2,2)` → gold fails its own test. |
| **70.8** | neutrino_oscillation | numerical ill-conditioning | test 3 has `H·L ~ 1e13` beyond float64; gold's own output `0.665031` vs target `0.665132` (Δ 1.8e-4 > tol) → gold fails its own test. |
| **47.4** | Internal_Energy (LJ MCMC) | unseeded / non-isolated RNG | tests 1–2 pass *only* because the harness shares one RNG state after test 0's seed; isolated → Δ ≈ 3950. (Invisible to gold self-test.) |
| **44.3** | two_mer_entropy | gold violates its own contract | gold overwrites the documented input `d0` with a hard-coded `0.01`; a spec-faithful impl (honoring `d0=0.5`) fails by Δ 0.571. (Invisible to gold self-test.) |

Two of the four are invisible to a naive gold-self-test (targets are generated
*by* the gold, so a buggy/non-deterministic gold can still reproduce its own
artifact) — which is exactly why the correction process below is layered.

## 2. Method — two-pass audit + a verify-with-human release gate

**Audit (find the defects).** Two passes over all 80 problems:
1. *First pass* — one independent agent per problem, deep step-by-step review
   against a fixed defect taxonomy (below), running the official joint-mode
   scorer and independent reference implementations.
2. *Adversarial re-verify* — a fresh agent re-checks every flagged defect
   (confirm / refute / uncertain), actively killing false alarms — especially
   over-flagged "ambiguous convention" claims that a cumulative reading resolves.

**Defect taxonomy (D1–D12):** signature_mismatch · unsolvable_step ·
ambiguous_units · ambiguous_convention · nondeterministic · fragile_tolerance ·
target_anomaly · test_weakness · dependency_break · prompt_contradiction ·
missing_target · dependency_drift. (This audit followed a fixed, domain-agnostic
review protocol reusable across similar frozen-target benchmarks.)

**Correction (make the fixes provably land).** Every approved change went
through a *verify-with-human* release gate:
- **SSOT** = `scicode_verified/problems/<id>.json` (+ `targets/<id>.json`); the
  released `problems_test.jsonl` and the h5 are **derived**, never hand-edited.
- **Decision-as-data** = a `ledger/<round>.jsonl` entry per approved edit.
- **Bidirectional verify gate** (`tools/verify.py`) blocks release unless every
  ledger `after` is in the SSOT, every SSOT change has a ledger entry, and a
  prompt-only round leaves the target md5 untouched.
- **Manifest-bound consumption**: `manifest.json` records every file's md5 and
  the eval harness refuses to run on a mismatch — you can never silently score
  against stale data.

## 3. What the audit found

Confirmed (adversarially re-verified) defects, classified by the field they
corrupt and therefore which eval mode they affect. SciCode has
`with_background` / `without_background` modes; the **theory/background** field
is only shown in `with_background`, so its defects bite only that mode — every
other field pollutes **both** modes.

| Affected field | Eval mode | 🔴 blk | 🟡 maj | ⚪ min | total |
|---|---|--:|--:|--:|--:|
| Problem description | all modes | 6 | 53 | 38 | 97 |
| Function contract (docstring/header) | all modes | 8 | 52 | 48 | 108 |
| Theory (background) | with_background only | 7 | 25 | 29 | 61 |
| Judge · test cases | all modes | 17 | 35 | 55 | 107 |
| Judge · target value | all modes | 13 | 6 | 3 | 22 |
| Dependency / environment | all modes | 2 | 0 | 0 | 2 |
| **Total** | | **53** | **171** | **173** | **397** |

**336 defects pollute all modes** (🔴46 / 🟡146 / ⚪144); 61 affect only
`with_background`. **34 / 80 problems (42.5%) carry a blocker-level step** (a
correct solution cannot pass, or a wrong one trivially passes) — and because of
all-or-nothing scoring, a single blocker sinks the whole problem's score.

Per-problem map (confirmed defects · blockers · status ✅ clean / 🟡 minor-major
/ 🔴 has blocker):

| # | name | split | steps | def | blk | | # | name | split | steps | def | blk |
|--|--|--|--|--|--|--|--|--|--|--|--|--|
| 1 | CG | dev | 1 | 2 | 0 🟡 | | 41 | Structural_stability_serial_dilution | test | 3 | 1 | 0 🟡 |
| 2 | Gaussian_Beam_Focus | test | 1 | 6 | 3 🔴 | | 42 | multi_quantum_well_lasers_threshold | test | 3 | 2 | 0 🟡 |
| 3 | Gauss_Seidel | dev | 1 | 1 | 0 🟡 | | 43 | two_end_fiber_laser | test | 3 | 3 | 1 🔴 |
| 4 | IncomChol | dev | 1 | 2 | 0 🟡 | | 44 | two_mer_entropy | dev | 3 | 1 | 1 🔴 |
| 5 | Lanczos | test | 1 | 2 | 1 🔴 | | 45 | finite_difference_heat_eq | test | 4 | 7 | 0 🟡 |
| 6 | Spatial_filters_I | dev | 1 | 3 | 0 🟡 | | 46 | helium_atom_vmc | test | 4 | 4 | 2 🔴 |
| 7 | Spatial_filters_II | dev | 1 | 3 | 0 🟡 | | 47 | Internal_Energy | dev | 4 | 7 | 1 🔴 |
| 8 | Spatial_filters_III | test | 1 | 1 | 0 🟡 | | 48 | MEELS_conversion | test | 4 | 3 | 0 🟡 |
| 9 | Weighted_Jacobi | test | 1 | 1 | 0 🟡 | | 49 | nbody | dev | 4 | 6 | 0 🟡 |
| 10 | ewald_summation | dev | 11 | 8 | 0 🟡 | | 50 | Replica_symmetry_breaking | test | 4 | 5 | 1 🔴 |
| 11 | GADC_entanglement | test | 12 | 12 | 0 🟡 | | 51 | SciCode_Example | dev | 4 | 1 | 0 🟡 |
| 12 | Schrodinger_DFT_SCF | test | 14 | 2 | 0 🟡 | | 52 | Shooting_algo_H_atom | test | 4 | 10 | 2 🔴 |
| 13 | Maxwell_Equation_Solver | test | 15 | 7 | 1 🔴 | | 53 | Stochastic_Lotka_Volterra | test | 4 | 3 | 0 🟡 |
| 14 | Brownian_optical_tweezer | test | 2 | 5 | 0 🟡 | | 54 | SUPG | test | 4 | 9 | 2 🔴 |
| 15 | Crank_Nicolson_TDSE | test | 2 | 3 | 0 🟡 | | 55 | Swift_Hohenberg | test | 4 | 7 | 0 🟡 |
| 16 | Davidson_method | test | 2 | 3 | 0 🟡 | | 56 | temporal_niches | test | 4 | 0 | 0 ✅ |
| 17 | linear_tetrahedron | test | 2 | 5 | 1 🔴 | | 57 | 1D_HO_numerov_shooting | test | 5 | 4 | 0 🟡 |
| 18 | NURBS | test | 2 | 4 | 1 🔴 | | 58 | Tolman_Oppenheimer_Volkoff | test | 5 | 8 | 1 🔴 |
| 19 | n_tangle | dev | 2 | 2 | 0 🟡 | | 59 | VQE | test | 5 | 5 | 0 🟡 |
| 20 | phonon_angular_momentum | test | 2 | 3 | 0 🟡 | | 60 | Widom_particle_insertion | test | 5 | 11 | 2 🔴 |
| 21 | Absorption_GaAlAs | test | 3 | 5 | 1 🔴 | | 61 | Xray_conversion_I | test | 5 | 4 | 1 🔴 |
| 22 | Beam_translation_reexpansion | test | 3 | 5 | 2 🔴 | | 62 | dmrg | test | 6 | 3 | 1 🔴 |
| 23 | Blahut_Arimoto | test | 3 | 3 | 0 🟡 | | 63 | Estimating_Stock_Option_Price | test | 6 | 11 | 0 🟡 |
| 24 | Burgers_equation | test | 3 | 5 | 1 🔴 | | 64 | GCMC | test | 6 | 8 | 1 🔴 |
| 25 | CRM_in_chemostat | test | 3 | 2 | 0 🟡 | | 65 | GHZ_protocol_fidelity | test | 6 | 8 | 0 🟡 |
| 26 | CRM_in_serial_dilution | test | 3 | 0 | 0 ✅ | | 66 | kolmogorov_crespi_potential | test | 6 | 8 | 1 🔴 |
| 27 | high_speed_photodetectors | test | 3 | 4 | 0 🟡 | | 67 | LEG_Dyson_bulk | test | 6 | 3 | 0 🟡 |
| 28 | Gaussian_Beam_Intensity | test | 3 | 9 | 1 🔴 | | 68 | helium_atom_dmc | test | 8 | 8 | 2 🔴 |
| 29 | Gram_Schmidt | dev | 3 | 1 | 0 🟡 | | 69 | LEG_Dyson_semi_infinite | test | 8 | 6 | 1 🔴 |
| 30 | helium_slater_jastrow | test | 3 | 2 | 0 🟡 | | 70 | neutrino_oscillation | dev | 8 | 7 | 1 🔴 |
| 31 | independent_component_analysis | test | 3 | 4 | 1 🔴 | | 71 | GADC_rev_coherent_info | test | 9 | 11 | 0 🟡 |
| 32 | Multiparticle_tweezer_array | test | 3 | 3 | 0 🟡 | | 72 | ising_model | test | 9 | 9 | 1 🔴 |
| 33 | chern_haldane_phase_diagram | test | 3 | 5 | 0 🟡 | | 73 | Xray_conversion_II | test | 9 | 9 | 6 🔴 |
| 34 | PN_diode_band_diagram | test | 3 | 4 | 0 🟡 | | 74 | Householder_QR | test | 1 | 1 | 0 🟡 |
| 35 | Quantum_Dot_Absorption | test | 3 | 3 | 0 🟡 | | 75 | graphene_tight_binding | test | 3 | 3 | 1 🔴 |
| 36 | Quasi_Fermi_photo_resistor | test | 3 | 2 | 0 🟡 | | 76 | protein_dna_binding | test | 4 | 5 | 3 🔴 |
| 37 | ray_optics_spherical_aberration | test | 3 | 6 | 0 🟡 | | 77 | Berendsen_thermostat | test | 12 | 11 | 0 🟡 |
| 38 | Reciprocal_lattice_vector | dev | 3 | 2 | 0 🟡 | | 78 | Chaotic_Dynamics_Pendulum | dev | 3 | 4 | 1 🔴 |
| 39 | DBR_reflection_spectra | test | 3 | 2 | 0 🟡 | | 79 | Nose_Hoover_chain | test | 4 | 7 | 3 🔴 |
| 40 | Spliting_Operator | test | 3 | 4 | 1 🔴 | | 80 | Anderson_thermostat | test | 7 | 11 | 3 🔴 |

### Recurring defect shapes (the pattern library)

Empty/short function headers · 1-based vs 0-based indexing · unstated
order/sign/2π conventions · cross-step order sensitivity · mid-stage targets ·
hidden seeds & statistical asserts · tolerance blind spots (target ≪ atol) ·
corrupted constants · conjugate/inverse-direction targets · exact `==0` asserts
· float-noise targets (roundoff fingerprints) · out-of-contract test inputs ·
mixed-precision constants · dependency drift (`scipy.integrate.simps` removed in
scipy ≥ 1.14 kills problems 2 & 28 before any solver code runs). These recurring
shapes, each with concrete confirmed instances, drove the corrections below.

## 4. The correction rounds (see `ledger/` for exact entries)

| Round | entries | Focus |
|---|--:|---|
| **R3** | 139 | Bulk landing of the confirmed corrections into the SSOT (descriptions, headers, test cases, targets) — the main cleanup. |
| **R4** | 17 | Physics deep-fixes: #12 charge density stated "per unit volume" (12.7/12.13); #13 `A_z` parity made vector-consistent (13.9) + cascade. |
| **R5** | 5 | #13 evolution-test redesign (physical inputs + converged RK4 reference, tolerance = algorithm error); no-background under-specification fixes. |
| **R6** | 3 | #12.4 made sign-agnostic; deferred test-redesign notes (#14 seeded-MC, #39 DBR intermediate matrix) recorded in `ledger/round6/`. |
| **R7** | 20 | `without_background` under-specification: surface *load-bearing* data/conventions from background into the visible prompt/docstring (leave derivable physics intact), plus minimal, justified tolerance loosening (#48). |

### Deep single-problem investigations (full write-ups in `ledger/`)

- **`ledger/BUG_13_Az_symmetry.md`** — 13.9 gold `A_z` parity `(+,+,−)` was
  vector-inconsistent → `(−,−,−)`; the fix resolves the whole 13.10–13.15
  cascade, verified with a converged RK4 reference.
- **`ledger/BUG_22_rotation_sign.md`** — 22.2/22.3 beam re-expansion rotation
  sign: targets bit-matched the conjugate of the correct value; fixed with a
  CS-phase-free harmonic and re-frozen targets, cross-checked against an
  independent contraction.
- **`ledger/round6/`** — `14_mannella_seeded_mc.md`, `39_dbr_intermediate_matrix.md`:
  seeded exact-reproduction Monte-Carlo tests that over-specify an RNG protocol;
  slated for a statistical-test redesign in a future target-touching round.

## 5. Where everything lives now / reproduce

| | |
|---|---|
| Released data | `scicode_verified/` (SSOT `problems/` + `targets/`, derived `problems_test.jsonl` + `test_data_cleaned.h5`, `manifest.json`) — also on the GitHub Release `data`. |
| Structured audit trail | `ledger/R3–R7.jsonl` + `ledger/BUG_*.md` + `ledger/round6/`. |
| Eval | `eval_clean/run_deepseek_eval.py` (the runner), `eval_clean/build_clean_h5.py` (rebuild the h5 from the original + `targets/`), `eval_clean/regrade_multienv.py`. |
| Release gate | `tools/assemble.py` (SSOT → jsonl + manifest), `tools/verify.py` (bidirectional gate). |

To rebuild the h5 from source instead of downloading it:
```bash
git clone <SciCode repo> SciCode       # or fetch the original test_data.h5 (hfd.sh)
python3 eval_clean/build_clean_h5.py   # original h5 + scicode_verified/targets/ -> test_data_cleaned.h5
# must reproduce manifest.json's h5_md5: 2b41a7df40ddc23ce651ec05b8ecb6f8
```

---
*Derived from the SciCode benchmark (Apache-2.0). The detailed per-defect
first-pass registry and the per-problem findings/verdicts that backed this
summary are preserved in git history (removed from the working tree in the
repo-tidy commit).*
