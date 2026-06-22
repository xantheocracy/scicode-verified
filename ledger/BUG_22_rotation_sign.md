# BUG_22 — Problem 22.2 rotation-coefficient SIGN ERROR (CONFIRMED) + harmonic convention + 22.3 conjugation

**Status (2026-06-21):** CONFIRMED bug; **FIXED & LANDED (R3, full-scope; ledger=139, verify ✅, gold
self-test green).** 22.2: last-term sign flipped −2→+2, CS-free harmonic convention pinned, targets
re-frozen to CLAIM A (§3). 22.3: in-plane test2/3/4 re-frozen to their complex conjugates (test1 real,
unchanged), the r1 test4 patch corrected (−0.1553j → +0.1553j), and an off-plane test5 added. The
22.3 imaginary-sign question (§6) is **RESOLVED**: with the corrected 22.2, the contraction (formula A)
equals the physical field-projection oracle to ~1e-15 for all cases → the unique answer is **+imag**
(reviewer was right; the worker's −imag was a conjugation bug in the worker's 22.3 code). Investigation
scratch: `ledger/_fix22_worker/`, `ledger/_fix22_reviewer/`.

> This file SUPERSEDES all earlier framing. Earlier scratch (`_conv22_worker/`, `_conv22_reviewer/`,
> `_ref22full.py`, `_br_fixed.py`, `_oracle.py`, `_audit22_bg/`) is from intermediate, partly-WRONG
> investigations — do not treat as authoritative. The authoritative scratch is `_fix22_worker/` and
> `_fix22_reviewer/`.

## 0. TL;DR verdict (corrects the earlier record)

- The 22.2 recurrence as shipped has a **SIGN ERROR**: the last term must be `+2(Q31+iQ32)`, not
  `−2(Q31+iQ32)`. **The original "flip the sign" suspicion was CORRECT.** The intermediate
  prior-session verdict ("not a sign bug / MINUS is correct / it's only a Condon–Shortley convention
  issue") was **WRONG**.
- The shipped 22.2 targets are **non-physical**: the as-written `−` recurrence produces a
  **NON-UNITARY** `T` that **violates the defining identity** `Y_n^m(d)=Σ_v T_n^{vm}(Q) Y_n^v(Q·d)`
  (residual ~0.27–0.6 under EVERY harmonic convention — checked CS-free, CS-incl, sph_harm).
- The **correct physical** `T` (the unitary Wigner rotation matrix) equals the **flipped (`+`)**
  recurrence values = **CLAIM A** (§3). Verified independently by BOTH agents, each with TWO methods
  (Gauss–Legendre quadrature projection of the identity **and** sympy Wigner-D via ZYZ Euler angles),
  agreeing to 1e-12…1e-15; every degree-n block is unitary and satisfies the identity to ~1e-14.
- **FIX (minimal, keeps the recursion):** flip the sign to `+2(Q31+iQ32)`, pin the harmonic
  convention (§4), and re-freeze the 22.2 targets to CLAIM A. **A Wigner-D rewrite is NOT required.**
- **22.1** is correct, unchanged (its 3 frozen targets reproduce to 1e-9/1e-16).
- **22.3** formula (A) is correct, unchanged; but its targets must be re-frozen (§5): in-plane →
  complex conjugates, plus add an off-plane test.

## 1. Pipeline (what problem 22 computes)
- 22.1 `Rlnm(l,n,m,k,z,N_t)` — axial (z-only) (R|R)_{ln}^m translation coeff. CORRECT.
- 22.2 `Tnvm(n,v,m,Q)` — rotation coefficient T_n^{vm}(Q). **WRONG sign (this bug).**
- 22.3 `compute_BRnm(r0,B,n,m,wl,N_t)` — rotate → axial-translate → rotate-back contraction. Formula
  correct; targets need re-freeze due to the corrected T (+ a convention conjugation).

`T_n^{vm}(Q)` is the Wigner rotation matrix on degree-n spherical harmonics, defined by
`Y_n^m(d) = Σ_v T_n^{vm}(Q) Y_n^v(Q·d)` for all directions d; it MUST be unitary (a rotation
preserves the norm of the field). Physical meaning: it is how degree-n multipole coefficients mix
under the frame rotation used to align r0 with ẑ (the GD/FMM rotate–translate–rotate trick).

## 2. Worker A (ledger/_fix22_worker/) — detailed findings
- Confirmed the as-written recurrence is non-unitary and violates the identity.
- Computed the correct physical T by TWO methods agreeing to ~1e-15: (a) quadrature projection
  `T=∫_S Y_n^m(u) conj(Y_n^v(Q·u)) dΩ`; (b) Wigner-D via ZYZ Euler angles (`Rz(α)Ry(β)Rz(γ)=Q`,
  verified 1e-16), `D[v,m]=e^{-ivα} d^n_{vm}(β) e^{-imγ}`, GD-basis conversion `T_GD=S·D·S⁻¹`,
  `S=diag(s_m)`, `s_m=1 (m≥0), (-1)^m (m<0)`. Result = CLAIM A.
- Verified unitarity + identity to ~1e-15 for all 7 test Q.
- 22.1 axial reproduces all 3 frozen targets to 1e-16.
- 22.3: contraction (with correct T) ≡ field-projection oracle to ~1e-15. Off-plane magnitude
  confirmed.
- **Worker's two debatable conclusions (the reviewer overruled both):** (1) recommended a Wigner-D
  REWRITE claiming the n-increasing recurrence "drops the χ Euler angle / is structurally
  incomplete"; (2) gave the off-plane target as `−0.08823177618756 − 0.11764236825008j`.

## 3. CLAIM A — correct physical 22.2 targets (BOTH agents, two methods each)
| test | (n,v,m) | OLD frozen (wrong) | NEW correct (CLAIM A) |
|---|---|---|---|
| 1 | (2,1,1) | +0.5 | **−0.5** |
| 2 | (5,2,1) | +0.33071891388 | **−0.33071891388307445** |
| 3 | (1,1,0) | +0.61237243570j | **+0.6123724356957937j** (unchanged; m=0) |
| 4 | (3,1,1) | 0.25663381−0.39968348j | **−0.15553096772612052 + 0.24222513055971262j** |
| 5 | (4,3,2) | 0.00896957−0.72395868j | **−0.004170870499078049 + 0.3366424819601227j** |
| 6 | (5,1,3) | 0.10158190−0.14460453j | **−0.23010797435236913 + 0.32756479548480727j** |
| 7 | (4,1,2) | −0.19578436−0.12916493j | **+0.1649896641056365 + 0.10884872539543267j** |

These are exactly the "flipped (+) recurrence" values from the very first BUG_22 table — i.e. the
sign flip was right all along.

## 4. Method = flip the sign (recurrence SALVAGEABLE; reviewer refuted "need Wigner-D")
Reviewer's decisive test (CLAIM B): with a GENERIC `Q=Rz(0.7)Ry(1.1)Rz(γ)` (all three Euler angles
nonzero):
- the m=0 base column is γ-independent — but so is the true Wigner-D m=0 column (1e-17), so this is a
  genuine property, NOT a defect; γ re-enters through the **Q-matrix coefficients in the recurrence
  step**.
