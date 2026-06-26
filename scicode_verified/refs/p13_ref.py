"""Faithful reference for SciCode #13 (Maxwell_Equation_Solver), step 13.9 `derivatives`.

Used by eval_clean/build_clean_h5.py (transform `_type: maxwell_az_parity_fix`) to
regenerate the 13.9 target with the corrected A_z inner-boundary symmetry parity.

Provenance / why this is faithful (NOT a single-model artifact):
  - The differential operators (partial_derivs_vec, laplace, gradient, divergence,
    grad_div), the Maxwell grid, symmetry, and outgoing_wave below are our own
    independent reproduction (research_by_problem/13/_p13/13.1-13.8), unchanged.
  - The per-field inner-boundary parities in derivatives() are gold's OWN convention
    (the z-axis magnetic-dipole configuration, σ=(-1,-1,1)). With the BUGGY A_z parity
    (1,1,-1) this reference reproduces the original gold 13.9 target to ~1e-12 on ALL
    SEVEN components (verified). That equivalence is what makes it a faithful gold ref.
  - The ONLY change here is the fix: A_z uses (-1,-1,-1), the value forced by gold's
    own A_x=(1,-1,1), A_y=(-1,1,1) under the polar-vector reflection constraint, and
    equal to gold's own E_z parity (E and A share symmetry per the 13.9 prompt /
    Lorenz gauge). gold's stored A_z=(1,1,-1) is the lone vector-inconsistent value.
    See ledger/BUG_13_Az_symmetry.md.

The build self-checks: with the corrected derivatives, components E_x,E_y,E_z,A_x,A_y,phi
must still match the pre-existing gold target to <1e-9; only A_z (component 5) changes.
"""
import numpy as np
from numpy import zeros, sqrt


def partial_derivs_vec(fct, delta):
    deriv_x = np.zeros_like(fct)
    deriv_y = np.zeros_like(fct)
    deriv_z = np.zeros_like(fct)
    deriv_x[1:-1, :, :] = (fct[2:, :, :] - fct[:-2, :, :]) / (2 * delta)
    deriv_x[0, :, :] = (-3 * fct[0, :, :] + 4 * fct[1, :, :] - fct[2, :, :]) / (2 * delta)
    deriv_x[-1, :, :] = (3 * fct[-1, :, :] - 4 * fct[-2, :, :] + fct[-3, :, :]) / (2 * delta)
    deriv_y[:, 1:-1, :] = (fct[:, 2:, :] - fct[:, :-2, :]) / (2 * delta)
    deriv_y[:, 0, :] = (-3 * fct[:, 0, :] + 4 * fct[:, 1, :] - fct[:, 2, :]) / (2 * delta)
    deriv_y[:, -1, :] = (3 * fct[:, -1, :] - 4 * fct[:, -2, :] + fct[:, -3, :]) / (2 * delta)
    deriv_z[:, :, 1:-1] = (fct[:, :, 2:] - fct[:, :, :-2]) / (2 * delta)
    deriv_z[:, :, 0] = (-3 * fct[:, :, 0] + 4 * fct[:, :, 1] - fct[:, :, 2]) / (2 * delta)
    deriv_z[:, :, -1] = (3 * fct[:, :, -1] - 4 * fct[:, :, -2] + fct[:, :, -3]) / (2 * delta)
    return deriv_x, deriv_y, deriv_z


def laplace(fct, delta):
    lap = np.zeros_like(fct)
    lap[1:-1, 1:-1, 1:-1] = (
        fct[2:, 1:-1, 1:-1] + fct[:-2, 1:-1, 1:-1] +
        fct[1:-1, 2:, 1:-1] + fct[1:-1, :-2, 1:-1] +
        fct[1:-1, 1:-1, 2:] + fct[1:-1, 1:-1, :-2] -
        6.0 * fct[1:-1, 1:-1, 1:-1]
    ) / (delta * delta)
    return lap


def gradient(fct, delta):
    grad_x = np.zeros_like(fct)
    grad_y = np.zeros_like(fct)
    grad_z = np.zeros_like(fct)
    grad_x[1:-1, 1:-1, 1:-1] = (fct[2:, 1:-1, 1:-1] - fct[:-2, 1:-1, 1:-1]) / (2 * delta)
    grad_y[1:-1, 1:-1, 1:-1] = (fct[1:-1, 2:, 1:-1] - fct[1:-1, :-2, 1:-1]) / (2 * delta)
    grad_z[1:-1, 1:-1, 1:-1] = (fct[1:-1, 1:-1, 2:] - fct[1:-1, 1:-1, :-2]) / (2 * delta)
    return grad_x, grad_y, grad_z


