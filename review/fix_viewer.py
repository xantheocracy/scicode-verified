#!/usr/bin/env python3
"""Zero-dependency viewer for the SciCode cleaning DIFF (original → cleaned).

Usage:  python3 review/fix_viewer.py          # then open http://localhost:8000
        python3 review/fix_viewer.py 8077      # custom port

Stdlib only (json/difflib/http.server/html/re/pathlib) + numpy/scicode for h5
target loading. Shows EXACTLY what the cleaning changed, one problem at a time:
 - per sub_step / per field BEFORE → AFTER text diffs (inline <del>/<ins>),
 - LaTeX rendered via MathJax (CDN; degrades to raw text offline) for prose
   fields only; code/test/docstring fields stay monospace (nomath),
 - per-step h5 target old→new previews with the human "note" from the patch JSON.
Only problems that actually changed are listed; unchanged ones are greyed.
"""
import json, sys, re, html, difflib
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = Path(__file__).resolve().parent
_PROJ = ROOT.parent
sys.path.insert(0, str(_PROJ / "SciCode" / "src"))

_ORIG_JSONL = _PROJ / "eval_clean" / "data_original" / "problems_test.jsonl"
_CLEAN_JSONL = _PROJ / "scicode_verified" / "problems_test.jsonl"
_ORIG_H5 = _PROJ / "SciCode" / "eval" / "data" / "test_data.h5"
_CLEAN_H5 = _PROJ / "scicode_verified" / "test_data_cleaned.h5"
_PATCH_DIRS = [_PROJ / "scicode_verified" / "targets"]

try:
    from scicode.parse.parse import process_hdf5_to_tuple as _h5tuple
except Exception:
    _h5tuple = None

_SKIP = {"13.6", "62.1", "76.3"}
# prose fields get MathJax; everything else is rendered monospace / nomath.
_PROSE_FIELDS = {"step_description_prompt", "step_background"}
_FIELD_LABEL = {
    "step_description_prompt": "子步题面 (step_description_prompt)",
    "step_background": "理论推导 (step_background)",
    "function_header": "函数契约 (function_header)",
    "return_line": "返回行 (return_line)",
    "test_cases": "测试用例 (test_cases)",
    "problem_io": "题目 I/O (problem_io · 顶层)",
}
_STEP_FIELDS = ["step_description_prompt", "step_background", "function_header",
                "return_line", "test_cases"]


# ---------- target preview helpers (borrowed from review/viewer.py) ----------
def _fmt_num(x):
    try:
        import numpy as np
        if isinstance(x, (complex, np.complexfloating)):
            return f"{x.real:.4g}{'+' if x.imag >= 0 else '-'}{abs(x.imag):.4g}j"
        if isinstance(x, (float, np.floating)):
            return f"{x:.4g}"
    except Exception:
        pass
    return str(x)


def _preview(o, depth=0):
    """Compact one-line preview of a target object (shape/type + a few values)."""
    try:
        import numpy as np
    except Exception:
        np = None
    if np is not None and isinstance(o, np.ndarray):
        flat = o.flatten()
        head = ", ".join(_fmt_num(v) for v in flat[:8])
        return f"ndarray{tuple(o.shape)} {o.dtype} = [{head}{' …' if flat.size > 8 else ''}]"
    if isinstance(o, bool):
        return str(o)
    if np is not None and isinstance(o, (np.bool_,)):
        return str(bool(o))
    if isinstance(o, (int, float, complex)) or (np is not None and isinstance(o, np.number)):
        return _fmt_num(o)
    if isinstance(o, str):
        return repr(o[:80] + ("…" if len(o) > 80 else ""))
    if isinstance(o, (tuple, list)):
        if depth == 0:
            return "(" + "  |  ".join(_preview(x, depth + 1) for x in o) + ")"
        return f"[{len(o)} 项]"
    if isinstance(o, dict):
        return "{" + ", ".join(f"{k}:…" for k in list(o)[:4]) + ("…}" if len(o) > 4 else "}")
    s = str(o)
    return s[:80] + ("…" if len(s) > 80 else "")


# ----------------------------- data loading -----------------------------
def _load_jsonl(p):
    out = {}
    if not p.exists():
        return out
    with open(p) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            out[str(d.get("problem_id"))] = d
    return out


