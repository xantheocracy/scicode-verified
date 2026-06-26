# DEFERRED (round6 / test-redesign) — #39.1 tests a convention-dependent intermediate matrix

**Status:** DEFERRED. R7 added a prompt-only clarification (39.1 docstring names the amplitude
transfer matrix; 39.3 prompt pins the n1-embedding boundary condition) that makes the problem
well-posed. This note records the DEEPER, target-touching concern for a future round.

## Issue
`39` Reflection_spectra_for_a_DBR, step **39.1** `matrix_elements` is scored by
`np.allclose(matrix_elements(...), target)` — i.e. it compares the 2x2 transfer MATRIX itself.
The matrix form is **convention-dependent**: the gold uses the amplitude transfer matrix
(B12.B21 per period), but the E-H characteristic matrix ([[cos, i sin/n],[i n sin, cos]]) is an
equally-valid representation of the same physics. A model using E-H fails 39.1 even if its final
physical reflectance R were correct.

Verified: no-bg deepseek-pro used a fully self-consistent E-H framework (E-H matrix + Chebyshev M^N
+ valid r=(A n1 + B n1n2 - C - D n2)/(A n1 + B n1n2 + C + D n2)); it is NOT wrong physics, just a
different convention + a different (also reasonable) boundary assumption (incident n1 / exit n2).

## Ideal fix (target-touching — not done here)
Score only the **physical observable** (the reflectance R, 39.3) with a pinned boundary condition,
and stop scoring the convention-dependent intermediate matrix at 39.1 (or test 39.1 only via a
physical consequence). This removes the representation dependence entirely. Changing what 39.1
scores touches test_cases / targets -> belongs to a dedicated test-redesign round, not a prompt-only
round.

## Done in R7 (prompt-only, sufficient for well-posedness)
- 39.1 docstring Output: defines M as "the amplitude transfer matrix of one n1/n2 period, relating
  the forward- and backward-propagating wave amplitudes" (excludes the E-H route).
- 39.3 prompt: "Assume light is incident from the n1 medium and the stack is embedded in that same
  n1 medium" (pins the boundary condition so R is unique).
