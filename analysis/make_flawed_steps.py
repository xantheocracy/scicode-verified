#!/usr/bin/env python3
"""Materialize the flawed-subproblem list from the defect ledger.

Counting rule (deterministic, no judgment calls):
- Suppressor defects = direction == 'too-strict/wrong' in taxonomy/defects.json.
- A defect's step footprint = every step id it names, parsed from
  (a) the leading "P.S" in its own `step` field, and
  (b) any "step P.S" / "(P.S)" / "targets.P.S" reference inside `fields_involved`.
  Problem-level fields (problem_description_main, problem_io, general_tests)
  are NOT expanded to all steps of the problem — conservative attribution.
- Layer "broad"   : step is named by any suppressor defect.
- Layer "grading" : step is named by a suppressor defect at least one of whose
  fields touches the grading surface (test_cases / general_tests / target* / gold).
- Universe = the 287 scored steps of the 64 released problems (problem 2 excluded),
  taken from a run4 results.json. Referenced steps outside the universe are
  reported as anomalies and excluded from percentages.
"""
import json, re, collections, pathlib

ROOT = pathlib.Path('/home/hsh/code/ML/SciCode_refine')
DEFECTS = ROOT / 'paper/analysis/taxonomy/defects.json'
UNIVERSE_FROM = ROOT / 'eval_clean/ds_runs/run4/cleaned_qwen3.6-35b-a3b/with_bg/results.json'
OUT = ROOT / 'paper/analysis/flawed_steps.json'

step_pat = re.compile(r'step (\d+\.\d+)|\((\d+\.\d+)\)|targets\.(\d+\.\d+)')
lead_pat = re.compile(r'^(\d+\.\d+)')

def grading_field(f: str) -> bool:
    f = f.lower()
    return 'test' in f or 'target' in f or 'gold' in f

defects = json.load(open(DEFECTS))
if isinstance(defects, dict):
    defects = defects['defects']
supp = [d for d in defects if d['direction'] == 'too-strict/wrong']

res = json.load(open(UNIVERSE_FROM))
universe = {s for r in res['results'] for s in r['steps']}
universe -= {'13.6', '62.1', '76.3'}   # steps the official harness skips (SKIP in run_deepseek_eval.py)
uni_problems = {s.split('.')[0] for s in universe}
assert len(universe) == 287 and len(uni_problems) == 64, (len(universe), len(uni_problems))

per_step = collections.defaultdict(lambda: {'defect_ids': [], 'grading': False})
anomalies = []
for d in supp:
    steps = set()
    step_field = str(d['step']).strip()
    m = lead_pat.match(step_field)
    if m:
        steps.add(m.group(1))
    for mm in step_pat.finditer(step_field):
        steps.add(next(g for g in mm.groups() if g))
    for f in (d.get('fields_involved') or []):
        for mm in step_pat.finditer(f):
            steps.add(next(g for g in mm.groups() if g))
    if not steps:
        anomalies.append({'defect_id': d['defect_id'], 'reason': 'no step id parsed',
                          'step_field': str(d['step'])})
        continue
    grading = any(grading_field(f) for f in (d.get('fields_involved') or []))
    for s in steps:
        if s not in universe:
            anomalies.append({'defect_id': d['defect_id'], 'reason': f'step {s} outside universe'})
            continue
        per_step[s]['defect_ids'].append(d['defect_id'])
        per_step[s]['grading'] |= grading

def key(s): return tuple(map(int, s.split('.')))
steps_out = [{'step_id': s, 'problem': s.split('.')[0],
              'layers': ['broad', 'grading'] if v['grading'] else ['broad'],
              'defect_ids': sorted(v['defect_ids'])}
             for s, v in sorted(per_step.items(), key=lambda kv: key(kv[0]))]

def layer_summary(pred):
    ss = [e for e in steps_out if pred(e)]
    pp = {e['problem'] for e in ss}
    return {'steps': len(ss), 'steps_pct': round(100 * len(ss) / 287, 1),
            'problems': len(pp), 'problems_pct': round(100 * len(pp) / 64, 1),
            'problem_ids': sorted(pp, key=int)}

summary = {'broad': layer_summary(lambda e: True),
           'grading': layer_summary(lambda e: 'grading' in e['layers'])}

# defect-level fields split (paper §4): test/gold-only vs solver-visible-only vs both
tg_only = vis_only = both = 0
for d in supp:
    fs = d.get('fields_involved') or []
    tg = any(grading_field(f) for f in fs)
    vis = any(not grading_field(f) for f in fs)
    if tg and vis: both += 1
    elif tg: tg_only += 1
    else: vis_only += 1
summary['defect_fields_split'] = {'test_gold_only': tg_only, 'visible_only': vis_only, 'both': both}

json.dump({'rule': __doc__.strip(), 'suppressor_defects': len(supp),
           'universe': {'steps': 287, 'problems': 64},
           'summary': summary, 'anomalies': anomalies, 'steps': steps_out},
          open(OUT, 'w'), indent=1, ensure_ascii=False)

print(f"suppressor defects: {len(supp)}")
for name, s in summary.items():
    if 'steps' not in s:
        print(f"{name}: {s}")
        continue
    print(f"{name:8s}: {s['steps']}/287 steps ({s['steps_pct']}%), "
          f"{s['problems']}/64 problems ({s['problems_pct']}%)")
print(f"anomalies: {len(anomalies)}")
for a in anomalies:
    print("  ", a)