def divergence(v_x, v_y, v_z, delta):
    div = np.zeros_like(v_x)
    div[1:-1, 1:-1, 1:-1] = (
        (v_x[2:, 1:-1, 1:-1] - v_x[:-2, 1:-1, 1:-1]) / (2 * delta) +
        (v_y[1:-1, 2:, 1:-1] - v_y[1:-1, :-2, 1:-1]) / (2 * delta) +
        (v_z[1:-1, 1:-1, 2:] - v_z[1:-1, 1:-1, :-2]) / (2 * delta)
    )
    return div


def grad_div(A_x, A_y, A_z, delta):
    grad_div_x = np.zeros_like(A_x)
    grad_div_y = np.zeros_like(A_y)
    grad_div_z = np.zeros_like(A_z)
    delta2 = delta * delta
    four_delta2 = 4.0 * delta2
    grad_div_x[1:-1, 1:-1, 1:-1] = (
        (A_x[2:, 1:-1, 1:-1] - 2.0 * A_x[1:-1, 1:-1, 1:-1] + A_x[:-2, 1:-1, 1:-1]) / delta2 +
        (A_y[2:, 2:, 1:-1] - A_y[2:, :-2, 1:-1] - A_y[:-2, 2:, 1:-1] + A_y[:-2, :-2, 1:-1]) / four_delta2 +
        (A_z[2:, 1:-1, 2:] - A_z[2:, 1:-1, :-2] - A_z[:-2, 1:-1, 2:] + A_z[:-2, 1:-1, :-2]) / four_delta2
    )
    grad_div_y[1:-1, 1:-1, 1:-1] = (
        (A_x[2:, 2:, 1:-1] - A_x[2:, :-2, 1:-1] - A_x[:-2, 2:, 1:-1] + A_x[:-2, :-2, 1:-1]) / four_delta2 +
        (A_y[1:-1, 2:, 1:-1] - 2.0 * A_y[1:-1, 1:-1, 1:-1] + A_y[1:-1, :-2, 1:-1]) / delta2 +
        (A_z[1:-1, 2:, 2:] - A_z[1:-1, 2:, :-2] - A_z[1:-1, :-2, 2:] + A_z[1:-1, :-2, :-2]) / four_delta2
    )
    grad_div_z[1:-1, 1:-1, 1:-1] = (
        (A_x[2:, 1:-1, 2:] - A_x[2:, 1:-1, :-2] - A_x[:-2, 1:-1, 2:] + A_x[:-2, 1:-1, :-2]) / four_delta2 +
        (A_y[1:-1, 2:, 2:] - A_y[1:-1, 2:, :-2] - A_y[1:-1, :-2, 2:] + A_y[1:-1, :-2, :-2]) / four_delta2 +
        (A_z[1:-1, 1:-1, 2:] - 2.0 * A_z[1:-1, 1:-1, 1:-1] + A_z[1:-1, 1:-1, :-2]) / delta2
    )
    return grad_div_x, grad_div_y, grad_div_z


class Maxwell:
    def __init__(self, n_grid, x_out):
        self.n_grid = n_grid
        self.n_vars = 7
        self.delta = float(x_out) / (n_grid - 2.0)
        self.x = np.linspace(-self.delta * 0.5, x_out + 0.5 * self.delta, self.n_grid)[:, None, None]
        self.y = np.linspace(-self.delta * 0.5, x_out + 0.5 * self.delta, self.n_grid)[None, :, None]
        self.z = np.linspace(-self.delta * 0.5, x_out + 0.5 * self.delta, self.n_grid)[None, None, :]
        self.r = np.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)
        for nm in ("E_x", "E_y", "E_z", "A_x", "A_y", "A_z", "phi", "constraint"):
            setattr(self, nm, zeros((n_grid, n_grid, n_grid)))
        self.t = 0.0


def symmetry(f_dot, x_sym, y_sym, z_sym):
    f_dot[0, :, :] = x_sym * f_dot[1, :, :]
    f_dot[:, 0, :] = y_sym * f_dot[:, 1, :]
    f_dot[:, :, 0] = z_sym * f_dot[:, :, 1]
    return f_dot