_ORIG = _load_jsonl(_ORIG_JSONL)
_CLEAN = _load_jsonl(_CLEAN_JSONL)


def _load_patches():
    """Merge patch jsons; later dirs do NOT override earlier (round-2 wins).

    Returns {pid: {"note": str, steps: {step: note_or_''}}}.
    """
    out = {}
    for d in _PATCH_DIRS:
        if not d.exists():
            continue
        for fp in sorted(d.glob("*.json")):
            try:
                data = json.load(open(fp))
            except Exception:
                continue
            pid = str(data.get("problem_id") or fp.stem)
            entry = out.setdefault(pid, {"note": "", "steps": {}})
            if not entry["note"] and isinstance(data.get("note"), str):
                entry["note"] = data["note"]
            for k, v in data.items():
                if k in ("problem_id", "note"):
                    continue
                if isinstance(v, dict):
                    # per-step entry; may itself carry a "note"
                    if k not in entry["steps"]:
                        sn = v.get("note") if isinstance(v.get("note"), str) else ""
                        entry["steps"][k] = sn
    return out


_PATCHES = _load_patches()

# ---------- cleaning log (per-change reasons + nature tags, both rounds) ----------
_LOG_PATH = ROOT / "cleaning_log.json"
try:
    _LOG = json.load(open(_LOG_PATH))
except Exception:
    _LOG = {}

_NATURE_LABEL = {
    "convention": "必要约定/去歧义", "contract": "输出契约(宜入docstring)",
    "terminology": "术语/命名修正", "consistency": "内部自洽",
    "target": "重生成 target", "testfix": "test 类型/约定修正(保 target)",
    "tolerance": "放宽容差(消方法彩票)", "knob": "数值旋钮(过度规定风险)",
    "explain": "解释/推理句(可删)", "leak": "可能泄露(需审)",
    "review": "待人工核定", "nochange": "决定不改",
}


def _reasons_for(pid, step, field):
    """Return list of {round,nature,reason} from the cleaning log matching this (step,field).

    A log change matches if its step equals `step` (or is '' = problem-level) AND its
    field equals `field` (or is '' = problem-level). problem_io diffs use step '(顶层)'.
    """
    e = _LOG.get(str(pid))
    if not e:
        return []
    out = []
    for ch in e.get("changes", []):
        cs, cf = ch.get("step", ""), ch.get("field", "")
        step_ok = (cs == step) or (cs == "") or (step == "(顶层)" and cs in ("", "problem_io"))
        field_ok = (cf == field) or (cf == "")
        # for problem_io the log may store field 'problem_io'
        if field == "problem_io" and cf == "problem_io":
            field_ok = True
        if step_ok and field_ok:
            out.append(ch)
    # prefer the most specific (both step & field non-empty) first
    out.sort(key=lambda c: (c.get("step", "") == "", c.get("field", "") == ""))
    return out


_TGT_CACHE = {}


def _targets(h5path, step_number, n_tests):
    """Return list of raw target objects (or None on failure)."""
    key = (str(h5path), step_number, n_tests)
    if key in _TGT_CACHE:
        return _TGT_CACHE[key]
    if step_number in _SKIP or _h5tuple is None or not Path(h5path).exists():
        _TGT_CACHE[key] = None
        return None
    try:
        tg = list(_h5tuple(step_number, n_tests, str(h5path)))
    except Exception:
        tg = None
    _TGT_CACHE[key] = tg
    return tg


def _targets_equal(a, b):
    try:
        import numpy as np
    except Exception:
        np = None

    def eq(x, y):
        if np is not None and (isinstance(x, np.ndarray) or isinstance(y, np.ndarray)):
            ax, ay = np.asarray(x), np.asarray(y)
            if ax.shape != ay.shape:
                return False
            try:
                return bool(np.allclose(ax, ay, rtol=1e-9, atol=0, equal_nan=True))
            except Exception:
                return bool(np.array_equal(ax, ay))
        if isinstance(x, (tuple, list)) and isinstance(y, (tuple, list)):
            return len(x) == len(y) and all(eq(p, q) for p, q in zip(x, y))
        # scipy sparse matrices: compare densely (avoids SparseEfficiencyWarning)
        if hasattr(x, "toarray") and hasattr(y, "toarray"):
            try:
                ax, ay = x.toarray(), y.toarray()
                return ax.shape == ay.shape and bool(np.allclose(ax, ay, rtol=1e-9, atol=0))
            except Exception:
                return False
        try:
            if np is not None and isinstance(x, (float, np.floating, complex, np.complexfloating)):
                return bool(np.isclose(x, y, rtol=1e-9, atol=0, equal_nan=True))
        except Exception:
            pass
        try:
            r = (x == y)
        except Exception:
            return False
        if np is not None and isinstance(r, np.ndarray):
            return bool(r.all())
        return bool(r)

    return eq(a, b)


