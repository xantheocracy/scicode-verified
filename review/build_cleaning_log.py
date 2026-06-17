#!/usr/bin/env python3
"""Assemble review/cleaning_log.json: a 2-round, per-change cleaning log with REASONS
and a NATURE tag, so fix_viewer.py can annotate every diff with "why" + "what kind".

Sources merged:
  - round-1 field-level reasons: tmp_log/r1_batchA.json + r1_batchC.json (subagent partial,
    format {pid:{summary, changes:[{step,field,reason,source}]}}); for the 23-49 gap we
    fall back to the first heading/line of legacy/cleaning/log/<id>.md as a problem summary.
  - round-2 (problems 5-38, prior session): clean_2round/audit/prompt_trap_audit.json findings.
  - round-2 (problems 39-80, this session): the ROUND2 dict below (field-level + nature).

NATURE tags (what kind of change, for the human leakage/over-spec audit):
  convention  - necessary convention / disambiguation (domain-required; not a leak)
  contract    - output contract (shape/type/meaning) -> ideally belongs in docstring
  terminology - fixes a wrong label/name; no new info
  consistency - internal self-consistency (text vs text, docstring vs return, etc.)
  target      - regenerated a frozen target (h5) to match the spec
  testfix     - test_cases fixed to be type/convention-consistent (target-preserving)
  tolerance   - loosened a test tolerance to kill a method/rounding lottery
  knob        - numerical knob pinned for bit-exact reproducibility -> OVER-SPECIFICATION risk
  explain     - explanatory/justification clause ("..., so X") -> reasoning, trim candidate
  leak        - possible answer/insight leakage -> review
  nochange    - decided NOT to change (recorded for completeness)
"""
import json, re, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJ = ROOT.parent
TMP = PROJ / "tmp_log"
OUT = ROOT / "cleaning_log.json"

def jload(p):
    try: return json.load(open(p))
    except Exception: return {}

# ---------- round-1 from batch partials ----------
r1 = {}
for fn in ("r1_batchA.json", "r1_batchB.json", "r1_batchC.json"):
    d = jload(TMP / fn)
    for pid, rec in d.items():
        r1.setdefault(str(pid), {"summary": "", "changes": []})
        if rec.get("summary") and not r1[str(pid)]["summary"]:
            r1[str(pid)]["summary"] = rec["summary"]
        for ch in rec.get("changes", []):
            r1[str(pid)]["changes"].append(ch)

# round-1 gap (23-49 etc.): fall back to legacy/cleaning/log/<id>.md first meaningful line
LOGDIR = PROJ / "legacy" / "cleaning" / "log"
def legacy_summary(pid):
    p = LOGDIR / f"{pid}.md"
    if not p.exists(): return ""
    for line in open(p):
        s = line.strip().lstrip("#").strip()
        if s and not s.startswith("Split") and len(s) > 12:
            return s[:300]
    return ""

# ---------- round-2 problems 5-38: from the audit findings ----------
audit = jload(PROJ / "clean_2round" / "audit" / "prompt_trap_audit.json")
audit_by = {}
for r in (audit.get("results") or []):
    audit_by[str(r.get("pid"))] = r

def r2_from_audit(pid):
    r = audit_by.get(pid)
    if not r: return "", []
    summ = (r.get("summary") or "")[:300]
    changes = []
    for f in r.get("findings", []):
        changes.append({
            "round": "R2", "step": f.get("step", ""), "field": "",
            "reason": f"[{f.get('severity','')}·{f.get('type','')}] {f.get('description','')[:220]}"
                      + (f"  → fix: {f.get('recommended_fix','')[:140]}" if f.get('recommended_fix') else ""),
            "nature": "review", "source": "clean_2round/audit/prompt_trap_audit.json"})
    return summ, changes

