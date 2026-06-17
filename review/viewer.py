#!/usr/bin/env python3
"""Zero-dependency viewer for the SciCode review (LaTeX + defect highlighting).

Usage:  python3 review/viewer.py          # then open http://localhost:8000
        python3 review/viewer.py 8001      # custom port

Stdlib only. Serves a one-problem-at-a-time browser:
 - renders LaTeX in prompts/derivations via MathJax (CDN; degrades to raw text offline),
 - classifies each confirmed defect to its field and tints that field,
 - highlights verbatim quotes from the defect evidence inside the original text.
"""
import json, sys, re
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = Path(__file__).resolve().parent
_PROJ = ROOT.parent
sys.path.insert(0, str(_PROJ / "SciCode" / "src"))
_H5 = _PROJ / "SciCode" / "eval" / "data" / "test_data.h5"
try:
    from scicode.parse.parse import process_hdf5_to_tuple as _h5tuple
except Exception:
    _h5tuple = None
_SKIP = {"13.6", "62.1", "76.3"}
_TGT_CACHE = {}


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


def load_targets(step_number, n_tests):
    """Return a list of preview strings, one per test case (or an error note)."""
    if step_number in _SKIP:
        return ["(官方跳过步,h5 无目标值)"] * n_tests
    if _h5tuple is None or not _H5.exists():
        return ["(未找到 test_data.h5,无法读取目标值)"] * n_tests
    if step_number in _TGT_CACHE:
        return _TGT_CACHE[step_number]
    try:
        tgts = _h5tuple(step_number, n_tests, str(_H5))
        out = [_preview(t) for t in tgts]
    except Exception as e:
        out = [f"(读取失败: {e})"] * n_tests
    _TGT_CACHE[step_number] = out
    return out
SEVRANK = {"minor": 0, "major": 1, "blocker": 2}
DEFN = {"D1": "签名不匹配", "D2": "信息缺失/无法做出", "D3": "单位制不明", "D4": "约定不明",
        "D5": "非确定性", "D6": "容差脆弱", "D7": "target错误", "D8": "测试过弱",
        "D9": "跨步依赖", "D10": "文档矛盾", "D11": "缺target", "D12": "依赖漂移"}
# field keys: description / background / header / test / target / dep
FIELD_OF_FIX = {"header_edit": "header", "prompt_edit": "description", "test_edit": "test",
                "tolerance_change": "test", "target_regen": "target", "step_drop": "target",
                "env_pin": "dep"}


def load(kind, pid):
    p = ROOT / kind / f"{pid}.json"
    return json.loads(p.read_text()) if p.exists() else None


def classify_field(vd, finding):
    fx = vd.get("fix") if isinstance(vd.get("fix"), dict) else None
    loc = (fx or {}).get("target_location", "") or ""
    l = loc.lower()
    if l:
        if "background" in l: return "background"
        if any(k in l for k in ["function_header", "docstring", "return_line", "problem_io"]): return "header"
        if "description" in l or "prompt" in l: return "description"
        if "test_case" in l or l.startswith("test"): return "test"
        if "h5" in l or "target" in l: return "target"
        if "depend" in l: return "dep"
    fk = vd.get("fix_kind") or (fx or {}).get("kind")
    if fk in FIELD_OF_FIX: return FIELD_OF_FIX[fk]
    dt = vd.get("defect_type")
    if dt == "D1": return "header"
    if dt == "D12": return "dep"
    if dt in ("D7", "D11"): return "target"
    if dt in ("D5", "D6", "D8", "D9"): return "test"
    txt = (str(finding.get("evidence", "")) + " " +
           str(vd.get("one_liner") or vd.get("reproduction") or "")).lower()
    if "background" in txt: return "background"
    if any(k in txt for k in ["docstring", "function_header", "return_line", "problem_io", "header"]): return "header"
    return "description"


