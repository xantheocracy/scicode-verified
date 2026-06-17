# SciCode 缺陷终版登记表(按受影响字段 / 评测模式)

两轮审计:80 题逐步深审 → 全新代理对抗复核;仅收录**复核确认**的缺陷。

**关键区分**:SciCode 有 `with_background` / `without_background` 两种评测模式。`理论推导(background)` 字段**只在 with_background 模式喂给模型**,其缺陷只在该模式生效;其余字段(题面 / 函数契约 / 测试 / target)**两种模式都受影响**,是真正污染所有评测的部分。

**确认缺陷 397 条。** 假阳性 1(64.6),存疑 1(62.6)。

## 一、按受影响字段 / 评测模式分类

| 受影响字段 | 评测模式 | 🔴blk | 🟡maj | ⚪min | 合计 |
|--|--|--|--|--|--|
| 题面(description) | 所有模式 | 6 | 53 | 38 | 97 |
| 函数契约(docstring/header) | 所有模式 | 8 | 52 | 48 | 108 |
| 理论推导(background) | 仅 with_background | 7 | 25 | 29 | 61 |
| 裁判·测试用例 | 所有模式 | 17 | 35 | 55 | 107 |
| 裁判·target值 | 所有模式 | 13 | 6 | 3 | 22 |
| 依赖/环境 | 所有模式 | 2 | 0 | 0 | 2 |

**小结:影响所有模式的缺陷 336 条(🔴46 / 🟡146 / ⚪144);仅影响 with_background 的理论推导缺陷 61 条(🔴7 / 🟡25 / ⚪29)。**

> 注:字段归类优先取重型 verdict 的 `fix.target_location`(精确),其余按 fix_kind + 证据关键词推断,`理论推导 vs 函数契约` 的边界个别条目可能有偏差。

## 二、逐题明细

### ⚪ 题 1 (dev) — 2 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 1.1 | D10 文档矛盾 | ⚪ | 理论推导(background) | Quote accurate: both background fields state f(x)=1/2 x^T A x - x^T A x (second term should be x^T b) and contain the stray 'ff'; the adjacent gradien… |
| 1.1 | D10 文档矛盾 | ⚪ | 裁判·测试用例 | Eigenvalue claims reproduce exactly (case 2: [-106.52, 120.52]; case 3: [-4.64, 18.64]) so tests 2/3 are symmetric indefinite despite the SPD premise,… |

