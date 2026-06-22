"""Normalize every legacy/cleaning/targets/*.json to ONE canonical format:
       {"problem_id": "<id>", "note": <str?>, "<step>": {"<idx>": value, ...}, ...}
   (top-level step keys -> {test_index: value}; metadata in problem_id/note.)

Deterministic: it only RELOCATES values, never alters them. For each file it backs up the
original to legacy/cleaning/_targets_orig_backup/, writes the canonical form, reloads it from disk,
and asserts the extracted {step:{idx:value}} is byte-identical to the source; on any mismatch
it RESTORES the original and flags the file. Files it cannot map (non-numeric target keys, e.g.
28.3) are FLAGGED and left untouched.
"""
import json, os, re, shutil
SRC = 'legacy/cleaning/targets'
BK = 'legacy/cleaning/_targets_orig_backup'
STEP = re.compile(r'^\d+\.\d+$')
os.makedirs(BK, exist_ok=True)

def is_idx(k):
    return str(k).lstrip('-').isdigit()

def extract(d):
    """Return ({step: {int_idx: value}}, flags) from any of the known on-disk shapes."""
    patches = {}; flags = []
    # FLAT: top-level "<step>": {"<idx>": value}
    for k, v in d.items():
        if STEP.match(k):
            if isinstance(v, dict):
                patches.setdefault(k, {}).update({int(i): val for i, val in v.items() if is_idx(i)})
                bad = [i for i in v if not is_idx(i)]
                if bad: flags.append(f'{k}: non-index keys {bad}')
            else:
                flags.append(f'{k}: top-level value not a dict ({type(v).__name__})')
    # NESTED: "targets": {"<step>": [vals] | {"<idx>": value}}
    t = d.get('targets')
    if isinstance(t, dict):
        for step, v in t.items():
            if not STEP.match(step):
                flags.append(f'targets has non-step key {step!r}'); continue
            if isinstance(v, list):
                patches.setdefault(step, {}).update({i: val for i, val in enumerate(v)})
            elif isinstance(v, dict):
                patches.setdefault(step, {}).update({int(i): val for i, val in v.items() if is_idx(i)})
                bad = [i for i in v if not is_idx(i)]
                if bad: flags.append(f'{step}: non-index keys {bad}')
            else:
                flags.append(f'{step}: unexpected value type {type(v).__name__}')
    return patches, flags

results = []
for fn in sorted(os.listdir(SRC), key=lambda x: int(x.split('.')[0]) if x.split('.')[0].isdigit() else 999):
    if not fn.endswith('.json'): continue
    pid = fn[:-5]; path = os.path.join(SRC, fn)
    d = json.load(open(path))
    patches, flags = extract(d)
    n_tests = sum(len(v) for v in patches.values())
    if flags or not any(patches.values()):
        results.append((pid, 'FLAG', sorted(patches), n_tests, flags or ['no numeric target values found'])); continue
    canon = {'problem_id': pid}
    if d.get('note') is not None: canon['note'] = d['note']
    for step in sorted(patches, key=lambda s: (int(s.split('.')[0]), int(s.split('.')[1]))):
        canon[step] = {str(i): patches[step][i] for i in sorted(patches[step])}
    shutil.copy(path, os.path.join(BK, fn))
    json.dump(canon, open(path, 'w'), indent=1)
    chk, _ = extract(json.load(open(path)))   # reload from disk + re-extract
    if chk != patches:
        shutil.copy(os.path.join(BK, fn), path)   # restore
        results.append((pid, 'VERIFY_FAIL', sorted(patches), n_tests, ['round-trip != source; restored'])); continue
    results.append((pid, 'OK', sorted(patches), n_tests, []))

print(f"{'pid':>4}  {'status':<11} {'steps':<16} {'tests':<5} flags")
for pid, st, steps, nt, fl in results:
    print(f"{pid:>4}  {st:<11} {','.join(steps):<16} {nt:<5} {'; '.join(fl)}")
ok = [r for r in results if r[1] == 'OK']; flg = [r for r in results if r[1] != 'OK']
print(f"\n规范化 OK: {len(ok)} 文件 | 需人工处理: {len(flg)} -> {[r[0] for r in flg]}")
print(f"原文件备份在: {BK}/")