def extract_quotes(*texts):
    """Verbatim citations the reviewer put in quotes; skip ones with $ (would break MathJax)."""
    out, seen = [], set()
    for t in texts:
        if not t: continue
        for m in re.findall(r"'([^']{10,140})'", str(t)) + re.findall(r'"([^"]{10,140})"', str(t)):
            q = m.strip()
            if q and "$" not in q and "\\(" not in q and q not in seen:
                seen.add(q); out.append(q)
    return out


def merged(pid):
    prob = load("problems", pid)
    find = load("findings", pid) or {}
    verd = load("verdicts", pid) or {}
    orig = {(x["step_number"], x["defect_type"]): x for x in find.get("findings", [])}
    by_step = {}
    nconf = nref = nunc = nblk = 0
    for vd in verd.get("verdicts", []):
        st, dt, ver = vd.get("step_number"), vd.get("defect_type"), vd.get("verdict")
        f = orig.get((st, dt), {})
        rs = vd.get("revised_severity"); rs = rs if rs in SEVRANK else None
        sev = rs or f.get("severity", "minor")
        fx = vd.get("fix")
        rec = {
            "step": st, "type": dt, "type_name": DEFN.get(dt, ""), "verdict": ver, "severity": sev,
            "field": classify_field(vd, f),
            "fix_kind": vd.get("fix_kind") or (fx.get("kind") if isinstance(fx, dict) else None),
            "reason": vd.get("one_liner") or vd.get("reproduction") or vd.get("uncertainty_notes") or "",
            "evidence": f.get("evidence", ""),
            "suggested_fix": f.get("suggested_fix", ""),
            "quotes": extract_quotes(f.get("evidence", ""), vd.get("one_liner"), vd.get("reproduction")),
        }
        by_step.setdefault(st, []).append(rec)
        if ver == "confirmed":
            nconf += 1
            if sev == "blocker": nblk += 1
        elif ver == "refuted": nref += 1
        elif ver == "uncertain": nunc += 1
    targets = {}
    for st in (prob.get("sub_steps", []) if prob else []):
        sn = st.get("step_number"); tcs = st.get("test_cases") or []
        if sn and tcs:
            targets[sn] = load_targets(sn, len(tcs))
    return {"problem": prob, "by_step": by_step, "targets": targets,
            "stats": {"confirmed": nconf, "refuted": nref, "uncertain": nunc, "blocker": nblk},
            "summary": verd.get("summary", ""),
            "headline": find.get("headline", find.get("overall_assessment", ""))}


_CLEANDIR = _PROJ / "cleaning" / "problems"
_QUARDIR = _PROJ / "cleaning" / "log"


def _clean_status(pid):
    if (_CLEANDIR / f"{pid}.json").exists():
        return "fixed"
    # quarantined: has a log but no publishable problem
    log = _QUARDIR / f"{pid}.md"
    if log.exists() and "QUARANTINE" in log.read_text(errors="ignore"):
        return "quarantine"
    return ""


def index():
    out = []
    for pid in range(1, 81):
        prob = load("problems", pid)
        if not prob: continue
        s = merged(pid)["stats"]
        out.append({"id": pid, "name": prob.get("problem_name", "?"), "split": prob.get("split", "?"),
                    "steps": len(prob.get("sub_steps", [])), "confirmed": s["confirmed"], "blocker": s["blocker"],
                    "clean_status": _clean_status(pid)})
    return out


PAGE = r"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<title>SciCode Review Viewer</title>
<script>
window.MathJax = { tex:{ inlineMath:[['$','$'],['\\(','\\)']], displayMath:[['$$','$$'],['\\[','\\]']], processEscapes:true },
  options:{ ignoreHtmlClass:'nomath', skipHtmlTags:['script','noscript','style','textarea','pre','code'] } };