def outgoing_wave(maxwell, f_dot, f):
    deriv_x, deriv_y, deriv_z = partial_derivs_vec(f, maxwell.delta)
    d_f_dr = (maxwell.x * deriv_x + maxwell.y * deriv_y + maxwell.z * deriv_z) / maxwell.r
    f_dot[-1, :, :] = -f[-1, :, :] / maxwell.r[-1, :, :] - d_f_dr[-1, :, :]
    f_dot[:, -1, :] = -f[:, -1, :] / maxwell.r[:, -1, :] - d_f_dr[:, -1, :]
    f_dot[:, :, -1] = -f[:, :, -1] / maxwell.r[:, :, -1] - d_f_dr[:, :, -1]
    return f_dot


def derivatives(maxwell, fields):
    """Time derivatives in Lorenz gauge. Inner-boundary parities are gold's dipole
    convention; A_z is the CORRECTED, vector-consistent (-1,-1,-1) (gold bug = (1,1,-1))."""
    E_x, E_y, E_z, A_x, A_y, A_z, phi = fields
    d = maxwell.delta
    lap_Ax = laplace(A_x, d); lap_Ay = laplace(A_y, d); lap_Az = laplace(A_z, d)
    gd_x, gd_y, gd_z = grad_div(A_x, A_y, A_z, d)
    gpx, gpy, gpz = gradient(phi, d)
    divA = divergence(A_x, A_y, A_z, d)
    E_x_dot = -lap_Ax + gd_x
    E_y_dot = -lap_Ay + gd_y
    E_z_dot = -lap_Az + gd_z
    A_x_dot = -E_x - gpx
    A_y_dot = -E_y - gpy
    A_z_dot = -E_z - gpz
    phi_dot = -divA
    symmetry(E_x_dot, 1.0, -1.0, 1.0)
    symmetry(E_y_dot, -1.0, 1.0, 1.0)
    symmetry(E_z_dot, -1.0, -1.0, -1.0)
    symmetry(A_x_dot, 1.0, -1.0, 1.0)
    symmetry(A_y_dot, -1.0, 1.0, 1.0)
    symmetry(A_z_dot, -1.0, -1.0, -1.0)   # FIX: was (1.0, 1.0, -1.0) in gold
    symmetry(phi_dot, -1.0, -1.0, 1.0)
    for f, src in [(E_x_dot, E_x), (E_y_dot, E_y), (E_z_dot, E_z),
                   (A_x_dot, A_x), (A_y_dot, A_y), (A_z_dot, A_z), (phi_dot, phi)]:
        outgoing_wave(maxwell, f, src)
    return (E_x_dot, E_y_dot, E_z_dot, A_x_dot, A_y_dot, A_z_dot, phi_dot)


# The three 13.9 test-case field setups (from scicode_verified/problems/13.json).
def field_setups():
    x, y, z = np.meshgrid(*[np.linspace(0, 2, 50)] * 3)
    return [
        (x, y, z, x, y, z, z * 0),
        (x, y, z, -y, x, z * 0, z * 0 + 1),
        (x, y, z, x * 0, -z, y, z * 0 + 1),
    ]


def update_fields(maxwell, fields, fields_dot, factor, dt):
    """13.10 — standard linear update, convention-free (carries no parity itself)."""
    return [f + factor * dt * fd for f, fd in zip(fields, fields_dot)]


# The three 13.10 test cases reuse 13.9's field inputs but with a per-test `factor`; dt=0.1.
def step10_setups():
    fs = field_setups()
    factors = [0.5, 0.3, 0.2]
    return [(fs[i], factors[i], 0.1) for i in range(3)]


# ============================================================================
# Evolution-test redesign (13.11/13.12/13.13/13.15). See
# docs/superpowers/specs/2026-06-24-p13-evolution-test-redesign-design.md
# Physical inputs with the magnetic-dipole octant symmetry sigma=(-1,-1,1); a
# CONVERGED reference is produced here (RK4, small courant) for the targets.
# IMPORTANT: the initial-data formulas below MUST stay byte-identical to the
# inline construction in the test_cases (scicode_verified/problems/13.json).
# ============================================================================