# ----------------------------- diff computation -----------------------------
def _norm(v):
    """Normalize a field value to a string for textual diffing."""
    if v is None:
        return ""
    if isinstance(v, list):
        # test_cases is a list of strings; join with a clear separator
        return "\n# ---- next test ----\n".join(str(x) for x in v)
    return str(v)


def diff_problem(pid):
    """Compute the full change record for one problem id (str).

    Returns dict with: changed (bool), name, fields (list of text-field diffs),
    target_changes (list per step), patch_note, tags (set of change types).
    """
    o = _ORIG.get(pid)
    c = _CLEAN.get(pid)
    rec = {"id": pid, "name": (c or o or {}).get("problem_name", "?"),
           "changed": False, "fields": [], "target_changes": [],
           "patch_note": "", "tags": []}
    if o is None or c is None:
        # present on only one side -> treat as fully changed/skip
        rec["only_side"] = "cleaned only" if o is None else "original only"
        return rec

    patch = _PATCHES.get(pid, {})
    rec["patch_note"] = patch.get("note", "")
    tags = set()

    # ---- top-level problem_io ----
    if _norm(o.get("problem_io")) != _norm(c.get("problem_io")):
        rec["fields"].append({"step": "(顶层)", "field": "problem_io",
                              "label": _FIELD_LABEL["problem_io"], "prose": False,
                              "before": _norm(o.get("problem_io")),
                              "after": _norm(c.get("problem_io"))})
        tags.add("io")

    # ---- per sub_step text fields ----
    o_steps = {s.get("step_number"): s for s in (o.get("sub_steps") or [])}
    c_steps = {s.get("step_number"): s for s in (c.get("sub_steps") or [])}
    all_steps = sorted(set(o_steps) | set(c_steps),
                       key=lambda s: [int(x) for x in str(s).split(".") if x.isdigit()] or [0])

    for sn in all_steps:
        os_, cs_ = o_steps.get(sn, {}), c_steps.get(sn, {})
        for fld in _STEP_FIELDS:
            ov, cv = _norm(os_.get(fld)), _norm(cs_.get(fld))
            if ov != cv:
                rec["fields"].append({"step": sn, "field": fld,
                                      "label": _FIELD_LABEL[fld],
                                      "prose": fld in _PROSE_FIELDS,
                                      "before": ov, "after": cv})
                if fld == "step_description_prompt":
                    tags.add("prompt")
                elif fld == "step_background":
                    tags.add("background")
                elif fld == "function_header":
                    tags.add("header")
                elif fld == "return_line":
                    tags.add("return")
                elif fld == "test_cases":
                    tags.add("test")

    # ---- per-step h5 target diffs ----
    for sn in all_steps:
        cs_ = c_steps.get(sn) or o_steps.get(sn) or {}
        tcs = cs_.get("test_cases") or []
        n = len(tcs)
        if not n or sn in _SKIP:
            continue
        ot = _targets(_ORIG_H5, sn, n)
        ct = _targets(_CLEAN_H5, sn, n)
        if ot is None or ct is None:
            continue
        changed_tests = []
        for j in range(min(len(ot), len(ct))):
            if not _targets_equal(ot[j], ct[j]):
                changed_tests.append({"i": j,
                                      "before": _preview(ot[j]),
                                      "after": _preview(ct[j])})
        if len(ot) != len(ct):
            changed_tests.append({"i": "len", "before": f"{len(ot)} 个测试",
                                  "after": f"{len(ct)} 个测试"})
        if changed_tests:
            step_note = (patch.get("steps", {}) or {}).get(sn, "")
            rec["target_changes"].append({"step": sn, "tests": changed_tests,
                                          "note": step_note})
            tags.add("target")

    rec["changed"] = bool(rec["fields"] or rec["target_changes"])
    rec["tags"] = sorted(tags)
    return rec