</script>
<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
<style>
*{box-sizing:border-box;} body{margin:0;font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;color:#1a1a1a;}
#app{display:flex;height:100vh;}
#side{width:300px;border-right:1px solid #ddd;overflow-y:auto;background:#fafafa;flex-shrink:0;}
#side h1{font-size:14px;padding:12px;margin:0;background:#222;color:#fff;position:sticky;top:0;z-index:2;}
.filters{padding:8px;display:flex;gap:4px;flex-wrap:wrap;position:sticky;top:39px;background:#fafafa;border-bottom:1px solid #eee;z-index:1;}
.filters button{font-size:11px;padding:3px 8px;border:1px solid #ccc;background:#fff;border-radius:10px;cursor:pointer;}
.filters button.on{background:#222;color:#fff;border-color:#222;}
.row{padding:7px 12px;border-bottom:1px solid #eee;cursor:pointer;font-size:13px;display:flex;gap:6px;align-items:baseline;}
.row:hover{background:#eef4ff;} .row.sel{background:#dbe9ff;}
.row .id{font-weight:600;min-width:24px;} .row .nm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#444;}
.row .tag{font-size:10px;color:#888;}
.grouphdr{padding:8px 12px;background:#e8e8e8;font-weight:700;font-size:12px;cursor:pointer;border-bottom:1px solid #ccc;border-top:1px solid #ccc;}
.grouphdr small{font-weight:400;color:#777;} .row.cleaned .nm{color:#0a7a3a;}
#main{flex:1;overflow-y:auto;padding:20px 28px;}
#main h2{margin:0 0 4px;} .meta{color:#777;font-size:13px;margin-bottom:10px;}
.chips span{display:inline-block;font-size:12px;padding:2px 9px;border-radius:10px;margin-right:6px;}
.c-blocker{background:#fde0e0;color:#a00;}.c-major{background:#fff0d6;color:#a60;}.c-ref{background:#e3f0ff;color:#06c;}.c-unc{background:#efe3ff;color:#73c;}
.headline{background:#f6f8fa;border-left:3px solid #888;padding:8px 12px;font-size:13px;margin:12px 0;color:#333;}
.legend{font-size:11px;color:#888;margin:6px 0 14px;} .legend mark{padding:0 4px;}
.step{border:1px solid #e2e2e2;border-radius:6px;margin:14px 0;overflow:hidden;}
.step.has-blocker{border-color:#e88;}.step.has-major{border-color:#ecb86a;}
.step>.sh{background:#f3f4f6;padding:8px 12px;font-weight:600;font-size:14px;cursor:pointer;display:flex;justify-content:space-between;gap:8px;}
.step .body{padding:10px 14px;display:none;} .step.open .body{display:block;}
.fld{margin:8px 0;padding:6px 8px;border-radius:5px;} .fld .lbl{font-size:11px;color:#888;text-transform:uppercase;letter-spacing:.04em;}
.fld.tint-blocker{background:#fff5f5;box-shadow:inset 3px 0 #d33;} .fld.tint-major{background:#fffaf0;box-shadow:inset 3px 0 #e9a13b;} .fld.tint-minor{background:#f7f7f7;box-shadow:inset 3px 0 #bbb;}
pre{background:#0d1117;color:#c9d1d9;padding:10px;border-radius:5px;overflow-x:auto;font-size:12px;line-height:1.45;white-space:pre-wrap;word-break:break-word;}
.prompt{background:#fbfbf7;border:1px solid #eee;padding:8px 10px;border-radius:5px;font-size:13px;white-space:pre-wrap;line-height:1.5;}
mark{padding:0 1px;border-radius:2px;} mark.hl-blocker{background:#ffe3e3;border-bottom:2px solid #e57373;}
mark.hl-major{background:#fff4e0;border-bottom:2px solid #eab560;} mark.hl-minor{background:#eee;border-bottom:2px solid #bbb;}
pre mark{color:#1a1a1a;} pre .tgt{color:#6fd66f;font-weight:600;}
sup.hlc{font-size:9px;vertical-align:super;color:#777;font-weight:700;margin-left:1px;cursor:help;}
.defect{border-left:3px solid #ccc;padding:6px 10px;margin:8px 0;background:#fff;font-size:13px;}
.defect.confirmed.blocker{border-color:#d33;background:#fff6f6;}.defect.confirmed.major{border-color:#e9a13b;background:#fffaf0;}.defect.confirmed.minor{border-color:#bbb;}
.defect.refuted{border-color:#06c;background:#f4f9ff;}.defect.uncertain{border-color:#83c;background:#faf5ff;}
.defect .dh{font-weight:600;} .defect .dh small{font-weight:400;color:#777;} .defect .reason{margin-top:3px;color:#333;}
.defect details{margin-top:5px;} .defect summary{cursor:pointer;color:#06c;font-size:12px;} .defect details div{font-size:12px;color:#555;margin-top:4px;white-space:pre-wrap;}
.fieldnote{font-size:11px;color:#a60;margin-bottom:3px;} .empty{color:#888;padding:20px;}
.badge{font-size:10px;padding:1px 6px;border-radius:8px;} .b-blocker{background:#fde0e0;color:#a00;}.b-major{background:#fff0d6;color:#a60;}.b-minor{background:#eee;color:#666;}
</style></head><body><div id=app>
<div id=side><h1>SciCode Review · 80 题</h1>
<div class=filters id=filters>
 <button data-f=all class=on>全部</button><button data-f=blocker>🔴blocker</button><button data-f=defect>有缺陷</button>
 <button data-f=clean>✅干净</button><button data-f=cleaned>✎已清洗</button>
</div><div id=list></div></div>
<div id=main><div class=empty>← 从左侧选一道题</div></div></div>
<script>
let INDEX=[],FILTER='all',SEL=null,GROUP_OPEN={test:true,dev:true};
const SEVRANK={minor:0,major:1,blocker:2};
const esc=s=>(s==null?'':String(s)).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
// escape text, then wrap cited verbatim quotes. A mark is NOT "the bug" — it is text the
// defect's evidence references. Each carries a superscript defect code + hover reason so an
// incidental citation (e.g. a dead variable) isn't mistaken for the cause.
function hl(text, defs){
  const map=new Map();  // quote -> defect (keep highest severity if cited by several)
  defs.forEach(d=>(d.quotes||[]).forEach(q=>{ const c=map.get(q);
    if(!c||SEVRANK[d.severity]>SEVRANK[c.severity]) map.set(q,d); }));
  let s=esc(text);
  [...map.keys()].sort((a,b)=>b.length-a.length).forEach(q=>{ const d=map.get(q);
    const eq=esc(q); const i=s.indexOf(eq); if(i<0) return;
    const tip=esc(`${d.type} ${d.type_name} · ${d.severity} · ${d.reason}`).slice(0,280).replace(/"/g,'&quot;');
    s=s.slice(0,i)+`<mark class="hl-${d.severity}" title="${tip}">`+eq+`<sup class=hlc title="${tip}">${d.type}</sup></mark>`+s.slice(i+eq.length); });
  return s;
}
function fieldDefs(defs,key){ return defs.filter(d=>d.verdict=='confirmed'&&d.field==key); }
function tint(defs){ if(defs.some(d=>d.severity=='blocker'))return'tint-blocker'; if(defs.some(d=>d.severity=='major'))return'tint-major'; return defs.length?'tint-minor':''; }
function note(defs){ return defs.length?`<div class=fieldnote>⚠ 此处有缺陷:${defs.map(d=>d.type+' '+esc(d.type_name)).join('、')}</div>`:''; }
async function boot(){ INDEX=await(await fetch('/api/index')).json(); render(); }
function passFilter(p){ const f=FILTER;
  return f=='all'||(f=='blocker'&&p.blocker)||(f=='defect'&&p.confirmed)||(f=='clean'&&!p.confirmed)
    ||(f=='cleaned'&&p.clean_status); }
function statusMark(p){ return p.clean_status=='fixed'?'✎ ':(p.clean_status=='quarantine'?'⊘ ':''); }
function render(){ const L=document.getElementById('list'); L.innerHTML='';
  const filt=INDEX.filter(passFilter);
  ['test','dev'].forEach(split=>{
    const items=filt.filter(p=>p.split==split);
    const total=INDEX.filter(p=>p.split==split).length;
    const done=INDEX.filter(p=>p.split==split&&p.clean_status).length;
    const blk=items.filter(p=>p.blocker).length;
    const hdr=document.createElement('div'); hdr.className='grouphdr';
    hdr.innerHTML=`${GROUP_OPEN[split]?'▾':'▸'} ${split.toUpperCase()} <small>· 显示${items.length}/${total} 题 · 🔴${blk}${done?` · 已处理${done}`:''}</small>`;
    hdr.onclick=()=>{GROUP_OPEN[split]=!GROUP_OPEN[split];render();};
    L.appendChild(hdr);
    if(GROUP_OPEN[split]) items.forEach(p=>{
      const d=document.createElement('div'); d.className='row'+(SEL==p.id?' sel':'')+(p.clean_status=='fixed'?' cleaned':'');
      const ic=p.blocker?'🔴':(p.confirmed?'🟡':'✅');
      d.innerHTML=`<span class=id>${p.id}</span><span>${ic}</span><span class=nm>${statusMark(p)}${esc(p.name)}</span><span class=tag>${p.steps}步</span>`;
      d.onclick=()=>openP(p.id); L.appendChild(d);
    });
  });
}
document.getElementById('filters').onclick=e=>{if(e.target.dataset.f){FILTER=e.target.dataset.f;
  [...document.querySelectorAll('#filters button')].forEach(b=>b.classList.toggle('on',b.dataset.f==FILTER));render();}};
async function openP(id){ SEL=id; render();
  const m=await(await fetch('/api/problem/'+id)).json(); const p=m.problem,bs=m.by_step,s=m.stats;
  const chip=(n,cls,lbl)=>n?`<span class="${cls}">${lbl}: ${n}</span>`:'';
  let h=`<h2>题 ${p.problem_id} · ${esc(p.problem_name)}</h2>`;
  h+=`<div class="meta nomath">${p.split} 集 · ${p.sub_steps.length} 子步 · ${esc((p.required_dependencies||'').replace(/\n/g,' '))}</div>`;
  h+=`<div class=chips>${chip(s.blocker,'c-blocker','🔴blocker')}${chip(s.confirmed,'c-major','确认缺陷')}${chip(s.refuted,'c-ref','推翻')}${chip(s.uncertain,'c-unc','存疑')}</div>`;
  h+=`<div class=legend>缺陷以<b>字段级</b>标注:含缺陷的字段(题面/推导/契约/测试)整块按严重度上色(左侧色条)并列出缺陷类型;<b>具体哪一行错以该字段下方的缺陷卡片为准</b>(逐字片段高亮已移除,因其常只命中边角料而误导)。</div>`;
  if(m.headline) h+=`<div class=headline><b>一审结论:</b> ${esc(m.headline)}</div>`;
  if(m.summary)  h+=`<div class=headline><b>复核结论:</b> ${esc(m.summary)}</div>`;
  if(p.problem_description_main) h+=`<div class=fld><div class=lbl>主题面</div><div class=prompt>${esc(p.problem_description_main)}</div></div>`;
  p.sub_steps.forEach((st,i)=>{
    const defs=bs[st.step_number]||[];
    const conf=defs.filter(d=>d.verdict=='confirmed');
    const sevcls=conf.some(d=>d.severity=='blocker')?'has-blocker':(conf.some(d=>d.severity=='major')?'has-major':'');
    const badges=conf.map(d=>`<span class="badge b-${d.severity}">${d.type}</span>`).join(' ');
    h+=`<div class="step ${sevcls} ${i==0?'open':''}"><div class=sh onclick="this.parentNode.classList.toggle('open')"><span class=nomath>${st.step_number} ${esc((st.step_description_prompt||'').slice(0,70))}…</span><span>${badges}</span></div><div class=body>`;
    // Field-level only: tint + note the field that holds a defect. We do NOT span-highlight
    // verbatim quotes — they reliably hit only incidental mentions (e.g. a dead variable),
    // not the true locus (often a numeric property), which misleads. See defect card for the locus.
    const dfP=fieldDefs(defs,'description');
    h+=`<div class="fld ${tint(dfP)}"><div class=lbl>子步题面</div>${note(dfP)}<div class=prompt>${esc(st.step_description_prompt||'')}</div></div>`;
    if(st.step_background){ const dfB=fieldDefs(defs,'background');
      h+=`<div class="fld ${tint(dfB)}"><div class=lbl>理论推导 (background · 仅 with_background 模式)</div>${note(dfB)}<div class=prompt>${esc(st.step_background)}</div></div>`; }
    const dfH=fieldDefs(defs,'header');
    h+=`<div class="fld ${tint(dfH)}"><div class="lbl nomath">函数契约 (function_header)</div>${note(dfH)}<pre class=nomath>${esc(st.function_header||'')}</pre></div>`;
    if(st.test_cases&&st.test_cases.length){ const dfT=fieldDefs(defs,'test'); const tg=(m.targets||{})[st.step_number]||[];
      let tc=''; st.test_cases.forEach((c,j)=>{ tc+=esc(c)+'\n'; if(tg[j]!=null) tc+=`<span class=tgt># → target = ${esc(tg[j])}</span>\n`; if(j<st.test_cases.length-1) tc+='# ---- next test ----\n'; });
      h+=`<div class="fld ${tint(dfT)}"><div class="lbl nomath">测试用例 (${st.test_cases.length}) · target 取自 test_data.h5</div>${note(dfT)}<pre class=nomath>${tc}</pre></div>`; }
    const dfTgt=fieldDefs(defs,'target');
    if(dfTgt.length) h+=`<div class="fld tint-blocker"><div class=fieldnote>⚠ 裁判·target值 有缺陷(target 在 test_data.h5,此处无原文):${dfTgt.map(d=>d.type+' '+esc(d.type_name)).join('、')}</div></div>`;
    if(st.ground_truth_code) h+=`<div class=fld><div class="lbl nomath">标准答案 (gold · 仅 dev)</div><pre class=nomath>${esc(st.ground_truth_code)}</pre></div>`;
    if(defs.length){ h+=`<div><div class=lbl>缺陷 / 裁决</div>`;
      defs.forEach(d=>{ h+=`<div class="defect ${d.verdict} ${d.severity}"><div class="dh nomath">${SEVI(d)} ${d.type} ${esc(d.type_name)} <small>· ${d.verdict}${d.fix_kind?(' · 修法 '+d.fix_kind):''} · 字段 ${d.field}</small></div><div class=reason nomath>${esc(d.reason)}</div>`;
        if(d.evidence) h+=`<details><summary>一审证据</summary><div class=nomath>${esc(d.evidence)}</div></details>`;
        if(d.suggested_fix) h+=`<details><summary>修复建议</summary><div class=nomath>${esc(typeof d.suggested_fix=='string'?d.suggested_fix:JSON.stringify(d.suggested_fix,null,2))}</div></details>`;
        h+=`</div>`; }); h+=`</div>`; }
    h+=`</div></div>`;
  });
  const main=document.getElementById('main'); main.innerHTML=h; main.scrollTop=0;
  if(window.MathJax&&MathJax.typesetPromise) MathJax.typesetPromise([main]).catch(()=>{});
}
function SEVI(d){ return d.verdict=='confirmed'?({blocker:'🔴',major:'🟡',minor:'⚪'}[d.severity]):(d.verdict=='refuted'?'🔵推翻':'🟣存疑'); }
boot();
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def _send(self, body, ctype="application/json"):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(200); self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        try:
            if self.path == "/" or self.path.startswith("/index"):
                self._send(PAGE, "text/html")
            elif self.path == "/api/index":
                self._send(json.dumps(index(), ensure_ascii=False))
            elif self.path.startswith("/api/problem/"):
                self._send(json.dumps(merged(int(self.path.rsplit("/", 1)[1])), ensure_ascii=False))
            else:
                self.send_error(404)
        except Exception as e:
            self.send_error(500, str(e))

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"SciCode Review Viewer → http://localhost:{port}   (Ctrl-C 退出)")
    HTTPServer(("127.0.0.1", port), H).serve_forever()