# fixed design parameters (frozen in the spec; calibration in research_by_problem/13/_p13_code/calibrate_R5.py).
# Philosophy (user): atol == the algorithm's OWN convergence error, set tight, not padded.
#   test_courant small (0.02) so a 2nd-order ICN's time-discretization error is itself tiny;
#   the spec requires "maxwell.t advanced by t_const" so a compliant stepper lands EXACTLY at
#   t_const (dt rescaled) -> the only residual is scheme-order error. Reference = RK4@0.05
#   (converged to ~1e-7, i.e. << the test floor). atol = 1.5x the measured 2nd-order floor.
#   Measured n=64 floor (rescale endpoint, max over rk2/icn2/icn3, both configs, t<=0.5): see
#   _calib_R5.log; atol frozen from it. parity-bug / sign-flip are O(1) -> ~1e4x margin.
# atol      : field-comparison tolerance (13.11 stepper, 13.13 final field). = 1.5x 2nd-order floor.
# atol_series: constraint-series tolerance (13.15 main). The ‖.‖ operator amplifies field error by
#             ~1/delta, so the series' own algorithm error is larger -> its own (still-tight) atol.
# Both frozen from research_by_problem/13/_p13_code/_calib_R5.log + _calib_series_R5.log.
# Frozen from acceptance (research_by_problem/13/_p13_code/self_pass_R5.py, n=64):
#   field   atol=1e-4 : icn2 dev 1.4e-5 (t=0.2) / 2.7e-5 (t=0.5) -> ~4-7x margin; parity bug on
#                       config2 = 0.42/1.67 (margin ~1e4x) and even on config1 (1.7e-4 > 1e-4).
#   series  atol_series=1e-6 : icn2 series dev 1.35e-7 -> ~7x margin (the ‖divE‖ operator's own
#                       tight tolerance; was mistakenly 1e-3 = 7400x too wide in the first cut).
# atol         : 13.11 stepper final field @ t_stepper=0.2 (smaller accumulated error).
# atol_integrate: 13.13 integrate final field @ t_max=0.5. Looser because a VALID 2nd-order ICN's
#   time error grows with t: gemini-flash's k1/k3 scheme (a legit 2nd-order, error const larger
#   than icn2's) lands at 1.08e-4 vs the converged ref at t=0.5 — above the 1e-4 used for t=0.2.
#   Set 5e-4 (~4.6x the worst observed valid scheme; still ~800-3000x below any wrong-physics
#   signal, e.g. the config2 parity bug = 1.67). Keeps the test admitting valid solvers while
#   rejecting wrong answers. See research_by_problem/13/_p13_code/_diag_1313.log.
# atol_series  : 13.15 constraint series (scheme-insensitive; ‖divE‖ operator).
EVOL = dict(n_grid=64, x_out=2.0, c_az=8.0,
            ref_courant=0.05, test_courant=0.02,
            t_stepper=0.2, t_max=0.5, t_check=0.1,
            atol=1e-4, atol_integrate=5e-4, atol_series=1e-6)


def config1_fields(mw):
    """Toroidal magnetic-dipole pulse: E_x=8y e^-r^2, E_y=-8x e^-r^2, E_z=0; A=0, phi=0.
    (Equivalent to E_phi=-8 r sin(theta) e^-r^2.) Divergence-free, sigma=(-1,-1,1)."""
    g = np.exp(-mw.r ** 2)
    Ex = np.broadcast_to(8.0 * mw.y * g, (mw.n_grid,) * 3).copy()
    Ey = np.broadcast_to(-8.0 * mw.x * g, (mw.n_grid,) * 3).copy()
    z3 = np.zeros((mw.n_grid,) * 3)
    return [Ex, Ey, z3.copy(), z3.copy(), z3.copy(), z3.copy(), z3.copy()]


def config2_fields(mw, c=None):
    """config1 + a z-exciting, symmetry-compatible vector potential A_z = c*xyz*e^-r^2
    (parity (-1,-1,-1), matching sigma=(-1,-1,1)). Evolution drives E_z."""
    if c is None:
        c = EVOL['c_az']
    f = config1_fields(mw)
    f[5] = np.broadcast_to(c * mw.x * mw.y * mw.z * np.exp(-mw.r ** 2), (mw.n_grid,) * 3).copy()
    return f


def _rk4_step(mw, f, dt):
    def L(ff):
        return list(derivatives(mw, ff))
    k1 = L(f)
    k2 = L([a + 0.5 * dt * b for a, b in zip(f, k1)])
    k3 = L([a + 0.5 * dt * b for a, b in zip(f, k2)])
    k4 = L([a + dt * b for a, b in zip(f, k3)])
    return [a + dt / 6.0 * (b + 2 * c + 2 * d + e) for a, b, c, d, e in zip(f, k1, k2, k3, k4)]