# ---------- round-2 problems 39-80: this-session decisions (field-level + nature) ----------
# each entry: pid -> {"summary":..., "changes":[(step, field, nature, reason), ...]}
ROUND2 = {
 "41": {"summary":"41.3 措辞自洽:行列式是对归一化矩阵 M'=M/(D-1) 而非原始 M。",
   "changes":[("41.3","step_description_prompt","consistency",
     "prompt 写 'determinant of M',但所求是归一化矩阵 M'=M/(D-1) 的行列式(背景已定义 M')。改成 'determinant of the normalized conversion matrix' 以与背景自洽。零泄露。")]},
 "42": {"summary":"42.2 术语修正:g_w 是单阱峰值增益,不是 modal gain。",
   "changes":[("42.2","step_description_prompt","terminology",
     "g_w 被误称 'modal gain';物理上 modal gain = n_w·Γ_w·g_w,g_w 是单阱峰值增益。改 'single-well peak gain coefficient (g_w)',与 42.1 一致。")]},
 "43": {"summary":"43.2 背景补 SUPG 对 A、b 的贡献;43.3 prompt 补饱和功率公式;gamma 术语改 overlap factor。",
   "changes":[("43.2","step_background","convention",
     "背景把 A、b 写成仅 Galerkin 项,与 prompt 'use SUPG' + 主弱形式矛盾;补 SUPG 对 A(∫τa ω_,x a u_,x)和 b(∫τa ω_,x·12x²)的贡献。"),
    ("43.3","step_description_prompt","knob",
     "饱和功率公式 Pssat/Ppsat(gamma 在分母,决定性)只藏在隐藏 test 里;不给就是积分器/约定彩票。补进 prompt。属必要约定但接近过度规定。"),
    ("43.1","function_header","terminology","gamma_p/gamma_s docstring 'Gain coefficient' → 'Overlap (filling) factor'(与 prompt/背景一致)。"),
    ("43.3","function_header","terminology","同上 gamma 术语修正。")]},
 "45": {"summary":"45.2/45.3 test0 把 Python list 改成 np.array,与 docstring '2d array' 一致。",
   "changes":[("45.2","test_cases","testfix","test0 [[1,0,20]] → np.array([[1,0,20]]);docstring 说 '2d array'、模型用 .size,list 会崩。target 不变。"),
    ("45.3","test_cases","testfix","同 45.2。")]},
 "48": {"summary":"48.4 test3 把返回值包成 np.array(布尔索引需 ndarray)。",
   "changes":[("48.4","test_cases","testfix","docstring 说 'list of float' 但 test 对返回值布尔索引(需 ndarray);test3 包 np.array(chi_cal(...))。target 不变。")]},
 "50": {"summary":"50.3/50.4 ddof 统一为总体(ddof=0);消除 50.3 文字(样本std)与 50.4 target 的矛盾。",
   "changes":[("50.3","step_background","convention","'sample standard deviation' → 'population standard deviation (ddof=0)';物理上分布宽度=⟨q²⟩−⟨q⟩²(ddof=0)。"),
    ("50.4","step_description_prompt","convention","'standard deviation' → 'the population standard deviation (np.std default ddof=0)',与 target 一致。")]},
 "52": {"summary":"52.4 tests0/1 放宽到 atol=1e-5,消除积分器彩票。",
   "changes":[("52.4","test_cases","tolerance","target 绑定 odeint 的数值本征值;合法替代(solve_ivp)差 ~4e-7。加 atol=1e-5(态间距~0.007≫1e-5,判别力保留)。")]},
 "53": {"summary":"53.4 周期比较放宽到 <0.11,消除 FFT 方法/舍入彩票。",
   "changes":[("53.4","test_cases","tolerance","周期在 1 位小数下方法依赖、压在舍入边界;'period==e' → 'abs(period-e)<0.11'(容一个桶、拒≥0.2)。")]},
 "54": {"summary":"54.2 背景补 SUPG 到 A、b;54.4 填补空占位符。",
   "changes":[("54.2","step_background","convention","背景仅 Galerkin,与 'use SUPG' 矛盾;补 SUPG 对 A、b 的贡献。"),
    ("54.4","step_description_prompt","consistency","空占位符 'using , and functions' → 'using the basis, assemble, and stabilization functions'。")]},
 "55": {"summary":"55.3 docstring 命名统一;55.4 错位子句移到正确参数。",
   "changes":[("55.3","function_header","consistency","docstring 输出名 peak_near_q0_location → peak_location_near_q0(与 return_line 一致)。"),
    ("55.4","function_header","consistency","'; set to 0 if no stripe is formed' 从 min_height(输入)移到 stripe_mode(输出)。")]},
 "67": {"summary":"67.5 符号修正 ℏ/m_e → ℏ²/m_e。",
   "changes":[("67.5","step_description_prompt","terminology","常数 76.1996 meV·nm² 实为 ℏ²/mₑ;符号 '\\hbar/m_e' → '\\hbar^2/m_e'(值/单位不变)。")]},
 "71": {"summary":"71.8 澄清 reverse coherent info 的参考系 A/B。",
   "changes":[("71.8","step_description_prompt","convention","补一句:A 是参考子系统(未过信道的 qubit)、B 是信道输出,故 S(A) 取未过信道 qubit 的边际熵。消除 A/B 二义。")]},
 "72": {"summary":"72.1 docstring 邻居顺序对齐 prompt/test。",
   "changes":[("72.1","function_header","consistency","邻居顺序 docstring [left,above,right,below] → [above,right,below,left],对齐 prompt/test/target 的 (i-1,j),(i,j+1),(i+1,j),(i,j-1)。")]},
 "73": {"summary":"73.2 det_d 定义澄清;73.3/5/8/9 z_s 旋转轴 φ→θ。",
   "changes":[("73.2","function_header","convention","det_d 'sample distance to the detector' 二义(沿光束 vs 垂直倾斜面);改 'sample-to-beam-center distance measured along the incident beam (+x)'。"),
    ("73.3","function_header","consistency","z_s 'step size in the φ rotation' → 'θ rotation'(prompt 扫 θ)。"),
    ("73.5","function_header","consistency","同上 z_s。"),("73.8","function_header","consistency","同上 z_s。"),("73.9","function_header","consistency","同上 z_s。")]},
 "79": {"summary":"79.3 dt 约定澄清(传完整 dt,nhc_Y4 内部出 dt/2)。",
   "changes":[("79.3","function_header","convention","dt docstring 澄清:'the full integration time step; nhc_Y4 internally evolves over dt/2 via Yoshida weights, so pass the full dt (not dt/2)'。背景 LaTeX 暗示 dt/2 致二义。")]},
 "76": {"summary":"76.2 target 重生成为 L1 概率 KL(option a)。",
   "changes":[("76.2","target","target","'KL between probability distributions' 框定要求行 L1 归一化为概率;旧 L2-直接和与框定矛盾。target 重生成为真 KL。76.1 文本与 76.4 不动。")]},
 # round-2 no-change decisions (recorded for completeness)
 "40": {"summary":"不改:主方程项序与 40.2 显式赋值,可恢复;两模型都过。","changes":[("","","nochange","SUPG split 算子分配在 40.2 已显式,主方程项序仅轻微,可恢复。")]},
 "46": {"summary":"不改:动能 -½∇²ψ/ψ 可从 46.2 哈密顿量恢复(且不加公式 hint)。","changes":[("46.1","","nochange","动能约定可从 46.2 哈密顿量恢复;按用户偏好不加公式 hint。")]},
 "56": {"summary":"不改:allowed_orders 规则可从主描述 sequential-consumption 动力学恢复;R=4 例子合法。","changes":[("","","nochange","规则可恢复;两模型都过;docstring R 通用,R=4 例子非缺陷。")]},
 "58": {"summary":"不改:flash 挂 58.4 是 r=0 除零(模型错);prompt 已提示中心极值。","changes":[("","","nochange","模型错(未处理 r=0);数据正确。")]},
 "59": {"summary":"不改:59.2 相位矛盾 round-1 已修(相位无关 test);59.3 量子比特序可恢复。","changes":[("","","nochange","均已修/可恢复。")]},
 "60": {"summary":"仅对齐 60.5 problem_io 参数表到 header(positions/L→N/rho);k_B 可恢复;失败是 stale。","changes":[("60.5","problem_io","consistency","problem_io 参数表 positions/L → N/rho,对齐 header 签名。")]},
 "62": {"summary":"不改:v0 等可恢复(规范不变量),两模型都过。","changes":[("","","nochange","可恢复。")]},
 "63": {"summary":"不改:参数名反转/降序网格已在 docstring 钉死且可恢复;改签名/重生成2D target 风险大。","changes":[("","","nochange","可恢复且修复有风险。")]},
 "64": {"summary":"不改:round-1 已显式写 k_B=1、移除 SI 氩常数;失败是模型硬编码 SI(模型错)。","changes":[("","","nochange","已修;模型错。")]},
 "68": {"summary":"不改:68.1 动能可恢复;68.8 那句是分支概念描述,与配方不冲突。","changes":[("","","nochange","可恢复/无害。")]},
 "69": {"summary":"不改:69.2 D_2DEG 是模型错(同 67.2,退化数值积分);V_q/eps0 可恢复。","changes":[("","","nochange","模型错/可恢复。")]},
 "75": {"summary":"不改:75.3 失败是模型硬编码 a0=2.68(应算 a/√3);prompt 正确。","changes":[("","","nochange","模型错。")]},
}