_DIFF_CACHE = {}


def get_diff(pid):
    pid = str(pid)
    if pid not in _DIFF_CACHE:
        _DIFF_CACHE[pid] = diff_problem(pid)
    return _DIFF_CACHE[pid]


def build_index():
    """All problems with change metadata; computed once."""
    ids = sorted(set(_ORIG) | set(_CLEAN),
                 key=lambda x: int(x) if str(x).isdigit() else 1 << 30)
    out = []
    for pid in ids:
        d = get_diff(pid)
        text_only = bool(d["fields"]) and not d["target_changes"]
        out.append({"id": pid, "name": d["name"], "changed": d["changed"],
                    "tags": d["tags"], "n_fields": len(d["fields"]),
                    "n_targets": len(d["target_changes"]),
                    "text_only": text_only,
                    "target_changed": bool(d["target_changes"])})
    return out


# ----------------------------- HTML rendering -----------------------------
def _inline_diff_html(before, after):
    """Word/char-level inline diff -> escaped HTML with <del>/<ins> spans."""
    # split into tokens preserving whitespace & newlines so structure is visible
    tok = re.compile(r"\s+|\w+|[^\s\w]")
    a = tok.findall(before)
    b = tok.findall(after)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        seg_a = html.escape("".join(a[i1:i2]))
        seg_b = html.escape("".join(b[j1:j2]))
        if op == "equal":
            out.append(seg_a)
        elif op == "delete":
            out.append(f"<del>{seg_a}</del>")
        elif op == "insert":
            out.append(f"<ins>{seg_b}</ins>")
        elif op == "replace":
            out.append(f"<del>{seg_a}</del><ins>{seg_b}</ins>")
    return "".join(out)


def _reasons_html(pid, step, field):
    """HTML block of matching cleaning-log reasons for a (step, field) change."""
    rs = _reasons_for(pid, step, field)
    if not rs:
        return ('<div class="reason none nomath">⚠ 此处暂无登记理由'
                '（人工审核时补充到 review/cleaning_log.json）</div>')
    out = ['<div class="reasonwrap">']
    for ch in rs:
        rnd = html.escape(ch.get("round", ""))
        nat = ch.get("nature", "")
        natlbl = _NATURE_LABEL.get(nat, nat)
        scope = ""
        if not ch.get("field") and not ch.get("step"):
            scope = " <span class=scope>(整题)</span>"
        elif not ch.get("field"):
            scope = " <span class=scope>(整步)</span>"
        out.append(
            f'<div class="reason nomath">'
            f'<span class="rbadge r-{rnd}">{rnd}</span>'
            f'<span class="nat n-{html.escape(nat)}">{html.escape(natlbl)}</span>{scope} '
            f'{html.escape(ch.get("reason", ""))}</div>')
    out.append('</div>')
    return "".join(out)


_PROB_CTX_FIELDS = [
    ("problem_description_main", "题面 (problem_description_main · 顶层)", True),
    ("problem_background_main", "背景 (problem_background_main · 顶层)", True),
    ("problem_io", "题目 I/O (problem_io · 顶层)", False),
    ("required_dependencies", "依赖 (required_dependencies · 顶层)", False),
]


def _ctx_box(label, val, prose, changed):
    """One field rendered in full (cleaned value); prose -> MathJax, code -> mono."""
    if isinstance(val, list):
        val = "\n# ---- next test ----\n".join(str(x) for x in val)
    if val is None:
        val = ""
    cls = "ctxbody prose" if prose else "ctxbody nomath code"
    badge = ' <span class="cbadge">已变更</span>' if changed else ''
    chcls = " ctxchanged" if changed else ""
    return (f'<div class="ctxfld{chcls}">'
            f'<div class="lbl nomath">{html.escape(label)}{badge}</div>'
            f'<div class="{cls}">{html.escape(val)}</div></div>')