- the **flipped (`+2(Q31+iQ32)`) n-increasing recurrence reproduces the full unitary Wigner-D to
  1.7e-14 for BOTH γ=0 and γ=0.9** (m≥0 columns, n≤4), and all 7 CLAIM-A values to ~1e-12. The
  original `−` sign fails by ~1.3.
- Therefore the **only required 22.2 change is the sign flip**; Wigner-D is a valid reference, not
  required. (Caveat: the prompt's recurrence only climbs m upward from m=0; all 7 tests have m≥0 so
  reachable. m<0 columns would need the Hermitian/symmetry relation — not exercised by the tests.)

## 4b. Harmonic convention to pin (exact, unambiguous)
GD: `Y_n^m = (-1)^m sqrt[(2n+1)/(4π)·(n-|m|)!/(n+|m|)!]·P_n^{|m|}(cosθ)·e^{imφ}`, where `P_n^{|m|}` is
the **Condon–Shortley-FREE** associated Legendre. In scipy: `lpmv`/`lpmn` return the CS-INCLUDED P, so
`P_csfree = scipy.special.lpmv(|m|, n, cosθ)/(-1)**|m|`. **Do NOT use `scipy.special.sph_harm`
directly** — it equals this Y for m≥0 but differs by `(-1)^m` for m<0 (the base case queries
`Y_n^{-v}`), so sph_harm reproduces only 1/7 targets. (Earlier worker wording "= sph_harm" was wrong;
reviewer corrected it.)

## 5. 22.3 re-freeze (formula A unchanged)
22.1 axial correct/unchanged. With the corrected T, formula (A) ≡ the convention-free field-projection
oracle. The 4 in-plane targets must be re-frozen to the **complex conjugate** of the current frozen
(test1 real → unchanged), plus ADD an off-plane test. Reviewer's values (each matching its oracle +
contraction + a least-squares reconstruction fit):
| test | r0 | OLD frozen | NEW (reviewer) |
|---|---|---|---|
| 1 | [0.5,0,0] | −0.15530995 | `-0.15530995409608` (unchanged, real) |
| 2 | [0.5,0.5,0] | −0.1525448−0.1525448j | `-0.15254479680485 + 0.15254479680485j` |
| 3 | [0.5,1,0] | −0.14447758−0.28895517j | `-0.14447758329891 + 0.28895516659782j` |
| 4 | [0,0.5,0] | −0.15530995j | `+0.15530995409608j` |
| NEW off-plane | [0.3,0.4,0.5] (B[1,N_t]=1,n=2,m=1,N_t=5,wl=2π) | — | `-0.08823177618756 + 0.11764236825008j` |

## 6. RESOLVED — the 22.3 imaginary sign is +imag (where the 22.3 problem was)
Investigated directly with the CORRECTED 22.2: the 22.3 **formula (A) is correct** — fed the corrected
physical T + a consistent GD convention, the contraction equals the physical field-projection oracle to
~1e-15 for ALL cases (in-plane test1–4 + off-plane). The PROBLEM was purely that the **frozen 22.3
targets were the complex CONJUGATE** of the physically-correct GD-convention values: the original 22.3
output used the conjugate (`e^{-imφ}`) convention, self-consistent only with the WRONG (−2) 22.2. So the
fix is a TARGET re-freeze (no prompt/background/formula change). The sign is **+imag** (contraction ==
oracle == least-squares reconstruction; unique, no ambiguity). The worker's −imag was a conjugation bug
in the worker's own 22.3 code. Off-plane test5 added so this class is detectable (gold self-test: the
conjugate impl fails 4/5, only the real test1 slips through; the off-plane catches it).

## 7. Fix scope when landing (full-scope, target-touching)
- 22.2 `step_background`: flip `−2(Q31+iQ32)` → `+2(Q31+iQ32)`; pin the §4b harmonic convention.
- 22.2 targets: re-freeze test1/2/4/5/6/7 to CLAIM A (test3 unchanged).
- 22.2 tests: optionally add a structural unitarity + defining-identity check.
- 22.3 targets: re-freeze in-plane test2/3/4 to the §5 values (test1 unchanged); add the off-plane
  test — once §6 sign is locked.
- Then: assemble + verify (full scope) + rebuild h5 + gold self-test; consolidate records + memory.