# ---------- assemble ----------
legacy_ids = [p.stem for p in LOGDIR.glob("*.md")] if LOGDIR.exists() else []
allids = sorted({*r1, *audit_by, *ROUND2, *legacy_ids},
                key=lambda x: int(x) if str(x).isdigit() else 1 << 30)
log = {}
for pid in allids:
    pid = str(pid)
    entry = {"r1_summary": "", "r2_summary": "", "changes": []}
    # round-1
    if pid in r1:
        entry["r1_summary"] = r1[pid]["summary"]
        for ch in r1[pid]["changes"]:
            entry["changes"].append({"round":"R1","step":ch.get("step",""),"field":ch.get("field",""),
                                     "reason":ch.get("reason",""),"nature":ch.get("nature","") or "convention",
                                     "source":ch.get("source","")})
    elif legacy_summary(pid):
        entry["r1_summary"] = legacy_summary(pid)
        entry["changes"].append({"round":"R1","step":"","field":"","reason":entry["r1_summary"],
                                 "nature":"convention","source":f"legacy/cleaning/log/{pid}.md"})
    # round-2
    if pid in ROUND2:
        entry["r2_summary"] = ROUND2[pid]["summary"]
        for st, fld, nat, why in ROUND2[pid]["changes"]:
            entry["changes"].append({"round":"R2","step":st,"field":fld,"reason":why,"nature":nat,"source":"session"})
    else:
        s2, ch2 = r2_from_audit(pid)
        if s2: entry["r2_summary"] = s2
        entry["changes"].extend(ch2)
    if entry["r1_summary"] or entry["r2_summary"] or entry["changes"]:
        log[pid] = entry

json.dump(log, open(OUT, "w"), ensure_ascii=False, indent=1)
print(f"wrote {OUT} with {len(log)} problems")
print("  R1 summaries:", sum(1 for v in log.values() if v["r1_summary"]))
print("  R2 summaries:", sum(1 for v in log.values() if v["r2_summary"]))
print("  total change entries:", sum(len(v["changes"]) for v in log.values()))