def _full_context_html(pid, o, c):
    """Render the ENTIRE cleaned problem (every field, changed or not) for context."""
    if not c:
        return ""
    o = o or {}
    out = ['<h3>完整内容 (cleaned · 全部字段，未变更也显示)</h3>']
    for key, label, prose in _PROB_CTX_FIELDS:
        val = c.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            continue
        changed = _norm(o.get(key)) != _norm(val)
        out.append(_ctx_box(label, val, prose, changed))
    o_steps = {s.get("step_number"): s for s in (o.get("sub_steps") or [])}
    for ss in (c.get("sub_steps") or []):
        sn = str(ss.get("step_number"))
        os_ = o_steps.get(ss.get("step_number"), {})
        out.append(f'<div class="ctxstep"><div class="ctxsteptitle nomath">▼ 步骤 {html.escape(sn)}</div>')
        for key in _STEP_FIELDS:
            val = ss.get(key)
            if val is None or (isinstance(val, str) and not val.strip()) or (isinstance(val, list) and not val):
                continue
            changed = _norm(os_.get(key)) != _norm(val)
            out.append(_ctx_box(_FIELD_LABEL.get(key, key), val, key in _PROSE_FIELDS, changed))
        out.append('</div>')
    return "".join(out)


def render_problem_html(pid):
    d = get_diff(pid)
    o = _ORIG.get(str(pid))
    c = _CLEAN.get(str(pid))
    name = html.escape(d["name"])
    parts = [f'<h2>题 {html.escape(str(pid))} · {name}</h2>']

    # ---- per-problem cleaning summary (both rounds) ----
    le = _LOG.get(str(pid))
    if le and (le.get("r1_summary") or le.get("r2_summary")):
        parts.append('<div class="logsumm nomath">')
        if le.get("r1_summary"):
            parts.append(f'<div><span class="rbadge r-R1">R1</span> {html.escape(le["r1_summary"])}</div>')
        if le.get("r2_summary"):
            parts.append(f'<div><span class="rbadge r-R2">R2</span> {html.escape(le["r2_summary"])}</div>')
        parts.append('</div>')

    if d.get("only_side"):
        parts.append(f'<div class=headline>该题只存在于一侧: {html.escape(d["only_side"])}</div>')
        return "".join(parts)
    if not d["changed"]:
        parts.append('<div class=empty>此题清洗前后内容完全一致（无变更）。</div>')
        parts.append(_full_context_html(pid, o, c))
        return "".join(parts)

    tagspans = "".join(f'<span class="tag t-{html.escape(t)}">{html.escape(t)}</span>'
                       for t in d["tags"])
    parts.append(f'<div class=chips>{tagspans}</div>')
    parts.append(f'<div class=meta>{len(d["fields"])} 个字段文本变更 · '
                 f'{len(d["target_changes"])} 个步骤 target 变更</div>')
    if d["patch_note"]:
        parts.append(f'<div class=headline><b>补丁说明 (note):</b> '
                     f'<span class=nomath>{html.escape(d["patch_note"])}</span></div>')

    # ---- text field diffs ----
    if d["fields"]:
        parts.append('<h3>文本变更 (original → cleaned)</h3>')
    for f in d["fields"]:
        prose = f["prose"]
        cls = "prose" if prose else "nomath code"
        inline = _inline_diff_html(f["before"], f["after"])
        parts.append('<div class=fld>')
        parts.append(f'<div class="lbl nomath">{html.escape(str(f["step"]))} · '
                     f'{html.escape(f["label"])}</div>')
        # combined inline diff
        parts.append(f'<div class="diff {cls}">{inline}</div>')
        # explicit before/after panels for clarity
        bcls = "prose" if prose else "nomath"
        parts.append('<details class=ba><summary>BEFORE → AFTER 分栏</summary>')
        parts.append('<div class=bawrap>')
        parts.append(f'<div class=bacol><div class="balbl">BEFORE</div>'
                     f'<div class="babox {bcls}">{html.escape(f["before"])}</div></div>')
        parts.append(f'<div class=bacol><div class="balbl">AFTER</div>'
                     f'<div class="babox {bcls}">{html.escape(f["after"])}</div></div>')
        parts.append('</div></details>')
        parts.append(_reasons_html(pid, str(f["step"]), f["field"]))
        parts.append('</div>')

    # ---- target diffs ----
    if d["target_changes"]:
        parts.append('<h3>Target 变更 (test_data.h5 → test_data_cleaned.h5)</h3>')
    for tc in d["target_changes"]:
        parts.append('<div class="fld tint-target">')
        parts.append(f'<div class="lbl nomath">步骤 {html.escape(str(tc["step"]))} · '
                     f'target 取自 h5</div>')
        if tc["note"]:
            parts.append(f'<div class=fieldnote>说明: '
                         f'<span class=nomath>{html.escape(tc["note"])}</span></div>')
        parts.append('<table class=tgt>')
        parts.append('<tr><th>test</th><th>原 target</th><th>新 target</th></tr>')
        for t in tc["tests"]:
            parts.append(f'<tr><td>{html.escape(str(t["i"]))}</td>'
                         f'<td class=nomath><del>{html.escape(t["before"])}</del></td>'
                         f'<td class=nomath><ins>{html.escape(t["after"])}</ins></td></tr>')
        parts.append('</table>')
        parts.append(_reasons_html(pid, str(tc["step"]), "target"))
        parts.append('</div>')

    parts.append(_full_context_html(pid, o, c))
    return "".join(parts)