def evolve_ref(mw, fields, t_max, courant=None):
    """Converged reference time-integration (RK4) to t_max. Returns final field list."""
    if courant is None:
        courant = EVOL['ref_courant']
    f = [np.asarray(a).copy() for a in fields]
    dt = courant * mw.delta
    n = int(np.ceil(t_max / dt))
    dt = t_max / n
    for _ in range(n):
        f = _rk4_step(mw, f, dt)
    return f


def check_constraint_ref(mw):
    """‖∇·E‖_2 scaled by cell volume, on mw.E_x/E_y/E_z (deterministic operator)."""
    div = divergence(mw.E_x, mw.E_y, mw.E_z, mw.delta)
    return float(np.sqrt(np.sum(div ** 2) * mw.delta ** 3))


# --- reference target builders (called by the build transform) ---
def ref_stepper(config):
    """13.11 target: final 7-field state after evolving `config` to t_stepper. (7,N,N,N)."""
    mw = Maxwell(EVOL['n_grid'], EVOL['x_out'])
    f0 = config1_fields(mw) if config == 1 else config2_fields(mw)
    ff = evolve_ref(mw, f0, EVOL['t_stepper'])
    return np.array(ff)


def ref_integrate(config):
    """13.13 target: final 7-field state after integrating `config` to t_max. (7,N,N,N)."""
    mw = Maxwell(EVOL['n_grid'], EVOL['x_out'])
    f0 = config1_fields(mw) if config == 1 else config2_fields(mw)
    ff = evolve_ref(mw, f0, EVOL['t_max'])
    return np.array(ff)


def ref_main(n_grid, x_out):
    """13.15 target: final 7-field state from main(n_grid,x_out,...) on config1 (dipole)."""
    mw = Maxwell(n_grid, x_out)
    f0 = config1_fields(mw)
    ff = evolve_ref(mw, f0, EVOL['t_max'])
    return np.array(ff)


def constraint_field(mw, which):
    """Deterministic E fields for the 13.12 check_constraint test (no evolution).
    'dipole' = divergence-free toroidal dipole E (small discrete div);
    'linear' = E=(x,y,z) -> analytic div = 3 in the interior (clearly non-zero)."""
    if which == 'dipole':
        f = config1_fields(mw)
        return f[0], f[1], f[2]
    g3 = (mw.n_grid,) * 3
    Ex = np.broadcast_to(mw.x + 0.0 * mw.r, g3).copy()
    Ey = np.broadcast_to(mw.y + 0.0 * mw.r, g3).copy()
    Ez = np.broadcast_to(mw.z + 0.0 * mw.r, g3).copy()
    return Ex, Ey, Ez


def ref_check_constraint(which):
    """13.12 target: deterministic ‖∇·E‖ of the chosen (un-evolved) E field."""
    mw = Maxwell(EVOL['n_grid'], EVOL['x_out'])
    mw.E_x, mw.E_y, mw.E_z = constraint_field(mw, which)
    return check_constraint_ref(mw)


def evolve_ref_series(mw, fields, t_max, t_check, courant=None):
    """Converged reference (RK4) returning (final_fields, constraint_series), recording
    ‖∇·E‖ every t_check — matches the 13.13/13.15 integrate/main semantics."""
    if courant is None:
        courant = EVOL['ref_courant']
    f = [np.asarray(a).copy() for a in fields]
    series = []
    t = 0.0
    while t < t_max - 1e-10:
        dt_seg = min(t_check, t_max - t)
        n = int(np.ceil(dt_seg / (courant * mw.delta)))
        dt = dt_seg / n
        for _ in range(n):
            f = _rk4_step(mw, f, dt)
        t += dt_seg
        mw.E_x, mw.E_y, mw.E_z = f[0], f[1], f[2]
        series.append(check_constraint_ref(mw))
    return f, np.array(series)


def ref_main_series(n_grid, x_out):
    """13.15 target: the constraint time-series from main(n_grid,x_out,...) on config1."""
    mw = Maxwell(n_grid, x_out)
    f0 = config1_fields(mw)
    _, series = evolve_ref_series(mw, f0, EVOL['t_max'], EVOL['t_check'])
    return series
