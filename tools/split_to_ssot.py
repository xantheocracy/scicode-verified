"""Bootstrap (run ONCE): split the current released problems_test.jsonl into the
per-problem SSOT files scicode_verified/problems/<id>.json.

The SSOT is derived FROM the authoritative current release so that, by
construction, assemble.py reproduces the release byte-for-byte (the baseline
anchor required before any content edits — see the verify-with-human skill).

SSOT files are pretty-printed (indent=1, ensure_ascii=False) for human review;
key order is preserved exactly as in the jsonl, so a compact re-dump round-trips.
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSONL = os.path.join(ROOT, 'scicode_verified', 'problems_test.jsonl')
OUTDIR = os.path.join(ROOT, 'scicode_verified', 'problems')
os.makedirs(OUTDIR, exist_ok=True)

with open(JSONL, encoding='utf-8') as f:
    objs = [json.loads(l) for l in f if l.strip()]

for o in objs:
    pid = str(o['problem_id'])
    with open(os.path.join(OUTDIR, f'{pid}.json'), 'w', encoding='utf-8') as g:
        json.dump(o, g, ensure_ascii=False, indent=1)
        g.write('\n')

print(f'wrote {len(objs)} SSOT files to {OUTDIR}')