PAGE = r"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<title>SciCode Fix Viewer · 清洗变更</title>
<script>
window.MathJax = { tex:{ inlineMath:[['$','$'],['\\(','\\)']], displayMath:[['$$','$$'],['\\[','\\]']], processEscapes:true },
  options:{ ignoreHtmlClass:'nomath', skipHtmlTags:['script','noscript','style','textarea','pre','code'] } };
</script>
<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
<style>
*{box-sizing:border-box;} body{margin:0;font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;color:#1a1a1a;}
#app{display:flex;height:100vh;}
#side{width:320px;border-right:1px solid #ddd;overflow-y:auto;background:#fafafa;flex-shrink:0;}
#side h1{font-size:14px;padding:12px;margin:0;background:#222;color:#fff;position:sticky;top:0;z-index:2;}
.filters{padding:8px;display:flex;gap:4px;flex-wrap:wrap;position:sticky;top:39px;background:#fafafa;border-bottom:1px solid #eee;z-index:1;}
.filters button{font-size:11px;padding:3px 8px;border:1px solid #ccc;background:#fff;border-radius:10px;cursor:pointer;}
.filters button.on{background:#222;color:#fff;border-color:#222;}
.summary{font-size:12px;color:#555;padding:8px 12px;border-bottom:1px solid #eee;line-height:1.5;}
.row{padding:7px 12px;border-bottom:1px solid #eee;cursor:pointer;font-size:13px;display:flex;gap:6px;align-items:baseline;flex-wrap:wrap;}
.row:hover{background:#eef4ff;} .row.sel{background:#dbe9ff;}
.row.unchanged{opacity:.45;} .row .id{font-weight:600;min-width:24px;}
.row .nm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#444;}
.row .tags{flex-basis:100%;display:flex;gap:3px;flex-wrap:wrap;margin-top:2px;}
.tag{font-size:10px;padding:1px 6px;border-radius:8px;background:#eee;color:#555;}
.t-target{background:#fde0e0;color:#a00;} .t-test{background:#e3f0ff;color:#06c;}
.t-prompt{background:#fff0d6;color:#a60;} .t-header{background:#e7f7e7;color:#0a7a3a;}
.t-background{background:#efe3ff;color:#73c;} .t-return{background:#f0e6d6;color:#85601a;} .t-io{background:#dde;color:#446;}
#main{flex:1;overflow-y:auto;padding:20px 28px;}
#main h2{margin:0 0 6px;} #main h3{margin:22px 0 8px;border-bottom:1px solid #eee;padding-bottom:4px;font-size:15px;}
.meta{color:#777;font-size:13px;margin-bottom:10px;}
.chips{margin:6px 0 4px;} .chips .tag{font-size:12px;margin-right:5px;}
.headline{background:#f6f8fa;border-left:3px solid #888;padding:8px 12px;font-size:13px;margin:12px 0;color:#333;line-height:1.5;}
.fld{margin:12px 0;padding:8px 10px;border:1px solid #e2e2e2;border-radius:6px;}
.fld .lbl{font-size:11px;color:#888;text-transform:uppercase;letter-spacing:.04em;margin-bottom:5px;}
.fld.tint-target{border-color:#e88;background:#fff6f6;}
.diff{font-size:13px;line-height:1.55;white-space:pre-wrap;word-break:break-word;padding:6px 8px;border-radius:5px;background:#fbfbf7;}
.diff.code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;background:#0d1117;color:#c9d1d9;}
.diff.prose{font-family:inherit;}
del{background:#ffe3e3;color:#a00;text-decoration:line-through;border-radius:2px;padding:0 1px;}
ins{background:#dcffe0;color:#0a6b2a;text-decoration:none;border-radius:2px;padding:0 1px;}
.diff.code del{background:#5a1d1d;color:#ffb4b4;} .diff.code ins{background:#16431f;color:#a8f0bb;}
details.ba{margin-top:6px;} details.ba summary{cursor:pointer;color:#06c;font-size:12px;}
.bawrap{display:flex;gap:10px;margin-top:6px;} .bacol{flex:1;min-width:0;}
.balbl{font-size:10px;color:#888;letter-spacing:.05em;margin-bottom:2px;}
.babox{white-space:pre-wrap;word-break:break-word;padding:6px 8px;border-radius:5px;font-size:12px;line-height:1.5;border:1px solid #eee;background:#fafafa;}
.babox.nomath{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;}
.fieldnote{font-size:12px;color:#a60;margin-bottom:6px;}
table.tgt{width:100%;border-collapse:collapse;font-size:12px;margin-top:4px;}
table.tgt th,table.tgt td{border:1px solid #e2e2e2;padding:4px 6px;text-align:left;vertical-align:top;}
table.tgt th{background:#f3f4f6;} table.tgt td.nomath{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;word-break:break-word;}
table.tgt del,table.tgt ins{text-decoration:none;display:block;}
.empty{color:#888;padding:20px;}
.logsumm{background:#eef6ff;border:1px solid #cfe2ff;border-radius:6px;padding:8px 10px;margin:8px 0 4px;font-size:13px;line-height:1.6;}
.logsumm>div{margin:2px 0;}
.reasonwrap{margin-top:6px;}
.reason{font-size:12.5px;line-height:1.55;background:#fffbe9;border-left:3px solid #e8c34a;padding:6px 9px;border-radius:0 5px 5px 0;margin-top:5px;color:#3a3320;}
.reason.none{background:#f6f6f6;border-left-color:#ccc;color:#999;}
.rbadge{display:inline-block;font-size:10px;font-weight:700;padding:1px 6px;border-radius:8px;margin-right:5px;color:#fff;}
.r-R1{background:#6c8ebf;} .r-R2{background:#b07b2e;}
.nat{display:inline-block;font-size:10.5px;padding:1px 7px;border-radius:8px;margin-right:5px;background:#e6e6e6;color:#444;}
.n-convention{background:#e7f7e7;color:#0a7a3a;} .n-contract{background:#e3f0ff;color:#06c;}
.n-knob{background:#ffe0e0;color:#b00;} .n-explain{background:#ffe8cc;color:#a60;}
.n-leak{background:#ffd6e7;color:#c0157a;} .n-tolerance{background:#fff0d6;color:#a60;}
.n-testfix{background:#e3f0ff;color:#06c;} .n-terminology{background:#efe3ff;color:#73c;}
.n-consistency{background:#e7eefc;color:#3556a8;} .n-target{background:#fde0e0;color:#a00;}
.n-review{background:#f0e0c0;color:#806000;} .n-nochange{background:#eee;color:#888;}
.scope{color:#999;font-size:11px;}
.ctxstep{border:1px solid #e8e8e8;border-radius:6px;margin:10px 0;padding:6px 12px;background:#fcfcfc;}
.ctxsteptitle{font-size:13px;font-weight:600;color:#333;margin:2px 0 6px;}
.ctxfld{margin:8px 0;}
.ctxfld .lbl{font-size:11px;color:#888;text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px;}
.ctxbody{white-space:pre-wrap;word-break:break-word;padding:7px 9px;border-radius:5px;font-size:13px;line-height:1.6;border:1px solid #eee;background:#fafafa;}
.ctxbody.code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;background:#0d1117;color:#c9d1d9;border-color:#222;}
.ctxbody.prose{font-family:inherit;}
.ctxchanged>.ctxbody{border-left:3px solid #e8a33a;background:#fffaf0;}
.ctxchanged>.ctxbody.code{background:#1a160d;border-left-color:#e8a33a;}
.cbadge{display:inline-block;font-size:10px;font-weight:700;padding:1px 6px;border-radius:8px;background:#e8a33a;color:#fff;margin-left:6px;text-transform:none;letter-spacing:0;}
</style></head><body><div id=app>
<div id=side><h1>SciCode 清洗变更 (original → cleaned)</h1>
<div class=summary id=summary>加载中…</div>
<div class=filters id=filters>
 <button data-f=changed class=on>已变更</button><button data-f=target>含target变更</button>
 <button data-f=textonly>仅文本</button><button data-f=all>全部(含未变)</button>
</div><div id=list></div></div>
<div id=main><div class=empty>← 从左侧选一道题查看清洗 diff</div></div></div>
<script>
let INDEX=[],FILTER='changed',SEL=null;
const esc=s=>(s==null?'':String(s)).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function passFilter(p){
  if(FILTER=='all') return true;
  if(FILTER=='changed') return p.changed;
  if(FILTER=='target') return p.target_changed;
  if(FILTER=='textonly') return p.text_only;
  return true;
}
async function boot(){ INDEX=await(await fetch('/api/index')).json(); renderSummary(); render(); }
function renderSummary(){
  const ch=INDEX.filter(p=>p.changed);
  const tgt=ch.filter(p=>p.target_changed).length;
  const txt=ch.filter(p=>p.text_only).length;
  document.getElementById('summary').innerHTML=
    `<b>${ch.length}</b> 题被清洗修改（共 ${INDEX.length} 题）· `
    +`仅文本 <b>${txt}</b> · 含 target 变更 <b>${tgt}</b>`;
}
function render(){ const L=document.getElementById('list'); L.innerHTML='';
  INDEX.filter(passFilter).forEach(p=>{
    const d=document.createElement('div');
    d.className='row'+(SEL==p.id?' sel':'')+(p.changed?'':' unchanged');
    const ic=p.changed?(p.target_changed?'🔴':'✎'):'·';
    const tags=(p.tags||[]).map(t=>`<span class="tag t-${esc(t)}">${esc(t)}</span>`).join('');
    d.innerHTML=`<span class=id>${esc(p.id)}</span><span>${ic}</span>`
      +`<span class=nm>${esc(p.name)}</span>`
      +(tags?`<span class=tags>${tags}</span>`:'');
    d.onclick=()=>openP(p.id); L.appendChild(d);
  });
}
document.getElementById('filters').onclick=e=>{if(e.target.dataset.f){FILTER=e.target.dataset.f;
  [...document.querySelectorAll('#filters button')].forEach(b=>b.classList.toggle('on',b.dataset.f==FILTER));render();}};
async function openP(id){ SEL=id; render();
  const html=await(await fetch('/api/problem/'+id)).text();
  const main=document.getElementById('main'); main.innerHTML=html; main.scrollTop=0;
  if(window.MathJax&&MathJax.typesetPromise) MathJax.typesetPromise([main]).catch(()=>{});
}
boot();
</script></body></html>"""


def _reload():
    """Re-read all source files so a browser refresh shows the latest edits
    (no server restart needed). Cheap text reads; clears the diff cache."""
    global _ORIG, _CLEAN, _PATCHES, _LOG
    _ORIG = _load_jsonl(_ORIG_JSONL)
    _CLEAN = _load_jsonl(_CLEAN_JSONL)
    _PATCHES = _load_patches()
    try:
        _LOG = json.load(open(_LOG_PATH))
    except Exception:
        _LOG = {}
    _DIFF_CACHE.clear()


class H(BaseHTTPRequestHandler):
    def _send(self, body, ctype="application/json"):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(200)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        try:
            if self.path == "/" or self.path.startswith("/index"):
                self._send(PAGE, "text/html")
            elif self.path == "/api/index":
                _reload()
                self._send(json.dumps(build_index(), ensure_ascii=False))
            elif self.path.startswith("/api/problem/"):
                _reload()
                pid = self.path.rsplit("/", 1)[1]
                self._send(render_problem_html(pid), "text/html")
            else:
                self.send_error(404)
        except Exception as e:
            self.send_error(500, str(e))

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"SciCode Fix Viewer → http://localhost:{port}   (Ctrl-C 退出)")
    HTTPServer(("127.0.0.1", port), H).serve_forever()