### 🔴 题 2 (test) — 7 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 2.1 | D12 依赖漂移 | 🔴 | 依赖/环境 | First pass filed this as D2; recalibrated to D12 (dependency_drift) — it is also already a known fact in the review SKILL ('Problems 2 and 28: require… |
| 2.1 | D7 target错误 | 🔴 | 函数契约(docstring/header) | Loaded h5 targets myself: tests 1-3 are (61,51) float64; all 61 rows identical to max-rel 2.0e-13 (circularly symmetric polar/angle-major grid, NOT an… |
| 2.1 | D2 信息缺失/无法做出 | 🔴 | 理论推导(background) | Static: the prompt/background/docstring nowhere state (a) the observation-plane position (no lens focal-length formula is given; background 'f' is the… |
| 2.1 | D4 约定不明 | 🟡 | 题面(description) | Loaded targets: test 2 (d=4) vs test 3 (d=2) max abs diff = 3.41e-12 (pure float noise; np.allclose True) — d has no effect on the gold intensity, con… |
| 2.1 | D8 测试过弱 | ⚪ | 裁判·测试用例 | h5 target for test 4 is np.True_. Probe ran: np.zeros((61,51)), np.ones((61,51)), np.zeros((51,51)), np.full((7,3),2.5) ALL satisfy (np.argmax(arr)==0… |
| 2.1 | D10 文档矛盾 | ⚪ | 理论推导(background) | Static, quoted from problem_background_main (and identical step_background): (1) 'Z_2=f-\frac{f^3\left(f-Z_1\right)}{\left(f-Z_1\right)^2+\left(\frac{… |
| 2.1 | D8 测试过弱 | ⚪ | 函数契约(docstring/header) | [复核新增] First pass noted only as a step-notes 'curiosity', never filed: np.allclose broadcasting means the documented 2D return shape is unconstrain |

### ⚪ 题 3 (dev) — 1 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 3.1 | D4 约定不明 | ⚪ | 理论推导(background) | Quote verbatim in prompt; literally M=D-L with L=tril(A) is the wrong GS splitting (correct M=tril(A)=D+strict lower), but the background's component-… |

### 🟡 题 4 (dev) — 2 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 4.1 | D8 测试过弱 | 🟡 | 裁判·测试用例 | Re-ran probe: `return np.linalg.cholesky(A)` passes 3/3 via official steptest; all three test matrices are structurally fill-in-free (tridiagonal x2; … |
| 4.1 | D4 约定不明 | ⚪ | 理论推导(background) | Quote accurate: problem_io/header output is just 'A : Matrix, 2d array M * M'; gold zeroes the strict upper triangle so targets have zero uppers, whil… |

### 🔴 题 5 (test) — 2 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 5.1 | D6 容差脆弱 | 🔴 | 裁判·测试用例 | Independently verified every element of the claim. (1) Structure: J@A@J==A (centro-symmetric) and J@b==b (palindromic) for test 1; Krylov matrix [b,Ab… |
| 5.1 | D7 target错误 | 🟡 | 裁判·target值 | Loaded h5 targets directly via process_hdf5_to_tuple('5.1', 3, ...). Test-1 target (7x6): all column norms 1.0 but max \|Q^T Q - I\| = 0.944821 at ent… |

### ⚪ 题 6 (dev) — 3 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 6.1 | D3 单位制不明 | ⚪ | 理论推导(background) | Docstring quote accurate: no unit stated for frequency_threshold; gold uses pixel/bin radius in the shifted spectrum, so an fftfreq cycles/pixel readi… |
| 6.1 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Test 4 verbatim passes image_array (not image_array2) to the second call leaving image_array1/2 dead, and the area assert is one-sided; T depends only… |
| 6.1 | D10 文档矛盾 | ⚪ | 理论推导(background) | Background verbatim says '[m,n]' input but 'Ouput the nxn array'; gold returns (m,n); cosmetic contradiction, minor stands. |

### 🟡 题 7 (dev) — 3 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 7.1 | D8 测试过弱 | 🟡 | 裁判·测试用例 | Re-ran reviewer's no-FFT stub (correct mask T, zeros filtered_image) in official concatenated style: exit 0, full credit; periodicity argument (input … |
| 7.1 | D9 跨步依赖 | 🟡 | 裁判·测试用例 | Test 4 verbatim calls apply_band_pass_filter(image_array,...) for T1 before any image_array assignment in that test (and has stray 'frequency_threshol… |
| 7.1 | D10 文档矛盾 | ⚪ | 理论推导(background) | Background verbatim says 'Ouput the nxn array' for an [m,n] input and 'the frequency threshold' (singular) vs two bandmin/bandmax params in header; co… |

### 🟡 题 8 (test) — 1 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 8.1 | D4 约定不明 | 🟡 | 题面(description) | Quotes accurate: no text specifies fftshift-centered layout for returned T; re-ran reviewer's scratch — natural-order impl (identical filtered image) … |

### 🟡 题 9 (test) — 1 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 9.1 | D10 文档矛盾 | 🟡 | 理论推导(background) | Both quotes accurate: description defines M=D/omega (and cites I - omega*D^{-1}A), but background equation omits the (1-omega)x^k term; re-ran reviewe… |

### 🟡 题 10 (dev) — 8 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 10.1 | D2 信息缺失/无法做出 | 🟡 | 题面(description) | Prompt quote accurate; alpha appears only as free parameter in Ewald formulas, no heuristic stated; gold alpha=5*max\|recvec row\| matches targets (EX… |
| 10.2 | D4 约定不明 | 🟡 | 裁判·测试用例 | Prompt specifies no row order; test is order-sensitive np.allclose; np.meshgrid default 'xy' yields same set in different row order (standard numpy be… |
| 10.3 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Docstring never states displacement sign; gold uses configs[i+1:]-configs[i] (r_j-r_i); targets nonzero for tests 2-4 so the equally valid opposite si… |
| 10.4 | D10 文档矛盾 | 🟡 | 函数契约(docstring/header) | Docstring quotes accurate: declares input (natoms, npairs, 1, 3) and return (npairs,), but tests pass (nelec, natoms, 1, 3) and gold reduces only the … |
| 10.6 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Gold contains 'recvec * 2 * np.pi'; docstring only says 'reciprocal lattice vectors' while harness passes inv(latvec).T, so the 2pi-included physics c… |
| 10.7 | D9 跨步依赖 | 🟡 | 裁判·测试用例 | cmp_tuple_or_list is plain np.allclose (order-sensitive); select_big_weights preserves input order via boolean mask; 10.6's own test is order-insensit… |
| 10.10 | D8 测试过弱 | 🟡 | 裁判·测试用例 | Gold simplifies to -factor*(sum q_ion - nelec)^2; all four test systems are neutral (1-1, 4-4, 2-2, 8-8) so every target is exactly 0 and 'return 0.0'… |
| 10.1 | D9 跨步依赖 | ⚪ | 裁判·测试用例 | Verified in test strings: L = 4/3**0.5 defined only in test case 3 but referenced by test case 4 in 10.1/10.2/10.3/10.4/10.10 etc.; only namespace lea… |

### 🟡 题 11 (test) — 12 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 11.1 | D1 签名不匹配 | 🟡 | 函数契约(docstring/header) | Header 'def ket(dim):' verified; all 3 tests pass two positional args (ket(2,0) etc.), docstring lists an 'args' param the header omits. |
| 11.1 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | h5 targets verified as (2,1)/(4,1)/(6,1) column vectors; docstring's 'dim dimensional array' reads 1-D, and a (d,) return fails allclose by broadcast … |
| 11.3 | D1 签名不匹配 | 🟡 | 函数契约(docstring/header) | Header 'def tensor():' verified zero-param; every test passes 2 arguments, incompatible as given. |
| 11.4 | D4 约定不明 | 🟡 | 理论推导(background) | Docstring/prompt/background never state the index base; test calls sys=[2] with dim=[2,2] only make sense 1-based, and tests are hidden from the solve… |
| 11.8 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Docstring 'perm: list of int containing the desired order' states no base; test perms [2,1],[1,3,2] are 1-based and a numpy-axes 0-based impl crashes. |
| 11.9 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Docstring states no base; tests partial_trace(X,[2],[2,2]) and (X,[1],[3,2]) are 1-based, 0-based reading fails. |
| 11.3 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Docstring promises '2d array' but h5 test-1 target verified as 1-D shape (4,) int32 [0,0,0,1]; a (4,1) column return would fail allclose. |
| 11.6 | D10 文档矛盾 | ⚪ | 题面(description) | Quote accurate: 'Write a function with and functions ... to receiver function.' — function names dropped; still solvable from main description. |
| 11.7 | D10 文档矛盾 | ⚪ | 题面(description) | Quote accurate: 'm-1 0's and one Write a function...' missing the '1.'; same corruption in problem_description_main ('and one If so'). |
| 11.10 | D10 文档矛盾 | ⚪ | 理论推导(background) | Background verified: formula uses log_2 while prose says 'In denotes the (natural) matrix logarithm'; prompt's explicit 'log base 2' settles scoring. |
| 11.11 | D10 文档矛盾 | ⚪ | 题面(description) | Quote accurate: 'Calculate the coherent information of a state with and function.' — names dropped; background gives I_c = S(B)-S(AB) so solvable. |
| 11.12 | D10 文档矛盾 | ⚪ | 题面(description) | Both quotes accurate: prompt has 'measurement in .' / 'with function , and .', and background formula rho'=tr(PiRhoPi)/p has the spurious trace. |

### 🟡 题 12 (test) — 2 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 12.14 | D4 约定不明 | 🟡 | 题面(description) | Scratch logs (scf_variants.log, scf_trace.log) reproduce the claim: SCF unconverged at iteration cap (band energies oscillate ~0.5-0.8 Ry at it7-9, ma… |
| 12.2 | D8 测试过弱 | ⚪ | 裁判·target值 | Read frozen h5 targets directly: max\|t\| = 2.091e-8 / 1.641e-9 / 7.950e-9 as claimed; all-zeros passes tests 2 and 3 under np.allclose default atol=1… |

### 🔴 题 13 (test) — 9 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 13.12 | D9 跨步依赖 | 🔴 | 裁判·测试用例 | Ran steptest joint mode on review/work/13/verify variants. (a) Natural implementation (stepper stores final evolved fields into maxwell): check_constr… |
| 13.9 | D4 约定不明 | 🟡 | 题面(description) | Baseline with parity table E_x_dot,A_x_dot:(1,-1,1); E_y_dot,A_y_dot:(-1,1,1); E_z_dot,A_z_dot:(1,1,-1); phi_dot:(-1,-1,1) and symmetry-before-outgoin… |
| 13.15 | D10 文档矛盾 | 🟡 | 函数契约(docstring/header) | Static: h5 '13.15' targets are 1-D float64 arrays of shapes (10,),(10,),(10,),(20,) - constraint VALUES only - while function_header docstring and pro… |
| 13.11 | D4 约定不明 | 🟡 | 题面(description) | Floor+remainder policy (full substeps of courant*delta = 0.0208333, final remainder substep 0.0125 to land on t_const=0.2): official PASS (base_impl.p… |
| 13.8 | D4 约定不明 | 🟡 | 题面(description) | Baseline (evaluate step-13.1 partial_derivs_vec on the FULL array, overwrite only the three outer faces with -(f + x*dx + y*dy + z*dz)/r): official PA… |
| 13.13 | D4 约定不明 | ⚪ | 函数契约(docstring/header) | h5 '13.13' targets have exactly 10 entries for t_max=1, t_check=0.1 (checkpoints t=0.1..1.0, no t=0 entry; verified shapes (10,),(10,),(10,)). Variant… |
| 13.14 | D4 约定不明 | ⚪ | 题面(description) | Static: the 13.14 prompt formula 'E_phi = -8 A (r sin(theta)/lambda^2) exp(-(r/lambda)^2)' is the only mention of A and lambda; neither is given a val… |
| 13.3 | D8 测试过弱 | ⚪ | 裁判·测试用例 | [复核新增] All three test_cases of 13.3 are verbatim identical (same fct = np.sin(x)*np.sin(2*y)*np.sin(3*z)), and the three h5 targets are bit-identic |
| 13.5 | D8 测试过弱 | ⚪ | 裁判·测试用例 | [复核新增] 13.5 tests 1-2 have analytically-zero targets (max\|target\| = 8.71e-14: grad_div of (-y,x,0) and of (x,y,z) is identically zero), and 13.4 te |

### 🟡 题 14 (test) — 5 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 14.1 | D4 约定不明 | 🟡 | 题面(description) | Test does np.random.seed(0) then allclose against a frozen single-trajectory target; prompt never states the legacy-global-RNG/one-draw-per-step conve… |
| 14.2 | D6 容差脆弱 | 🟡 | 裁判·测试用例 | Tests verified unseeded with band (0.95,1.05) and Navg=4000; estimator relative std sqrt(2/4000)=2.24% makes the band ~2.2 sigma, so the claimed ~7-9%… |
| 14.1 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Re-ran reviewer's Euler-Maruyama stub via steptest: PASS 3/3 under official joint scoring, so tests cannot distinguish the taught leapfrog scheme at d… |
| 14.2 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Quotes accurate: problem_io output says 'eta : float - Ratio...' while the step header docstring and return line say x_MSD, and the test computes eta … |
| 14.2 | D8 测试过弱 | ⚪ | 裁判·测试用例 | The test compares only against the closed-form equilibrium MSD (analytical_msd defined in-test), so returning that standard textbook formula gives eta… |

### 🟡 题 15 (test) — 3 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 15.2 | D2 信息缺失/无法做出 | 🟡 | 题面(description) | Prompt quote verified ('$\hbar=\times 10^{-34} Js$', mantissa missing); reran reviewer's scratch via steptest: impl_gold_hbar.py (hbar=1.0545718e-34) … |
| 15.1 | D8 测试过弱 | 🟡 | 裁判·测试用例 | Arithmetic checks out: diag imag ~9.26e-8 hides under rtol*\|1\|=1e-5 (so sign-swapped/real diagonals pass), off-diag ~4.6e-8 sits at atol=1e-8 floor … |
| 15.1 | D10 文档矛盾 | ⚪ | 理论推导(background) | Header docstring verbatim says 'each element is a float' while entries are necessarily complex (C = i*hbar*h/(4*m*a^2)); quote accurate. |

### 🟡 题 16 (test) — 3 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 16.2 | D8 测试过弱 | 🟡 | 裁判·测试用例 | Reproduced: np.sort(np.diag(matrixA))[:k] stub (no eigensolving) PASSES all 3 official joint tests; noise levels 0.0/1e-4/1e-5 in tests match the quot… |
| 16.2 | D4 约定不明 | 🟡 | 裁判·测试用例 | Test 1 is exactly init_matrix(100, 0.0) -> A = diag(1..100), so the prescribed q_i = -r_i/(diag(A)-lambda_i) is a literal 0/0 at any converged root; t… |
| 16.2 | D10 文档矛盾 | ⚪ | 理论推导(background) | Background verbatim says 'Define $n$ vectors b = {b_1,...b_n} with $n$ the dimension of A', which taken literally is full-space and contradicts the it… |

### 🔴 题 17 (test) — 5 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 17.2 | D7 target错误 | 🔴 | 裁判·target值 | h5 targets: [0.40089186286863654, 0.6414269805898188, 0.25657079223592727, 0.0, True]. (1) I implemented the standard Blochl/Lehmann-Taut DOS myself (… |
| 17.1 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Loaded h5 targets via process_hdf5_to_tuple('17.1', 3, ...): all 3 targets are 2-tuples of 25-entry dicts keyed exactly 'e00'..'e44' (str keys, no sep… |
| 17.1 | D4 约定不明 | 🟡 | 题面(description) | Prompt states 'Define the energy differences $\varepsilon_{ji} = \varepsilon_j - \varepsilon_i$'. I checked all 25 entries of all 3 h5 targets against… |
| 17.2 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Static check of review/problems/17.json: the 17.1 background defines rho(E) = (6*Omega_T/Omega_BZ) * Int dS/\|grad eps\|, but integrate_DOS(energy, en… |
| 17.2 | D8 测试过弱 | ⚪ | 裁判·测试用例 | h5 test 4 target is 0.0 (E=5 > eps4, compared with np.allclose) and test 5 target is True for `(float(integrate_DOS(0.9, ...)) == 0) == target`. My tr… |

### 🔴 题 18 (test) — 5 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 18.2 | D7 target错误 | 🔴 | 裁判·测试用例 | Raw h5 inspection (h5py): '18.2/test1/var1' shape (2,) value [0.5, 1.0]; tests 2/3 are scalars 0.0625 and 0.14 — the reference itself produced inconsi… |
| 18.1 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Wrote my own fresh implementations. 1-based (review/work/18/verify/b1.py, base case Xi[i-1] <= xi < Xi[i]): steptest joint PASS 3/3. Literal 0-based t… |
| 18.2 | D8 测试过弱 | 🟡 | 函数契约(docstring/header) | verify/nurbs_ignore_w.py returns the plain tensor product Bspline(xi_1,i_1,p_1,Xi_1)*Bspline(xi_2,i_2,p_2,Xi_2), ignoring w and the rational normaliza… |
| 18.1 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Static check of review/problems/18.json. Docstring says 'xi : knot index, integer' but tests pass xi=0.1, 1.5, 0.5 (float parameter coordinates); 'i :… |
| 18.1 | D4 约定不明 | ⚪ | 理论推导(background) | [复核新增] The background gives the bare Cox-de Boor recursion but never states the standard 0/0 := 0 convention, and EVERY test input has repeated kno |

### 🟡 题 19 (dev) — 2 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 19.1 | D1 签名不匹配 | 🟡 | 函数契约(docstring/header) | Header is literally 'def tensor():' (zero params) while docstring says 'args: any number of arrays' and all three tests call tensor(a,b); fix to 'def … |
| 19.2 | D8 测试过弱 | ⚪ | 裁判·测试用例 | All four targets are exactly 0 or 1 (fixed points of squaring), and sigma_x^n equals sigma_y^n on all four real test states (Bell/GHZ4=1, W4/product=0… |

### 🟡 题 20 (test) — 3 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 20.1 | D6 容差脆弱 | 🟡 | 题面(description) | Prompt gives THz->eV factor but no kB (verified by reading); kB=8.617e-5 (4 sig figs) fails test 1 (T=100K) under default allclose, reproduced via one… |
| 20.2 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Trivial zeros impl reaches and fails only the third assert (tests 0-1 pass: targets zero/sub-atol), reproduced with reviewer's impl_zeros.py; minor is… |
| 20.2 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Docstring labels output with the exact term the main text defines for unweighted l, but target is Bose-weighted: unweighted impl fails test 2 (reprodu… |

### 🔴 题 21 (test) — 5 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 21.2 | D8 测试过弱 | 🔴 | 裁判·测试用例 | Loaded h5 targets myself: 21.2 = {int32(0), int32(0), float64(4.359649170067458e-27)}. Wrote my own unconditional-zero alpha_eff (review/work/21/verif… |
| 21.2 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Wrote my own literal-formula impl with no below-gap clamp (review/work/21/verify/v_noclamp_212.py): np.sqrt(hbar*omega - Eg) -> nan for tests 0 (800nm… |
| 21.2 | D2 信息缺失/无法做出 | 🟡 | 题面(description) | Static, quoted verbatim from review/problems/21.json: 21.2 prompt reads 'The electron charge is $\times 10^{-19} C$, the vacuum speed of light is $3\t… |
| 21.3 | D2 信息缺失/无法做出 | 🟡 | 题面(description) | Independent grid scan (verify/scan_213.py) over 3 e x 6 hbar x 3 c x 4 Eg candidate sets: EXACTLY ONE combo passes all three numeric targets -- e=1.6e… |
| 21.2 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Static, quoted verbatim: header 'def alpha_eff(lambda_i, x, C):' (no default) vs docstring 'C (float): Optional scaling factor for the absorption coef… |

### 🔴 题 22 (test) — 7 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 22.3 | D7 target错误 | 🔴 | 裁判·测试用例 | Wrote my own quadrature projection (verify/quad_BR_22.3.py): psi(r-r0) projected onto conj(Y_2^1) on spheres a=0.7 and a=1.1 (radii agree to ~1e-15; t… |
| 22.3 | D7 target错误 | 🔴 | 裁判·测试用例 | My quadrature: BR_2^2 for r0=(0,0.5,0), B_1^1=1 is +0.217672526159j (radii 0.7/1.1 agree to 1e-15) -- NOT zero. Attacked all escape readings: conjugat… |
| 22.2 | D4 约定不明 | 🟡 | 理论推导(background) | Reproduced both legs myself. (1) steptest joint: conj-base + printed recursion (review/work/22/step_22.2.py) PASS 3/3; values bit-exact vs h5 targets … |
| 22.3 | D9 跨步依赖 | 🟡 | 理论推导(background) | Static: 22.1's background initiates only (R\|R)_{l0}^0 -> '(R\|R)_{lm}^m' upward in m (quote: 'which can be used to initiate the recursion process for… |
| 22.2 | D7 target错误 | 🟡 | 裁判·target值 | [复核新增] The frozen 22.2 targets are NOT rotation coefficients of the given Q under ANY spherical-harmonic phase convention or direction reading -- t |
| 22.3 | D10 文档矛盾 | ⚪ | 理论推导(background) | Verified all quotes verbatim from review/problems/22.json: 22.3 prompt ends '...calculate the reexpansion coeffcient with and .'; 22.3 background 'The… |
| 22.3 | D4 约定不明 | ⚪ | 函数契约(docstring/header) | [复核新增] The B matrix's column<->m mapping is never stated; problem_io and the 22.3 docstring say only 'B : matrix of shape(N_t + 1, 2 * N_t + 1)'. T |

### 🟡 题 23 (test) — 3 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 23.3 | D6 容差脆弱 | 🟡 | 裁判·target值 | Reproduced with reviewer's scratch: seed-0 e=1e-5 stop gives 0.073166717019552 (matches target to 1e-17) vs C*=0.07319398616 at e=1e-14, gap 2.73e-5 >… |
| 23.3 | D4 约定不明 | ⚪ | 题面(description) | Quotes accurate: main description uses \exp(D(...)) with an unbalanced paren while step 23.1 mandates log base 2; minor severity is right since impact… |
| 23.3 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Read general_tests: test 6 is a character-for-character copy of test 1 and test 7 of test 4 (same channel, same e), pure redundancy. |

### 🔴 题 24 (test) — 5 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 24.1 | D7 target错误 | 🔴 | 裁判·测试用例 | Loaded h5 targets myself: middle cell = +0.4444444444444444 (= +4/9) in ALL three tests (indices 4/49/14 for n_x=10/100/30; all odd cell counts so the… |
| 24.1 | D6 容差脆弱 | 🟡 | 裁判·测试用例 | Reproduced the last-bit-rounding sensitivity with my own code: central Gauss node of the middle cell computed as 0.5*(x[i]+x[i+1]) = exactly 0.0 for n… |
| 24.2 | D4 约定不明 | ⚪ | 题面(description) | Targets read directly: -0.75, 4.5, 22.5. Analytic check: LF = 0.5*(uL^2/2 + uR^2/2 - alpha*(uR-uL)); test0 (0,1) -> 0.25 - alpha/2 = -0.75 only for al… |
| 24.1 | D10 文档矛盾 | ⚪ | 题面(description) | Static check of review/problems/24.json sub_steps[0].step_description_prompt, quoted verbatim: 'The output will be cell-averaged values, an array of l… |
| 24.3 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Static check, quoted verbatim from review/problems/24.json: sub_steps[2].step_description_prompt reads '...using the initial conditon and Lax-Friedric… |

### ⚪ 题 25 (test) — 2 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 25.3 | D4 约定不明 | ⚪ | 题面(description) | Prompt 'survive in the end' vs SPC_THRES snapshot criterion is a genuine but minor wording wrinkle; snapshot reading is the natural one every numerica… |
| 25.3 | D6 容差脆弱 | ⚪ | 裁判·target值 | Thin ~4-5x margin above 1e-6 cutoff is real (test params verified: SPC_THRES=1e-6, dt=0.01); reviewer's multi-solver check shows no flip with supplied… |

### ✅ 题 26 (test) — 无确认缺陷

### 🟡 题 27 (test) — 4 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 27.2 | D2 信息缺失/无法做出 | 🟡 | 题面(description) | Prompt literally reads 'the electron charge is $\times 10^{-19} C$' (mantissa missing); re-ran reviewer's CODATA-q impl from review/work/27/ -> 27.2 F… |
| 27.2 | D10 文档矛盾 | ⚪ | 理论推导(background) | Background sentence 'Here we assume no applied voltage, so $V_0=0$' is verbatim in the step, and test 2 indeed calls capacitance(..., -3); contradicti… |
| 27.2 | D10 文档矛盾 | ⚪ | 理论推导(background) | Background formula C=eps/(x_p+x_i+x_n) omits area A while docstring outputs C in farads with A as input; 'p-i-p diode' typo also present verbatim; min… |
| 27.3 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Docstring types xi/f_3dB as float, but all four tests pass xi = np.linspace(0,5,50); a math-module scalar impl necessarily crashes; minor stands. |

### 🔴 题 28 (test) — 10 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 28.1-28.3 (all) | D12 依赖漂移 | 🔴 | 依赖/环境 | python3 -c 'from scipy.integrate import simps' -> ImportError on scipy 1.15.2. steptest.py --problem 28 --step {28.1,28.2,28.3} --code verify/impl_goo… |
| 28.2 | D10 文档矛盾 | 🟡 | 函数契约(docstring/header) | Reproduced both readings myself (simps-shimmed joint runner). Docstring-literal geometry (q0 --propagate s--> lens Mf1 --propagate z-->, 'z: distances… |
| 28.1 | D4 约定不明 | 🟡 | 题面(description) | Reproduced all three variants myself (shimmed joint runner). (a) Self-consistent fftfreq(N+1, d=L/N) + Fresnel TF: FAILS all 3 tests; measured P2 rel … |
| 28.1 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Verified the targets myself: test-1 target P1 = 3.141592653581e-06 = pi*w0^2 (rel diff 2.8e-12), test-2 rel diff 8.6e-14 -> unit PEAK amplitude E0=exp… |
| 28.3 | D10 文档矛盾 | 🟡 | 函数契约(docstring/header) | Inspected the h5 targets myself: Intensity target corner value It[0,0] = 0.969812/0.990954/0.991588 = exp(-rc^2/w_min^2) EXACTLY (amplitude); the phys… |
| 28.3 | D4 约定不明 | ⚪ | 函数契约(docstring/header) | Target focus_depth = 210.5105105105/240.5405405405/222.5225225225 = z[np.argmin(Wz)] exactly (grid values of linspace(0,300,1000)). Computed the exact… |
| 28.1 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Ran a deliberately wrong implementation returning np.fft.fftshift of both arrays (beam split into the four corners of the window - spatially scrambled… |
| 28.3 | D3 单位制不明 | ⚪ | 函数契约(docstring/header) | Static: 28.2/28.3 docstrings declare z, L1, s, R0 '(in meters)' while every test input is in mm ('# Wavelength in mm', '# Distance in mm'). 28.3 tests… |
| 28.1 | D10 文档矛盾 | ⚪ | 理论推导(background) | Static, quoted from sub_steps[0].step_background verbatim: '\\mathrm{e}^{-\\mathrm{i}\\left\\{k\\left[z+\\frac{x^2+y^2}{2 R(z)}\\right] \\arctan \\fra… |
| 28.1 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | [复核新增] return_line is ' return Gau, Gau_pro' (lowercase p) while the function_header docstring names the second output 'Gau_Pro'. A model that name |

### 🟡 题 29 (dev) — 1 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 29.1 | D4 约定不明 | 🟡 | 理论推导(background) | Quotes accurate: docstring/header say 'v (N*1 numpy array)' yet tests 2-3 feed (4,2) and (3,2,2) arrays; targets require the unstated flattened/Froben… |

### 🟡 题 30 (test) — 2 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 30.3 | D6 容差脆弱 | 🟡 | 裁判·测试用例 | Quoted test structure accurate (central 2nd-diff RMSE / delta^2 vs frozen target); roundoff math sound (eps/delta^2 ~ 1e-4 dominates target 1.6e-3 at … |
| 30.3 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Read all 6 test cases: only value/gradient/laplacian are exercised via test_gradient/test_laplacian; wf.kinetic in the required header is never called… |

### 🔴 题 31 (test) — 4 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 31.3 | D6 容差脆弱 | 🔴 | 裁判·测试用例 | Ran steptest joint mode with my own fresh re-implementation (review/work/31/verify/impl_best.py): 'RESULT step 31.3: FAIL (official joint scoring)'; -… |
| 31.3 | D5 非确定性 | 🟡 | 题面(description) | Tests wrap every call in np.random.seed(0) while the prompt only says "starting from a random vector `w`". Reproduced in review/work/31/verify/check_3… |
| 31.2 | D4 约定不明 | 🟡 | 题面(description) | Probed 10 whitening constructions against the frozen target (review/work/31/verify/check_311_312.py). Exactly one matches: center-with-sd + np.cov (dd… |
| 31.1 | D4 约定不明 | ⚪ | 函数契约(docstring/header) | Probed both ddof values against all 3 frozen targets (review/work/31/verify/check_311_312.py): ddof=0 matches bit-exactly (maxdiff 0.0 on all three); … |

### 🟡 题 32 (test) — 3 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 32.2 | D4 约定不明 | 🟡 | 理论推导(background) | Header says 'h: Step size of the differentiation' with h=1e-6 while all lengths are meters; re-ran scratch: literal absolute-h central diff FAILS 32.2… |
| 32.2 | D2 信息缺失/无法做出 | 🟡 | 理论推导(background) | k_i appears only as an undefined symbol in the 32.2 background (and nowhere else in the prompt); the passing scratch impl indeed supplies off-prompt k… |
| 32.3 | D6 容差脆弱 | ⚪ | 裁判·测试用例 | Test 4 quote accurate: abs(sum(nf)-sum(n0))<1e-6 with sum(n0)=39550742.17 demands ~2.5e-14 relative trace conservation over 1e5 RK4 steps — roundoff-f… |

### 🟡 题 33 (test) — 5 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 33.3 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Docstring quote accurate (no axis assignment stated); target matrix is transpose-asymmetric with exactly 1560/1600 mismatching entries as claimed, so … |
| 33.2 | D4 约定不明 | ⚪ | 裁判·测试用例 | Re-ran first-pass variants.py: only the author's arange/open-boundary grid bit-matches; periodic Fukui (exactly 1.0/-1.0/0.0), endpoint-inclusive, and… |
| 33.2 | D4 约定不明 | ⚪ | 理论推导(background) | Background never names the band; same variants run shows upper band gives exact negative (-1.0077587 etc.) and fails; minor is right since eigh column… |
| 33.3 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Checked h5: tests 1 and 2 results differ by max 7.1e-15 with identical m/phi arrays; scale-invariance argument (t1/t2=5 in both, H2=H1/5) is correct, … |
| 33.3 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Header summary line really says 'swept next-nearest-neighbor coupling constant' while m_values is the m/t2 ratio per problem_io and the per-output des… |

### 🟡 题 34 (test) — 4 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 34.2 | D2 信息缺失/无法做出 | 🟡 | 题面(description) | Quote verbatim in 34.2 prompt ('the electron charge is $\times 10^{-19} C$' — mantissa missing); reran scratch sol_codata_q.py: 34.2 PASS but 34.3 FAI… |
| 34.3 | D4 约定不明 | 🟡 | 题面(description) | Prompt indeed never specifies grid endpoints/length; reran scratch sol_grid_exclusive.py: 34.3 FAIL with exact quoted broadcast error shapes (461,) vs… |
| 34.3 | D10 文档矛盾 | ⚪ | 理论推导(background) | Verbatim: problem_io and 34.3 docstring say 'N_a: ... n-type region' / 'N_d: ... p-type region', contradicting 34.1/34.2 docstrings and the acceptor/d… |
| 34.2 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Arithmetic checks out (targets ~4e-6 cm so rtol*\|t\|~4e-11 << default atol 1e-8, a ~0.25% pass band) and steptest confirms CODATA-q impl passes 34.2 … |

### 🟡 题 35 (test) — 3 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 35.2 | D2 信息缺失/无法做出 | 🟡 | 题面(description) | Quote accurate: prompt reads '...i,j,k are at least The output should be in ascending order.' — lower bound truncated; >=1 vs >=0 give different answe… |
| 35.3 | D10 文档矛盾 | ⚪ | 题面(description) | Quote accurate: prompt body says 'smallest N non-zero energy levels' but docstring/targets are photon wavelengths (test 0's >1e10 only makes sense in … |
| 35.2 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Quote accurate: all order-sensitive tests wrap output in sorted()/sorted()[::-1], so the stated ascending/descending contracts are unenforced dead tex… |

### 🟡 题 36 (test) — 2 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 36.2 | D2 信息缺失/无法做出 | 🟡 | 题面(description) | Quote accurate: prompt text literally reads 'electron charge is $\times 10^{-19} C$' (mantissa dropped, in both main description and step prompt); ste… |
| 36.3 | D2 信息缺失/无法做出 | 🟡 | 题面(description) | Same corrupted constant propagates via the internal FD-integral call; reviewer's q-variant scratch and steptest logs are consistent, and the 36.2 CODA… |

### 🟡 题 37 (test) — 6 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 37.1 | D10 文档矛盾 | 🟡 | 理论推导(background) | Eq (1)/(2) quotes accurate (l'=r*i/u'+r with unprimed i, numerator missing n/n'), contradicting eq (5)'s sin I'; literal-prompt impl re-ran FAIL, text… |
| 37.1 | D4 约定不明 | 🟡 | 题面(description) | Passing impl uses seq [n_total,n1,n2,n_total] and never references n3 (decoy proven structurally); docstring quotes accurate, all tests pass n2==n1, d… |
| 37.2 | D4 约定不明 | 🟡 | 题面(description) | Same hidden media mapping with sinI1=h1/r1, U1=0 re-ran PASS on exact-trace targets; GPT-5 results file exists and shows 0/3 as cited. |
| 37.3 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Standard-convention impl (L31-l31) re-ran FAIL incl. test-4 boolean; swapped 'Axial'/'Paraxial' return labels verified in both headers, so the prompt'… |
| 37.2 | D10 文档矛盾 | ⚪ | 理论推导(background) | All quotes accurate: docstring says 'paraxial' for the non-paraxial step, background says 'paraxial ... angle >> 5 degree', prompt lists nonexistent '… |
| 37.1 | D8 测试过弱 | ⚪ | 裁判·测试用例 | All test cases verified to pass n2==n1 and gold ignores n3, so surface-2 refraction and n3 are unconstrained; follows logically from the confirmed map… |

### 🟡 题 38 (dev) — 2 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 38.3 | D1 签名不匹配 | 🟡 | 函数契约(docstring/header) | Header is literally 'def reciprocal():' (zero params) while docstring documents *arg and all 4 tests call with 1-3 positional args; gold uses 'def rec… |
| 38.3 | D4 约定不明 | 🟡 | 理论推导(background) | Background 1D formula is quoted accurately and is only for x-aligned a1=a*x_hat; test 4 input [1,1,5] is not x-aligned, and target arithmetic (2*pi/27… |

### 🟡 题 39 (test) — 2 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 39.1 | D10 文档矛盾 | 🟡 | 题面(description) | Quotes accurate: description says 'tuple of the matrix element (A,B,C,D)' while docstring/return_line say 2x2 array 'matrix'; a 4-tuple vs (2,2) targe… |
| 39.2 | D4 约定不明 | 🟡 | 题面(description) | All numeric claims verified: np.arccos(1.5+0j)=-0.9624j (so 'keep real part pi' gives pi-0.9624j, opposite sign of target), arccosh(\|0.5+1j\|)=0.4812… |

### 🔴 题 40 (test) — 4 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 40.3 | D2 信息缺失/无法做出 | 🔴 | 函数契约(docstring/header) | h5 target shapes confirmed: 42/14/22 for tests 0/1/2 = round(2/(dt/CFL))+2 exactly. Ran 7 solve variants via review/work/40/verify/v_40_3.py through s… |
| 40.2 | D4 约定不明 | 🟡 | 题面(description) | Wrote my own independent variants (review/work/40/verify/v_40_2_react_first.py, v_40_2_diff_first.py). steptest --problem 40 --step 40.2: reaction-fir… |
| 40.3 | D7 target错误 | 🟡 | 函数契约(docstring/header) | With the otherwise-exact grid (dx=dt/CFL, N=round(2/dx)+2): nsteps=round(T/dt) (solution at the documented 'Max time' T) -> steptest FAIL, maxerr {2.6… |
| 40.2 | D10 文档矛盾 | ⚪ | 题面(description) | Static check of review/problems/40.json: sub_steps[1].step_description_prompt = 'Write a function performing first order strang splitting at each time… |

### 🟡 题 41 (test) — 1 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 41.3 | D4 约定不明 | 🟡 | 裁判·target值 | Reproduced: test2 col-sums [93.46,76.31,99.0,135.16] are non-balanced (violates BG 'each column = D-1'); first-column-sum normalization gives 0.005174… |

### 🟡 题 42 (test) — 2 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 42.3 | D10 文档矛盾 | 🟡 | 理论推导(background) | Background does display both eta*J_th=nw*Jw and eta*I_th=J_th*w*L (double-counting eta, contradicting its own 'product of density and area' prose); li… |
| 42.1 | D10 文档矛盾 | ⚪ | 题面(description) | Prompt's final clause really says output is G_th while docstring/background define output g_w = G_th/(nw*Gamma_w); hand-check gives g_w=1601.99 for te… |

### 🔴 题 43 (test) — 4 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 43.3 | D6 容差脆弱 | 🔴 | 函数契约(docstring/header) | All reproductions re-run independently (review/work/43/verify/). (a) steptest joint with my own literal implementation (my_43.3.py: fixed linspace(0,L… |
| 43.3 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Static: the only spec for nz is 'nz : ndarray - Normalized population inversion distribution along the length of the fiber' (sub_steps[2].function_hea… |
| 43.3 | D4 约定不明 | 🟡 | 题面(description) | Re-ran branch-sensitivity probes myself. Current env (scipy 1.15.2), Ppl=50/Ppr=30, 100-pt mesh, default tol: signal guess 0.01 W -> sol.status=0 (sol… |
| 43.3 | D8 测试过弱 | ⚪ | 裁判·测试用例 | [复核新增] Boolean test 4 (assert (nz[0] > nz[len(nz)//2]) == target, target=True) is unconstraining: I verified that even the completely wrong NON-las |

### 🔴 题 44 (dev) — 1 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 44.3 | D7 target错误 | 🔴 | 裁判·target值 | Gold passes joint (steptest --use-gold: PASS). A spec-faithful entropies() that uses the documented d0 as solve_ivp's initial state (review/work/44/ve… |

### 🟡 题 45 (test) — 7 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 45.3 | D7 target错误 | 🟡 | 题面(description) | Outward-normal sentence is verbatim in the prompt; reran scratch: spec-literal outward impl FAILs 45.3 officially, +axis sign passes, so targets encod… |
| 45.4 | D9 跨步依赖 | 🟡 | 题面(description) | 45.4 tests 1-2 verifiably place nonzero N on top/left; reran step_45.4_outward.py: FAIL, so the 45.3 sign defect double-penalizes in 45.4. |
| 45.1 | D10 文档矛盾 | ⚪ | 题面(description) | Quote accurate ('second and third dimensions are x and y'); literal (Nt,Nx,Ny) impl fails with broadcast error vs target shape (2,5,10), confirming (N… |
| 45.4 | D4 约定不明 | ⚪ | 题面(description) | Prompt never says to apply BCs to slice t=0; reran step_45.4_noBC0.py (BCs only on t>=1): FAILs all 3 tests as claimed. |
| 45.3 | D8 测试过弱 | ⚪ | 裁判·测试用例 | All three 45.3 tests put nonzero N only on left/top (read from test code); reran all-minus impl: PASSes 45.3 officially, so the right/bottom branch is… |
| 45.4 | D4 约定不明 | ⚪ | 题面(description) | Conservative-form scratch FAILs 45.4 as claimed; per-point alpha*laplacian is the more literal reading, so minor severity is right. |
| 45.1 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | All quoted typos verified verbatim: duplicated 'T1' for material 2, 'heat conductivity' for alpha2 (in problem_io and 45.1/45.4 headers), and dangling… |

### 🔴 题 46 (test) — 5 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 46.3 | D5 非确定性 | 🔴 | 理论推导(background) | Target is bit-exact only under the source notebook's 'a + u > 1.0' acceptance idiom; canonical 'u < a' (same RNG stream) fails all 3 tests by ~1 bohr. |
| 46.4 | D5 非确定性 | 🔴 | 理论推导(background) | Frozen-float energy targets are one specific gold-sampler trajectory's fluctuations (analytic K=1, frozen 0.9391); any other correct sampler lands ~1 … |
| 46.4 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Error-bar targets bit-match ddof=0 SEM; the equally standard ddof=1 differs by rel 5e-4 and fails rtol 1e-5 - convention never stated. |
| 46.3 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Prose promises a `hamiltonian` parameter the header doesn't have, and the docstring omits tau/nsteps - tests follow the header, so doc-only. |
| 46.4 | D10 文档矛盾 | ⚪ | 题面(description) | [复核新增] sub_steps[3].step_description_prompt contains a truncated cross-reference: '...and their error bars, using `metropolis` defined in . Inputs  |

### 🔴 题 47 (dev) — 8 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 47.4 | D5 非确定性 | 🔴 | 题面(description) | Reproduced with my OWN independent implementations (review/work/47/verify/, vectorized energy functions, not the first pass's files). Official joint m… |
| 47.4 | D9 跨步依赖 | 🟡 | 裁判·测试用例 | Static: test_cases[1] and [2] of sub_steps[3] contain no np.random.seed call (verified by reading the JSON; only test 1 has np.random.seed(1024)). Dyn… |
| 47.4 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | dispSize ambiguity (variance vs standard deviation). Docstring says only 'dispSize: Size of displacement in Gaussian trial move, float'; gold uses np.… |
| 47.4 | D4 约定不明 | 🟡 | 题面(description) | Sweep structure unstated. Prompt/docstring say only 'MC_steps: Number of MC steps to perform'; the background describes selecting 'a particle' and dis… |
| 47.4 | D10 文档矛盾 | ⚪ | 题面(description) | Static + h5: sub_steps[3].step_description_prompt and problem_description_main both end with 'The output is a MC_steps by 1 float array.' while the he… |
| 47.4 | D10 文档矛盾 | ⚪ | 理论推导(background) | Static: sub_steps[3].step_background says 'Give this particle a random displacement, r(o) -> r(0)+\Delta(Ranf-0.5), where \Delta/2 is the maximum disp… |
| 47.2 | D10 文档矛盾 | ⚪ | 题面(description) | Static: sub_steps[1].step_description_prompt says 'The inputs of the function contain an integer i, a float array r, a N by 3 float array posistions, … |
| 47.4 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | [复核新增] Same prose-vs-header order class as the confirmed 47.2 finding, unflagged by the first pass: sub_steps[3].step_description_prompt says 'The  |

### ⚪ 题 48 (test) — 3 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 48.4 | D10 文档矛盾 | ⚪ | 理论推导(background) | Quotes accurate: problem_io says 'imaginary part', step description says 'obtain chi''', but docstring says 'NEGATIVE of the imaginary part' and backg… |
| 48.4 | D4 约定不明 | ⚪ | 题面(description) | Description only says 'set a fill value of 0' with no interpolation scheme; omega=linspace(-0.2,2.0,10) (step ~0.244) makes -omega off-grid so a schem… |
| 48.2 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Docstring says V_eff in 'inverse of square angstrom', but with 4*pi*e^2=1 and q,kappa in inverse angstrom, V_eff=1/(q^2+kappa^2) is angstrom^2 — label… |

### 🟡 题 49 (dev) — 6 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 49.1 | D10 文档矛盾 | 🟡 | 理论推导(background) | Background quote verified: F_1 = -(G m1 m2/r^2) r_hat with r_hat 'pointing from mass m_1 to mass m_2' is unambiguously repulsive; gold code computes a… |
| 49.1 | D10 文档矛盾 | 🟡 | 函数契约(docstring/header) | Description verbatim says '1D array xin of size 3*N' and '1D array of forces ... 3*N length array' while docstring and tests use 2D (N,3); contradicti… |
| 49.2 | D8 测试过弱 | 🟡 | 裁判·测试用例 | Reproduced: probe_zero_accel.py (rhs[:,3:6]=0, gravity ignored) PASSES official joint scoring; O(1) masses with SI G give \|a\|<=~1e-9 < allclose atol… |
| 49.3 | D8 测试过弱 | 🟡 | 裁判·测试用例 | Same root cause as 49.2 by magnitude arithmetic: gravity corrections ~1e-10..1e-13 are below atol/rtol terms, so Euler and no-gravity integrators are … |
| 49.4 | D4 约定不明 | 🟡 | 题面(description) | Arithmetic verified: (60-30)/0.3==100.0 and 600/0.15==4000.0 exactly, but the accumulate while-loop takes 101/4001 steps (t reaches 59.99999999999998<… |
| 49.4 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Reproduced: probe_rk2_full.py (midpoint RK2 instead of RK4) PASSES the full step officially incl. the energy bool test; the Epot '-2.*ggrav' factor an… |

### 🔴 题 50 (test) — 6 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 50.4 | D10 文档矛盾 | 🔴 | 理论推导(background) | Independent scan (review/work/50/verify/scan_step4_verify.py) vs h5 target test 0 (mean +0.0005191837, std 0.1147205648): J=(A+A.T)/2, fill_diagonal 0… |
| 50.1 | D5 非确定性 | 🟡 | 题面(description) | Re-ran review/work/50/scan_step1.py myself: of 8 variants {site: randint-per-attempt\|sequential} x {attempts: num_steps*N\|num_steps} x {acceptance r… |
| 50.3 | D4 约定不明 | 🟡 | 理论推导(background) | Independent 500-trial scan (review/work/50/verify/scan_step3_verify.py) over fresh draws of the unseeded test inputs, criterion std > f/sqrt(N): f in … |
| 50.4 | D5 非确定性 | 🟡 | 理论推导(background) | Same scan: with the correct J recipe, BATCH replica initialization (draw all num_replicas starting states, then equilibrate each) bit-matches target t… |
| 50.3 | D5 非确定性 | ⚪ | 裁判·测试用例 | Static: grep of review/problems/50.json shows np.random.seed in every test of 50.1 (seeds 1/2/2), 50.2 (1/3), 50.4 (1/3/2) but in NONE of 50.3's three… |
| 50.3 | D8 测试过弱 | ⚪ | 理论推导(background) | [复核新增] An implementation that ignores N entirely (potential_RSB = std(overlaps) > 0.15, hardcoded) passes ALL tests that exercise analyze_rsb: 50.3 |

### ⚪ 题 51 (dev) — 1 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 51.4 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Quotes accurate: docstring says 'num_steps: total steps to run, float' and prompt says 'a float num_steps' (x2), yet gold uses range(num_steps) and al… |

### 🔴 题 52 (test) — 11 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 52.2 | D6 容差脆弱 | 🔴 | 裁判·target值 | Default scipy.integrate.odeint chain bit-matches tests 1-2 targets (maxdiff 6.94e-18 / 4.44e-16, proving it is the reference method) but misses test 3… |
| 52.3 | D6 容差脆弱 | 🔴 | 裁判·target值 | Test 3 (Shoot(2, np.logspace(-3,3.2,1000), 1, [0,-1e-5])) target = -18577.755. Default odeint chain (which bit-matches tests 1-2 at relerr 5.05e-14 / … |
| 52.1 | D8 测试过弱 | 🟡 | 裁判·测试用例 | h5 targets for 52.1 are [-1e-05,-0.0], [-2e-05,0.0], [-2e-05,-0.0]: every u'' component is exactly 0 because all three test_cases set y=[0.0,c] (u=0).… |
| 52.2 | D6 容差脆弱 | 🟡 | 题面(description) | Tests 1-2 targets encode UNCONVERGED default-odeint output: my default-odeint impl matches to 6.94e-18 / 4.44e-16, while the converged truth (DOP853 r… |
| 52.2 | D10 文档矛盾 | 🟡 | 函数契约(docstring/header) | Static: docstring says 'ur: the integration result, float' (sub_steps[1].function_header, quoted from review/problems/52.json) while all three h5 targ… |
| 52.3 | D6 容差脆弱 | 🟡 | 题面(description) | Default-odeint chain matches tests 1-2 targets to relerr 5.05e-14 / 7.69e-14 (bit-level, confirming both the formula and the reference method). Conver… |
| 52.4 | D7 target错误 | 🟡 | 函数契约(docstring/header) | Targets hold nmax+1 states per call: test 1 shape (33,2) = sum over l=0..5 of (7-l)+1; test 2 (18,2) = sum over l=0..3 of (5-l)+1. Ran both readings t… |
| 52.4 | D6 容差脆弱 | 🟡 | 裁判·测试用例 | [复核新增] First pass's step note claimed 'Bound-state energies themselves are robust to integrator noise' -- this is FALSE for the shallowest states.  |
| 52.4 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Test 3 asserts np.isclose(Bnd[0], (0,-1)).any() == target.any() with target=[True,True] -> RHS always True. Verified: Bnd[0]=(0,42.0) -> assert True (… |
| 52.4 | D9 跨步依赖 | ⚪ | 裁判·测试用例 | Static: test_cases[1] and [2] use y0 in 'FindBoundStates(y0, R,l,nmax-l,Esearch)' without defining it; only test_cases[0] sets y0=[0,-1e-5]. Dynamic: … |
| 52.4 | D10 文档矛盾 | ⚪ | 题面(description) | Static: 52.4 prompt says 'using the Shoot(En,R,l) function for a given maximum angular momentum quantum number l' but 52.3's header is def Shoot(En, R… |

### 🟡 题 53 (test) — 3 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 53.1 | D10 文档矛盾 | 🟡 | 题面(description) | Quotes accurate; written PDF f=(1/a)exp(-Dt/a) has mean a (scale=a in numpy) but Gillespie/target need mean 1/a (scale=1/a); target reproduces exactly… |
| 53.2 | D4 约定不明 | 🟡 | 题面(description) | Contract is silent on whether the event crossing T is recorded; target excludes it (n=3467, last_t<T), so a naive while-t<T loop records one extra row… |
| 53.3 | D10 文档矛盾 | ⚪ | 题面(description) | 'rounded up to one decimal point' is round-to-nearest in targets (0.6283->0.6, not ceil's 0.7); literal ceil reading fails 53.3/53.4. Real but minor w… |

### 🔴 题 54 (test) — 10 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 54.2 | D7 target错误 | 🔴 | 题面(description) | Wrote my OWN gold-matching solution (review/work/54/verify/v_gold.py: full-hat basis, kappa=1, Pe=200 FIXED in tau, Nitsche-only stabilization, column… |
| 54.4 | D9 跨步依赖 | 🔴 | 裁判·测试用例 | v_specbasis.py = v_gold with ONLY basis() replaced by the 54.1-spec-literal half-element functions (omega^1_i=(x-x_{i-1})/h on [x_{i-1},x_i] only, ome… |
| 54.2 | D2 信息缺失/无法做出 | 🟡 | 题面(description) | Regex-scanned all of review/problems/54.json for kappa assignments: the parameter lists give only s_kappa=1, a=200, V_kappa=Ch^{-1}(1+\|s_kappa\|), C=… |
| 54.3 | D10 文档矛盾 | 🟡 | 题面(description) | Step 3 prompt verbatim: 'Write a function adjust mass matrix A and right hand side vector b, adding Nitsche term and SUPG stabilization term.' and its… |
| 54.4 | D7 target错误 | 🟡 | 函数契约(docstring/header) | Docstring verbatim: 'sol: solution array, 1d array of size (N+1,)' (and problem_io says the same). h5 targets for tests 1-3 are 2-D columns (33,1)/(65… |
| 54.2 | D7 target错误 | 🟡 | 函数契约(docstring/header) | Docstring verbatim: 'b: right hand side vector , 1d array size M*1' -- self-contradictory ('1d' vs 'M*1'). h5 b targets are (11,1)/(23,1)/(35,1) colum… |
| 54.1 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Loaded 54.1 targets: [0.], [1.0, 0.2], [0., 0., 0.] -- 2 of 3 all-zero (test points far outside any support: i=1,p=0.2,h=0.1 and i=3,p=[5,7,9],h=0.01)… |
| 54.1 | D10 文档矛盾 | ⚪ | 理论推导(background) | Static, quoted from review/problems/54.json: step background says input 2 is 'An array containing coordinates of nodal degree of freedom (mesh)' but t… |
| 54.4 | D10 文档矛盾 | ⚪ | 题面(description) | Static, quoted verbatim from sub_steps[3].step_description_prompt: 'Write a function to solve formed linear system using , and functions.' -- function… |
| 54.3 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | [复核新增] stabilization's docstring says 'b : right hand side vector, 1d array of shape (M,)' for BOTH input and output, but the tests pass b as (M,1) |

### 🟡 题 55 (test) — 9 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 55.4 | D7 target错误 | 🟡 | 裁判·target值 | Reproduced independently. (a) Direct diff vs h5 target test0: exp-propagator scheme with n=9999 steps matches target u to maxabs 7.79e-12; n=10000 mis… |
| 55.3 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Reproduced. Bin-center identities verified bit-exact: 55.3 test0 target 0.9774342463948407 == 5.5*sqrt(2)*pi/25 (N=50, nbins=N//2=25 over [0, max\|k\|… |
| 55.1 | D4 约定不明 | 🟡 | 理论推导(background) | Reproduced. Official steptest 55.1: exact exponential k-space propagator exp(dt*(2k^2/q0^2 - k^4/q0^4)) + explicit-Euler local substep -> PASS (test2 … |
| 55.2 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Reproduced (normalization). Raw Sk = fftshift(\|fft2(u)\|^2) matches the test0 target to maxabs 2.8e-13 (target max 33366.6). Official steptest 55.2: … |
| 55.2 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Reproduced at bit level. Target Kx varies along axis 0 (Kx[:4,0]=[-3.142,-2.827,-2.513,-2.199], Kx[0,:4] constant -3.142) == np.meshgrid(k,k,indexing=… |
| 55.1 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Reproduced: h5 target for 55.1 test0 is all zeros (max\|.\| = 0.0); the identity 'return u' (and any zero-preserving function) satisfies np.allclose f… |
| 55.4 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Reproduced: 55.4 test2 (epsilon=-0.5) target has \|u\|max=3.87e-13 and Sk_max=6.96e-20, both below cmp_tuple_or_list's atol=1e-8, with (False, 0) for … |
| 55.3 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | [复核新增] Docstring output name 'peak_near_q0_location' vs return_line 'return peak_found_near_q0, peak_location_near_q0' — inconsistent variable nami |
| 55.3 | D8 测试过弱 | ⚪ | 裁判·测试用例 | [复核新增] The proximity criterion's rejection branch is never exercised by any test in 55.3 or 55.4: every False-target case has NO peak above min_hei |

### ✅ 题 56 (test) — 无确认缺陷

### 🟡 题 57 (test) — 4 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 57.4 | D4 约定不明 | 🟡 | 题面(description) | h5 target for [0,-2,3,-4,-5] is 2 (strict product<0 convention); the equally standard np.diff(np.sign(a))!=0 convention gives 3 and fails; prompt says… |
| 57.5 | D4 约定不明 | 🟡 | 题面(description) | h5 targets are exact Estep=1e-4 grid values (1.0289, 1.0288/5.0713/9.0960; odd states ~integers), confirming unrefined scan recording; quantization 1e… |
| 57.2 | D4 约定不明 | ⚪ | 题面(description) | Prompt/docstring/background give no u[1] seed; h5 target test 0 has u[1]=1.0 exactly (Euler seed; Taylor seed gives ~0.846 with h^2/2*f0=-0.154), so o… |
| 57.2 | D4 约定不明 | ⚪ | 题面(description) | All 57.2/57.3 tests verifiably pass step=x[0]-x[1]<0; h5 test-2 target starts [0, -0.05050505...] = negative of the physical u'(0)=+1 solution, so h=a… |

### 🔴 题 58 (test) — 8 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 58.3 | D8 测试过弱 | 🔴 | 裁判·测试用例 | Static: all three 58.3 test_cases read 'assert np.allclose(eos_rho_from_press(press, eos_Gamma, eos_kappa), target)' — the step's own function eos_eps… |
| 58.4 | D10 文档矛盾 | 🟡 | 理论推导(background) | Static: step_background contains '$$\n\\frac{dm}{dr} = 4 \\pi r^3 \\mu,\n$$' (verbatim). Target check: 58.4 test1 component [1] = 1.38230077e9 = 4*pi*… |
| 58.5 | D4 约定不明 | 🟡 | 题面(description) | Ran review/work/58/verify/variants.py (my own code). Baseline (odeint default tolerances on linspace(0,rmax,npoints), surface = first grid point with … |
| 58.5 | D6 容差脆弱 | 🟡 | 题面(description) | My variants.py: odeint with rtol=1e-10/atol=1e-12 (same surface convention as the passing baseline): 1/4 pass — converged masses test1 M=0.123363112 v… |
| 58.2 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Static quote from sub_steps[1].function_header docstring: 'Outputs:\n eps: the specific internal energy corresponding to the given pressure, a float.'… |
| 58.3 | D10 文档矛盾 | ⚪ | 题面(description) | Static quotes: step_description_prompt says 'computes specific internal energy given density. The function shall take as input the density `rho`...' w… |
| 58.4 | D4 约定不明 | ⚪ | 裁判·测试用例 | Static: test 2 input data=(0.3, 1e3, 1.0), r=20 gives r-2m = 20-2000 = -1980 < 0 (point inside its own Schwarzschild radius). Hand-evaluated the verba… |
| 58.5 | D10 文档矛盾 | ⚪ | 题面(description) | Static quotes: sub_steps[4] prompt says 'Use the functions `press_from_rho` to compute the required quanties' and sub_steps[3] prompt says 'Use the fu… |

### 🟡 题 59 (test) — 5 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 59.2 | D4 约定不明 | 🟡 | 裁判·测试用例 | Re-ran probe_literal.py: literal exp(-i theta Y1X2)\|01> implementation FAILS 59.2 (vdot=+i, phase-sensitive test); only Rx(pi)-prepared state with it… |
| 59.3 | D8 测试过弱 | 🟡 | 裁判·测试用例 | Hand-checked tests 1-2: CNOT21\|11>=\|01> and CNOT21(HxH)\|-->=\|01>, both give <Z1>=+1; all targets ~+1 so 'return 1.0' and the missing-Z bug pass, m… |
| 59.2 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Test asserts vdot(o,c)==\|o\|\|c\|, which is trivially true for c=0 (0==0) and invariant under positive scaling of c; no normalization check. Math hol… |
| 59.4 | D8 测试过弱 | ⚪ | 裁判·测试用例 | test_cases[1] and [2] are byte-identical (same gl, theta=pi/6) in problems/59.json; only 2 distinct probes for a 6-coefficient Hamiltonian. |
| 59.1 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Scaffold return line is literally 'return Rz' while docstring output is 'R'; quote accurate, impact correctly rated minor. |

### 🔴 题 60 (test) — 11 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 60.4 | D7 target错误 | 🔴 | 函数契约(docstring/header) | h5 dump (my own): target for test 1 (N2=10, rho2=1) = (positions[:10] shape (10,3), L=2.154434690031884=(10/1)^(1/3), len=int32(27)) — the reference f… |
| 60.5 | D6 容差脆弱 | 🔴 | 裁判·测试用例 | All first-pass numbers reproduced exactly with my own driver (review/work/60/verify/driver_t2.py): uncorrected-mu MC -> mean rel dev +0.096467 vs the … |
| 60.2 | D10 文档矛盾 | 🟡 | 理论推导(background) | Static: background labels the potential '$V^{tr-sh}_{LJ}(r)$' and states 'The potential is truncated and shifted at a distance $r_c$', but the display… |
| 60.3 | D5 非确定性 | 🟡 | 函数契约(docstring/header) | My own code: single insertion drawn as np.random.uniform(0, L, 3) from the legacy global RNG -> steptest PASS 3/3 (test 1 value 1.0001280843865346 bit… |
| 60.4 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | h5 dump: test 0 (N=8, rho=1) rows [0.5,0.5,0.5],[0.5,0.5,1.5],... -> cell-centered (i+0.5)*L/n with z varying fastest. steptest: corner-anchored grid … |
| 60.5 | D10 文档矛盾 | 🟡 | 理论推导(background) | Static: problem_io documents 'mu_ext: Extended chemical potential, adjusted for potential truncation' and 'E_array: Energy array corrected for potenti… |
| 60.2 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Static: header docstring reads 'sigma : float, the distance at which the potential minimum occurs' — wrong (LJ minimum is at 2^(1/6) sigma); backgroun… |
| 60.3 | D10 文档矛盾 | ⚪ | 裁判·测试用例 | Static, verified against my own h5 dump: inline comments vs frozen targets — test 0 'Expected to be 1.0185805629757558' vs target 1.7230317731351154e-… |
| 60.3 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Verified: np.allclose(0.0, 1.7230317731351154e-149) -> True (target far below atol=1e-8), so test 0 individually accepts any \|x\|<=~1e-8 including ha… |
| 60.5 | D10 文档矛盾 | ⚪ | 题面(description) | Static, verbatim: step_description_prompt lists 'positions: An array of (x, y, z) coordinates for every particles' and 'L: The length of each side of … |
| 60.5 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Static: both tests only ever assert on mu_ext (test 0: 'assert (np.mean(mu_ext_list) == 0) == target'; test 1: the ref band) — E_array, n_accp, accp_r… |

### 🔴 题 61 (test) — 4 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 61.1 | D7 target错误 | 🔴 | 裁判·target值 | Wrote my own Busing-Levy Bmat (review/work/61/verify/sol_bl.py) and my own inv(A) Bmat (sol_inva.py) from scratch. steptest joint: sol_bl.py FAILS 61.… |
| 61.5 | D8 测试过弱 | ⚪ | 裁判·测试用例 | All 61.3/61.4/61.5 test cases use (a,b,c,alpha,beta,gamma)=(5.39097,5.39097,5.39097,90,90,90) (read from sub_steps JSON), for which every B convention… |
| 61.3 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Static check of review/problems/61.json: 61.3 function_header line reads verbatim 'z_s: step size in the \phi rotation, float in the unit of degree' w… |
| 61.5 | D10 文档矛盾 | ⚪ | 理论推导(background) | Static check, verbatim from review/problems/61.json: step_background starts 'Background\nEmploy step to calculate the momentum transfer $\vec{Q}$\n2. … |

### 🔴 题 62 (test) — 3 缺陷  (1存疑)

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 62.5 | D5 非确定性 | 🔴 | 裁判·测试用例 | Reproduced via reviewer's scratch: rho eigvals [0.9330127, 0.0223291 x3] degenerate to 1.2e-16; energy/H match target exactly while conn_Sz maxdiff=0.… |
| 62.1 | D1 签名不匹配 | ⚪ | 函数契约(docstring/header) | Header quote accurate: single 'class EnlargedBlock:' with __init__/print_all duplicated twice, 'class Block:' line missing, while prompt says 'Create … |
| 62.6 | D8 测试过弱 | ⚪ | 裁判·测试用例 | test_cases[2] and [5] are character-identical 'run_dmrg(block, 100,100, model_d)' and h5 targets are bitwise equal (-44.12773975752229 == -44.12773975… |

### 🟡 题 63 (test) — 11 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 63.1 | D1 签名不匹配 | 🟡 | 裁判·测试用例 | Header is (..., max_price, min_price); tests of 63.1/63.2/63.4 all pass (min, max); h5 target verified: p = linspace(log(500),log(20)) descending, dp … |
| 63.2 | D10 文档矛盾 | 🟡 | 理论推导(background) | Background's only payoff equation is V(t_max,p)=max(K-s,0) (put); h5 target V[1,-1]=1494.6997=exp(p[1])-K, i.e. call payoff max(s-K,0), contradicting … |
| 63.4 | D9 跨步依赖 | 🟡 | 裁判·测试用例 | 63.4 test repeats the swapped (min,max) call; h5 verified V[-1,0]=-375.6147=100-500e^{-0.05} on the inverted grid, while 63.5 target is on the ascendi… |
| 63.1 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Docstring says 'shape: price_step * 1' (and 63.2 says '1 * N_p'); h5 target is 1-D shape (5000,); (N,1) return fails allclose by broadcast. |
| 63.2 | D4 约定不明 | ⚪ | 裁判·target值 | h5 verified: V[0,:]=0 sits at the highest-price row and V[-1,0]=-680.1987=300-1000e^{-0.02} (negative call price); only blind index-literal boundary p… |
| 63.2 | D4 约定不明 | ⚪ | 理论推导(background) | h5 corners verified: V[0,-1]=0 (payoff would be 1500) and V[-1,-1]=-700 (payoff would be 0), so price boundary must overwrite payoff at corners; unsta… |
| 63.3 | D4 约定不明 | ⚪ | 函数契约(docstring/header) | Tests do call .toarray() and docstring never states sparse; real, but required_dependencies explicitly import scipy.sparse + spsolve, making sparse th… |
| 63.3 | D10 文档矛盾 | ⚪ | 理论推导(background) | Background literally reads aV^n_{j-1}+bV^n_j+cV^n_{j-1} (j-1 twice); typo confirmed, resolvable from the discretized equation above it. |
| 63.4 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | 63.4 docstring says D shape (N_t-2)x(N_t-2); 63.3's own docstring and targets give (N_p-2)x(N_p-2); tests use N_p=1000 vs N_t=2000 so materially wrong… |
| 63.6 | D4 约定不明 | ⚪ | 函数契约(docstring/header) | Docstring gives no read-off convention; h5 target 43.85910767618714 matches the reviewer's np.interp value to ~2e-11 relative, while nearest-grid look… |
| 63.6 | D4 约定不明 | ⚪ | 裁判·测试用例 | Test 0 has S0=100 below min_price=200 and the h5 target is exactly 0.0 (clamp artifact; true BS value ~1.17); confirmed. |

### 🔴 题 64 (test) — 8 缺陷  (1假阳性)

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 64.2 | D1 签名不匹配 | 🔴 | 裁判·测试用例 | Wrote 3 independent dist() variants and ran `steptest --problem 64 --step 64.2 --code ...` (joint=official): (a) docstring-compliant `return float(...… |
| 64.4 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Test 4 input: r3=positions3=[1e-8,1e-8,1e-8] -> pair distance exactly 0.0; h5 target = np.float64(inf) (dumped via process_hdf5_to_tuple). Ran steptes… |
| 64.6 | D5 非确定性 | 🟡 | 裁判·测试用例 | Wrote my own vectorized GCMC (variant A, insertion-branch-first) and a physically identical variant B that merely checks the deletion branch of the sa… |
| 64.6 | D8 测试过弱 | 🟡 | 裁判·测试用例 | Test text confirmed: epsilon=0 (ideal gas) and the single assert touches only Num_particle_Trace and the function's OWN returned Lambda. Built variant… |
| 64.6 | D10 文档矛盾 | ⚪ | 题面(description) | Verbatim from sub_steps[5].step_description_prompt: 'The argon mass in kg is 39.95*e-27, Lennard Jones epsilon for argon in real unit real_epsilon is … |
| 64.3 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Verbatim extraction from the problem JSON: the sigma param doc reads 'The distance at which the potential minimum occurs' in the function_header of 64… |
| 64.4 | D10 文档矛盾 | ⚪ | 题面(description) | Verbatim from sub_steps[3].step_description_prompt: 'The inputs of the function contain an integer i, a float array r, a N by 3 float array posistions… |
| 64.5 | D10 文档矛盾 | ⚪ | 理论推导(background) | Verbatim: 64.5's function_header docstring first line is 'Calculate the total Lennard-Jones potential energy of a particle with other particles in a p… |

### 🟡 题 65 (test) — 8 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 65.1 | D1 签名不匹配 | 🟡 | 函数契约(docstring/header) | Header is literally 'def tensor():' with zero params while all 3 tests pass positional args; quote accurate, matches recurring empty-header pattern. |
| 65.2 | D4 约定不明 | 🟡 | 理论推导(background) | Neither prompt, docstring, nor background states the index base; test 3 uses sys=[2] with dim=[2,2], only consistent under 1-based labels (0-based has… |
| 65.1 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Verified h5 65.1/test1 target is shape (4,) int32 [0 0 0 1] — 1-d, contradicting docstring's '2d array of floats'; column-ket reading would fail. |
| 65.3 | D8 测试过弱 | ⚪ | 裁判·测试用例 | All three test inputs are 4x4 (n=1) despite the 2n-qubit general spec; an n=1-hardcoded impl passes here and only fails later at 65.4/65.6. |
| 65.3 | D10 文档矛盾 | ⚪ | 题面(description) | Prompt reads verbatim '...using the apply_channel function in .' — step reference dropped; quote accurate, intent recoverable from the function name. |
| 65.4 | D10 文档矛盾 | ⚪ | 理论推导(background) | Background states rho''=V rho' V^dagger with V being 2^n x 2 ('with 2^n rows') — dimensionally impossible (needs rho' 2x2); correct direction is V^dag… |
| 65.6 | D9 跨步依赖 | ⚪ | 函数契约(docstring/header) | Test 3 y_error Kraus contains -1j*np.sqrt(0.1) (complex) while 65.2/65.3/65.6 docstrings all declare 'floats'; a float-preallocated accumulator faithf… |
| 65.6 | D10 文档矛盾 | ⚪ | 题面(description) | Prompt reads verbatim '...using the protocol in given by the function ghz_protocol' — step reference dropped between 'in' and 'given'; quote accurate. |

### 🔴 题 66 (test) — 8 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 66.6 | D4 约定不明 | 🔴 | 函数契约(docstring/header) | Wrote my own faithful implementation of the displayed equation E = sum_i sum_j Tap(r_ij) V_ij (v_666_sum.py) -> steptest FAIL. Same code with '/ (len(… |
| 66.1 | D4 约定不明 | 🟡 | 题面(description) | Wrote my own independent implementations. Blocked ordering (all A atoms then all B at offset (0, a/sqrt(3)); a1=(a,0), a2=(a/2, a*sqrt(3)/2); i outer … |
| 66.2 | D4 约定不明 | 🟡 | 题面(description) | Geometry check: on generate_monolayer_graphene(0,2.46,1.8,1) (the test's own 18-atom flake), atom 14 at (1.23, 3.5507) has argsort-3-nearest distances… |
| 66.6 | D10 文档矛盾 | 🟡 | 题面(description) | Static: the step prompt commands verbatim 'Use the following values for KC parameters:\nz0 = 3.416084\nC0 = 20.021583\nC2 = 10.9055107\nC4 = 4.2756354… |
| 66.2 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Static, quoted verbatim from review/problems/66.json: step description says 'Return the normalized normal vectors of shape `(natoms,)`' and docstring … |
| 66.2 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Loaded targets: all rows of each (18,3) target are identical (0,0,-1) for z>0 and (0,0,+1) for z<0 (np.unique over rows gives a single row per test). … |
| 66.5 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Targets are [1.0, 0.5, 0.0] for r=0,8,16 (loaded from h5 myself). My branchless probe omitting the required 'zero when x_ij > 1' rule (v_665_nobranch.… |
| 66.6 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Tests 3-5 read verbatim 'assert (np.abs(energy - energy_ref < 2)) == target' with h5 targets all boolean True (loaded myself). Precedence makes this o… |

### 🟡 题 67 (test) — 3 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 67.6 | D6 容差脆弱 | 🟡 | 裁判·测试用例 | Test 3 quote accurate (tol=1e-15 boolean); official steptest on reviewer's correct inline-D0 variant (sol_inline.py) fails exactly at the NUM-ANA asse… |
| 67.6 | D8 测试过弱 | 🟡 | 裁判·测试用例 | Reran probe: bare D0 passes tests 0-2 (\|D0-target\|~5e-10..9e-10 vs atol 1e-8, \|target\|~1.5e-8), 2x/0.5x V_q and conjugate also pass, and NUM=ANA=D… |
| 67.3 | D10 文档矛盾 | ⚪ | 理论推导(background) | Grep of problems/67.json shows 5 dangling 'step .' / 'step "' references matching the quoted locations; referents recoverable, so minor is right. |

### 🔴 题 68 (test) — 9 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 68.5 | D5 非确定性 | 🔴 | 理论推导(background) | Canonical textbook implementation (accept where acc > u, identical RNG consumption: chi normal then nconf uniforms per step) -> 'RESULT step 68.5: FAI… |
| 68.8 | D5 非确定性 | 🔴 | 题面(description) | Canonical documented-algorithm impl (impl_full.py) -> 'RESULT step 68.8: FAIL' (official joint); its test 5 (statistical boolean) passes in isolation … |
| 68.3 | D6 容差脆弱 | 🟡 | 裁判·测试用例 | Re-ran the six test bodies myself (review/work/68/verify, inline script): product-form Slater.value = np.prod(np.exp(-alpha*r), axis=1) reproduces ALL… |
| 68.6 | D10 文档矛盾 | 🟡 | 函数契约(docstring/header) | Computed drift_new / wf.gradient(configs_new) elementwise on the actual test inputs: all six components = 0.02 exactly (drift_old/grad_old likewise ~0… |
| 68.6 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | h5 targets for tests 2-3 are 2.59191777 and 17.42071956 (> 1), so the RAW Metropolis-Hastings quotient is required; v_minratio.py (return min(1, ratio… |
| 68.7 | D4 约定不明 | 🟡 | 题面(description) | step_background is the empty string and the prompt names no resampling algorithm. My multinomial impl np.random.choice(nconfig, nconfig, p=w/sum(w)) (… |
| 68.7 | D8 测试过弱 | 🟡 | 裁判·测试用例 | h5 dump: all three targets are the identical vector [5 7 6 5 4 6 4 8 9 3] despite three different weight inputs (all weights within ~1.5% of 1.0; seed… |
| 68.5 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Static check of review/problems/68.json sub_steps[4]: function_header docstring says 'wf (wavefunction object): MultiplyWF class' while all three test… |
| 68.5 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | [复核新增] step_description_prompt promises a parameter the header doesn't have: 'Write a Python function that performs Metropolis algorithms given the |

### 🔴 题 69 (test) — 6 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 69.5 | D7 target错误 | 🔴 | 裁判·target值 | h5 targets match quoted values; reviewer's pipeline (which passes 69.4 at atol=rtol=1e-13) gives pole 12.457530648/15.748936871/19.312288533 vs target… |
| 69.7 | D4 约定不明 | ⚪ | 题面(description) | alpha appears only inside step 7's formula and is never defined anywhere in the problem text (step 1 background gives q'=(eps-eps0)/(eps+eps0)q unname… |
| 69.7 | D8 测试过弱 | ⚪ | 裁判·测试用例 | h5 target 8.126205579652762e-09 < default atol 1e-8, so np.allclose(0, target)=True and a zero return passes test 0; 69.8 test 0 (8.1262e-9) same, 69.… |
| 69.8 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Re-ran steptest 69.8 with the scratch impl_lazy8.py whose I_Raman_num ignores N and returns the step-7 closed form: PASS 4/4 in official joint mode, i… |
| 69.2 | D8 测试过弱 | ⚪ | 裁判·测试用例 | All three 69.2 test cases set gamma = 0 (read from test_cases) while 69.4 feeds gamma=0.3 and 69.6-69.8 gamma=0.1 through D_2DEG, so a gamma bug is mi… |
| 69.1 | D10 文档矛盾 | ⚪ | 理论推导(background) | All quoted artifacts verified in problems/69.json: '[<u>duplicate LEG_Dyson equation-bulk step </u>]' in 69.1/69.2/69.3, dangling refs 'as described i… |

### 🔴 题 70 (dev) — 7 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 70.8 | D6 容差脆弱 | 🔴 | 裁判·测试用例 | steptest 70.8 --use-gold joint -> FAIL; --isolate -> 3/4 pass, test 4 (index 3) fails. My own re-run of gold vs h5 target for test 4 on numpy 2.2.6: m… |
| 70.7 | D10 文档矛盾 | 🟡 | 理论推导(background) | Wrote my OWN full-stack implementation (review/work/70/verify/step7_verbatim.py) implementing the background's displayed closed form u_k = sum_m e^{iL… |
| 70.1 | D1 签名不匹配 | ⚪ | 裁判·测试用例 | Static: header is pmns_mixing_matrix(s12, s23, s13, dCP); every test defines s12, s13, s23 and calls pmns_mixing_matrix(s12,s13,s23,dCP) -- value name… |
| 70.1 | D4 约定不明 | ⚪ | 函数契约(docstring/header) | type(1/cmath.sqrt(2)) is complex ((0.7071067811865475+0j)) while docstring says 's12 : Sin(theta_12); float'. math.sqrt(1 - s12**2) raises TypeError: … |
| 70.1 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Docstring: 'pmns: numpy array of floats with shape (3,3)'. h5 targets for all 3 tests are complex128; test 2 (dCP=1) target has max \|imag\| = 0.4207,… |
| 70.5 | D8 测试过弱 | ⚪ | 裁判·测试用例 | h5 targets: test0 = 0j exactly, test1 = -5.598e-9 (below allclose atol 1e-8), test2 = -1.616e-7. My own probe with 'def star_product(i, h): return 0.0… |
| 70.6 | D8 测试过弱 | ⚪ | 裁判·测试用例 | h5 targets for the h3 = <h> element: 1.1611e-11, 1.1611e-11, 1.4514e-9 -- all below allclose atol 1e-8, so that returned element is never verified. My… |

### 🟡 题 71 (test) — 11 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 71.1 | D1 签名不匹配 | 🟡 | 函数契约(docstring/header) | Header 'def ket(dim):' has one param; all 3 tests call ket(a, b) with two args; docstring lists 'args' missing from signature. |
| 71.1 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | h5 target for ket(2,0) is shape (2,1); checked allclose(np.array([1.,0.]), target)=False, so the docstring's '1-D dim-dimensional array' reading fails… |
| 71.2 | D1 签名不匹配 | 🟡 | 函数契约(docstring/header) | Header 'def tensor():' takes zero params; every test passes 2 positional args -> TypeError under the literal contract. |
| 71.3 | D4 约定不明 | 🟡 | 理论推导(background) | Full prompt/docstring read: no 1-based statement anywhere; test uses sys=[2] on dim=[2,2]; background indeed overloads i for Kraus and subsystem index… |
| 71.4 | D4 约定不明 | 🟡 | 题面(description) | Prompt says only 'order specified by perm'; tests use 1-based perms [2,1]/[1,3,2] (no 0), 0-based reading crashes; solver never sees tests. |
| 71.5 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Docstring quote accurate, no base stated; tests use sys=[2] on dim=[2,2] and sys=[1] on [3,2], so 0-based tracing crashes/mis-traces. |
| 71.6 | D4 约定不明 | 🟡 | 理论推导(background) | Prompt is one sentence with no formula/base; h5 targets re-read: 2.0 and 0.721928 = base-2 (ln gives 1.386/0.500); deps really import scipy.linalg.log… |
| 71.2 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | h5 target for tensor([0,1],[0,1]) is 1-D shape (4,) despite docstring promising '2d array'; checked (4,1) column result fails allclose. |
| 71.4 | D8 测试过弱 | ⚪ | 裁判·测试用例 | All test perms ([2,1],[2,1],[1,3,2]) are involutions, so perm==perm^-1 and source/destination conventions are provably indistinguishable; minor is rig… |
| 71.8 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Docstring says 'negative of coherent information'/'neg_I_c' while description says REVERSE coherent info with explicit formula I_R=S(A)-S(AB); both qu… |
| 71.9 | D10 文档矛盾 | ⚪ | 题面(description) | Quote accurate: prompt reads 'by using neg_coh_info in .' (dropped reference, wrong function name), and background's sqrt(p)\|00>+sqrt(1-p)\|11> contr… |

### 🔴 题 72 (test) — 9 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 72.5 | D7 target错误 | 🔴 | 函数契约(docstring/header) | Loaded h5: 72.5 test-1 target = (54.598150033144236, 2) and np.isclose(54.598..., exp(4)) is True, i.e. exp(-beta*dH) with dH=-4 and NO min cap. Built… |
| 72.6 | D5 非确定性 | 🟡 | 函数契约(docstring/header) | My literal baseline (one np.random.random() draw per site, row-major) passes 72.6 (steptest PASS). One-line variant shortcircuit.py ('if A >= 1 or np.… |
| 72.7 | D4 约定不明 | 🟡 | 题面(description) | Neither prompt nor docstring mentions lattice initialization. My baseline with lattice = np.random.choice([-1, 1], (N, N)) passes 72.7 (steptest PASS)… |
| 72.8 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Prompt only says 'returns a list of magnetization^2/N^4 at each temperature'; the per-temperature reduction and RNG bookkeeping are unstated. Baseline… |
| 72.8 | D9 跨步依赖 | 🟡 | 题面(description) | Built colmajor.py (identical to baseline except flip() iterates j outer / i inner). steptest results: 72.6 PASS, 72.7 PASS, 72.8 FAIL (all official jo… |
| 72.9 | D4 约定不明 | 🟡 | 题面(description) | Computed all four conventions against the targets (2.25, 2.3, 2.2) with my own chain: diff-left = (2.25, 2.3, 2.2) matches all three; np.gradient = (2… |
| 72.7 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Quoted from problem JSON: prompt says 'collects magnetization^2 / N^4' but docstring Return reads 'mag2: (numpy array) magnetization^2' (no /N^4); doc… |
| 72.7 | D8 测试过弱 | ⚪ | 裁判·测试用例 | Loaded h5 targets for 72.7: np.array_equal(target_test1, target_test2) is True ([1.0 x6, 0.60493827, 0.30864198, 0.60493827, 0.30864198] for both T=2.… |
| 72.2 | D10 文档矛盾 | ⚪ | 题面(description) | Quoted verbatim from review/problems/72.json: 72.2 prompt ends '...whose element is either 1 or -The `neighbor_list` function is given in .' (the '-1.… |

### 🔴 题 73 (test) — 9 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 73.1 | D7 target错误 | 🔴 | 裁判·target值 | Wrote my own textbook Busing-Levy B (columns=b_i, x*//a*, z*//a*xb*, a_i.b_j=delta_ij) -> steptest 73.1 FAIL (all 3 tests; test 3 max diff 0.044 vs ta… |
| 73.6 | D6 容差脆弱 | 🔴 | 裁判·测试用例 | Static: are_dicts_close begins 'if dict1.keys() != dict2.keys(): return False' - exact float equality on d* keys. Dynamic (my own fresh ringdstar, B=i… |
| 73.6 | D4 约定不明 | 🔴 | 裁判·target值 | Static: docstring promises 'each item is a sorted list', but target rings are NOT lexicographically sorted: test1 ring 0.32129 = [(-1,-1,-1),(1,1,1),(… |
| 73.7 | D4 约定不明 | 🔴 | 裁判·target值 | My fresh implementation: set(ha)==set(target_ha) and set(hb)==set(target_hb) in ALL 3 tests, steptest 73.7 FAIL. With my lexicographically sorted list… |
| 73.8 | D6 容差脆弱 | 🔴 | 题面(description) | My own reimplementation: test 1 has 24 candidate (h1,h2) pairs passing any angle filter (all have identical theoretical angle 35.264 deg vs observed 3… |
| 73.9 | D6 容差脆弱 | 🔴 | 裁判·target值 | My fresh auto_index: tests 1-3 FAIL np.allclose, but row-wise sorted \|hkl\| matches the target with atol 0.05 on every peak of every test - my output… |
| 73.2 | D4 约定不明 | ⚪ | 函数契约(docstring/header) | Tested three readings against h5 targets (review/work/73/verify/q_variants.py): (a) detector axes rotated, pivot at beam-center pixel placed det_d alo… |
| 73.3 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Static: problem_io and every docstring say 'z_s: step size in the \phi rotation', while the 73.3 prompt says 'During experiments, we rotate $\theta$ a… |
| 73.6 | D10 文档矛盾 | ⚪ | 题面(description) | Static, quoted: step_description_prompt = 'Calculate $d^* = 1/d$, where $d$ is the lattice spacing of the reciprocal lattice for a given $(h,k,l)$' - … |

### ⚪ 题 74 (test) — 1 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 74.1 | D4 约定不明 | ⚪ | 题面(description) | Verified: background quote accurate; np.linalg.qr (LAPACK convention) matches the literal impl on tests 1-2 to machine precision but differs only at R… |

### 🔴 题 75 (test) — 3 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 75.3 | D2 信息缺失/无法做出 | 🔴 | 题面(description) | Re-implemented from scratch (review/work/75/verify/). steptest official joint: bespoke hop set (intralayer NN only + interlayer vertical d=6.50 + firs… |
| 75.2 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | steptest official joint: convention A, d_vec = basis[ai] - (basis[aj] + di*latvecs[0] + dj*latvecs[1]) -> PASS (v_step2_convA.py). Mirror convention B… |
| 75.1 | D10 文档矛盾 | ⚪ | 题面(description) | Exact prompt text quoted from JSON: '$b$ = (b,a.u.)$^{-1}$, $a_0$ = 2.68 b, a.u., $d_0$ = 6.33 b, a.u.' -- the value 1.17 for the decay constant b is … |

### 🔴 题 76 (test) — 5 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 76.1 | D7 target错误 | 🔴 | 函数契约(docstring/header) | Wrote two impls. L1 (per prompt: row/row.sum after +1): steptest --problem 76 --step 76.1 -> FAIL all 3. L2 (mat/np.linalg.norm(axis=1) after +1): -> … |
| 76.2 | D9 跨步依赖 | 🔴 | 裁判·target值 | compute_kld = sum(P*ln(P/0.25)). With L2 upstream (76.1 reference): steptest 76.2 -> PASS all 3 (target test0=10.10996 matches ln on L2 matrix). With … |
| 76.4 | D5 非确定性 | 🔴 | 裁判·测试用例 | Targets test0=163 (N=240), test1=654 (N=1000). Verified random.seed(42); random.randint(0,N-1) as the FIRST draw == 163 and 654 exactly. The targets A… |
| 76.2 | D4 约定不明 | 🟡 | 题面(description) | Step prompt gives D_KL(P\|\|Q)=sum P log(P/Q) with no log base. Natural log on L2 matrix matches targets (test0 ln=10.10996, test2 ln=8.31777). log2 o… |
| 76.4 | D9 跨步依赖 | ⚪ | 裁判·测试用例 | Test index 4 defines data2 and generates from data2 but scans with load_motif_from_df(data); test index 5 defines data3, generates from data3, scans w… |

### 🟡 题 77 (test) — 11 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 77.3 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Docstring gives no direction and Returns line is the copy-pasted 'float: minimum image distance'; h5 targets ([0.5,0.5,0.5], [-2,-2,-2]) are exactly m… |
| 77.5 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | Docstring wrongly types r as 'float: distance' and never states displacement direction; h5 test-2 target is a positive multiple of r (attraction towar… |
| 77.6 | D10 文档矛盾 | 🟡 | 理论推导(background) | Background formula quoted accurately ('per particle' yet N^2, no 1/V); test-1 printed value = -64pi/9 = -22.3402 vs h5 target -0.0223402 = printed/L^3… |
| 77.7 | D10 文档矛盾 | 🟡 | 理论推导(background) | Printed p_tail lacks 1/V^2 (dimensionally an energy); h5 target -2.23402e-4 = printed/L^6 x10 (zJ/nm^3->bar), matching the reviewer's arithmetic exact… |
| 77.9 | D4 约定不明 | 🟡 | 裁判·测试用例 | Test 0 passes v=np.array([1,2,3]) (shape (3,)) against a docstring promising (N,3); any axis=1 per-particle implementation raises AxisError and fails … |
| 77.10 | D7 target错误 | 🟡 | 裁判·target值 | h5 test-3 virial = -8.8505 bar while pair 0-3 sits at r=0.712 < 2^(1/6) (repulsive => physical virial positive); the background's i->j/force-on-i pair… |
| 77.11 | D4 约定不明 | 🟡 | 裁判·测试用例 | Test 1 N=2 vs 3-row xyz; h5 target is shape (2,3) holding only the antisymmetric 0-1 pair, so a contract-faithful vectorized (3,3) return crashes np.a… |
| 77.12 | D2 信息缺失/无法做出 | 🟡 | 题面(description) | gamma appears only symbolically in the background and as gamma=4.6E-5 inside hidden test code, not as a parameter or stated value; reviewer logs show … |
| 77.12 | D8 测试过弱 | 🟡 | 裁判·测试用例 | out_nobarostat.log shows a barostat-less implementation PASSES the only test (30% pressure band), so the step never verifies barostat functionality wh… |
| 77.10 | D4 约定不明 | ⚪ | 裁判·测试用例 | Test 1 sets N=2 with a 3-row positions array; h5 kinetic target 2.7613e-4 bar = 2*kB*T/V (uses N=2), so deriving the count from xyz.shape[0] fails; mi… |
| 77.12 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Header literally reads 'units: bar.ostat. Set to 0 to deactivate, units: picoseconds.' — corrupted duplication of the tau_P line; minor is correct. |

### 🔴 题 78 (dev) — 5 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 78.3 | D5 非确定性 | 🔴 | 题面(description) | Ran `python3 review/tools/steptest.py --problem 78 --step 78.3 --use-gold` twice: deterministic FAIL both times with 'ValueError: operands could not b… |
| 78.1 | D10 文档矛盾 | 🟡 | 理论推导(background) | Quoted from sub_steps[0].step_background (verbatim): torque '\\tau = -mgL \\sin(\\theta) - \\beta L \\frac{d\\theta}{dt} + A \\cos(\\alpha t)' divided… |
| 78.2 | D8 测试过弱 | 🟡 | 裁判·测试用例 | Wrote my own deliberately wrong probes and ran official joint scoring. (1) Forward Euler (1st order) in place of RK4: review/work/78/verify/euler_wron… |
| 78.3 | D4 约定不明 | ⚪ | 函数契约(docstring/header) | Static check against the JSON: sub_steps[2] prompt and docstring nowhere state how n is derived from (t0, tf, dt) -- docstring output is just 'optimiz… |
| 78.2 | D4 约定不明 | ⚪ | 题面(description) | [复核新增] Tests 1 and 2 read `state` (and `state[0]`) AFTER calling the integrator: test 2 asserts 'final_state[0] < state[0]' and test 1 computes 'ex |

### 🔴 题 79 (test) — 7 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 79.2 | D7 target错误 | 🔴 | 理论推导(background) | Wrote my OWN spec-literal nhc_step (review/work/79/verify/my_spec.py) following the background pseudocode exactly (first sweep recomputes G_k fresh, M… |
| 79.3 | D7 target错误 | 🔴 | 函数契约(docstring/header) | my_spec.py (spec-literal nhc_step inside nhc_Y4): steptest 79.3 official joint = FAIL, per-test 1/1,1/1,0/1. my_stale.py (stale-G + G threaded through… |
| 79.4 | D6 容差脆弱 | 🔴 | 裁判·测试用例 | My own implementation (my_stale.py), verified bit-exact on every component of all nine 79.1-79.3 targets (one element 1.73e-18 off), passes 79.4 test … |
| 79.4 | D7 target错误 | 🟡 | 函数契约(docstring/header) | h5 targets loaded: x/v shapes are (20000,), (20000,), (40000,) -- flat 1-D. Both problem_io and the 79.4 docstring state 'x : array of shape (nsteps, … |
| 79.4 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | h5 79.4 targets: x[0]=0.0=x0 exactly and v[0]=0.8944271909999159=np.sqrt(2*0.1)*2 exactly for all 3 tests -- the target encodes record-then-step (init… |
| 79.1 | D8 测试过弱 | 🟡 | 裁判·测试用例 | Static: all three test cases set x0 = 0.0 (quoted from test_cases; they differ only in v0 and dt), so F(t) = -m*omega^2*x0 = 0 and the position update… |
| 79.2 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Static check against review/problems/79.json: the nhc_step docstring (and verbatim copy in nhc_Y4) declares 'G : float / The initial force of the harm… |

### 🔴 题 80 (test) — 11 缺陷

| 步 | 类型 | 级别 | 受影响字段 | 问题 |
|--|--|--|--|--|
| 80.3 | D7 target错误 | 🔴 | 理论推导(background) | Ran my own all-pairs min-image truncated-shifted LJ E_pot (review/work/80/verify/v_correct.py): steptest 80.3 FAIL (official joint). My chain reconstr… |
| 80.5 | D7 target错误 | 🔴 | 裁判·target值 | h5 targets inspected directly: every nonzero row has identical x=y=z components (test1 row0 = [6.6107e-4]*3; all test2 rows isotropic) -- impossible f… |
| 80.6 | D7 target错误 | 🔴 | 裁判·target值 | Textbook velocity Verlet on top of correct all-pairs vector forces (v_correct.py): steptest 80.6 FAIL on all tests. Identical Verlet code on top of th… |
| 80.4 | D4 约定不明 | 🟡 | 函数契约(docstring/header) | My f_ij with the standard reading r = r_i - r_j, F_i = -dV/dr*rhat (v_correct.py): steptest 80.4 FAIL. Same code with the opposite sign +dV/dr*rhat (v… |
| 80.5 | D4 约定不明 | 🟡 | 裁判·测试用例 | Test 1 verbatim: 'N = 2 ... positions = np.array([[...],[...],[...]])' -- three rows; h5 target shape (2,3) verified by direct load. My implementation… |
| 80.7 | D4 约定不明 | 🟡 | 裁判·测试用例 | initialize_fcc(200) builds ceil(200^(1/3))^3 = 6^3 = 216 positions (verified). Ran two identical correct vectorized Anderson-NVT implementations throu… |
| 80.7 | D8 测试过弱 | 🟡 | 裁判·测试用例 | Wrote my own no-simulation stub (v_stub7.py: instant_T_array=np.full(num_steps,T), intercollision_times=np.full(1000,1/nu), zeros/echoed inputs otherw… |
| 80.7 | D10 文档矛盾 | 🟡 | 函数契约(docstring/header) | Static, quoted verbatim from sub_steps[6].function_header: 'Integrate the equations of motion using the velocity Verlet algorithm, with the inclusion … |
| 80.7 | D5 非确定性 | ⚪ | 裁判·测试用例 | Static: grep over all three 80.7 test_cases finds no 'seed' (verified programmatically); the Anderson thermostat necessarily consumes unseeded np.rand… |
| 80.7 | D6 容差脆弱 | ⚪ | 裁判·测试用例 | Measured myself on this machine: one naive loop-based forces() call on the 216-particle fcc config = 0.123 s; one loop-based E_pot() = 0.094 s. A stra… |
| 80.2 | D10 文档矛盾 | ⚪ | 函数契约(docstring/header) | Static, quoted verbatim: 80.2 docstring 'Calculate the combined truncated and shifted Lennard-Jones potential energy and, if specified, the truncated … |

