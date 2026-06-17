"""The bidirectional verify gate (verify-with-human invariant 4). Exits non-zero
on ANY failure — wire it as the release gate.

Checks:
  release-in-sync : on-disk problems_test.jsonl == assemble(SSOT)  (no hand edits)
  forward         : every ledger entry's `after` is the current SSOT value AND its
                    `before` was the baseline value -> catches missed/incorrect edits
  reverse         : every field that changed vs the baseline release has a matching
                    ledger entry -> catches stray/accidental edits
  coupling        : in scope=prompt, the target patch set md5 is UNCHANGED vs the
                    baseline (a prompt-only round must not touch targets/h5)
  integrity       : ast.parse every sub_step function_header and test_cases line

Baseline = the previous released state. Default: git HEAD's committed
scicode_verified/problems_test.jsonl (+ manifest.json). Override with
BASELINE_JSONL=/path and BASELINE_MANIFEST=/path.

Usage:
  python3 tools/verify.py [--round R3] [--scope prompt|full]
  # ROUND env / --round selects ledger/<round>.jsonl (optional; absent => expect 0 changes)
"""
import json, os, sys, ast, hashlib, subprocess, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VDIR = os.path.join(ROOT, 'scicode_verified')
PROB = os.path.join(VDIR, 'problems')
TARG = os.path.join(VDIR, 'targets')
JSONL = os.path.join(VDIR, 'problems_test.jsonl')
MANIFEST = os.path.join(VDIR, 'manifest.json')


def md5_bytes(b): return hashlib.md5(b).hexdigest()


def git_show(path):
    """Return committed HEAD content of a repo-relative path, or None."""
    try:
        rel = os.path.relpath(path, ROOT)
        return subprocess.check_output(['git', '-C', ROOT, 'show', f'HEAD:{rel}'],
                                       stderr=subprocess.DEVNULL)
    except Exception:
        return None


def load_jsonl_objs(text):
    return {str(o['problem_id']): o for o in (json.loads(l) for l in text.splitlines() if l.strip())}


def assemble_from_ssot():
    files = [fn for fn in os.listdir(PROB) if fn.endswith('.json')]
    objs = [json.load(open(os.path.join(PROB, fn), encoding='utf-8')) for fn in files]
    objs.sort(key=lambda o: int(o['problem_id']))
    return objs, '\n'.join(json.dumps(o, ensure_ascii=False) for o in objs) + '\n'


def deep_diff(a, b, path=''):
    """Yield (dotted_path, before, after) leaf differences between a and b."""
    if type(a) != type(b):
        yield (path, a, b); return
    if isinstance(a, dict):
        for k in dict.fromkeys(list(a.keys()) + list(b.keys())):
            yield from deep_diff(a.get(k, '<MISSING>'), b.get(k, '<MISSING>'),
                                 f'{path}.{k}' if path else k)
    elif isinstance(a, list):
        if len(a) != len(b):
            yield (path, f'<list len {len(a)}>', f'<list len {len(b)}>'); return
        for i, (x, y) in enumerate(zip(a, b)):
            yield from deep_diff(x, y, f'{path}[{i}]')
    else:
        if a != b:
            yield (path, a, b)


def get_path(obj, dotted):
    """Resolve a dotted/indexed path like 'sub_steps[2].step_description_prompt'."""
    import re
    cur = obj
    for tok in re.findall(r'[^.\[\]]+|\[\d+\]', dotted):
        if tok.startswith('['):
            cur = cur[int(tok[1:-1])]
        else:
            cur = cur[tok]
    return cur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--round', default=os.environ.get('ROUND', ''))
    ap.add_argument('--scope', default=os.environ.get('SCOPE', 'prompt'), choices=['prompt', 'full'])
    args = ap.parse_args()
    fails = []

    # ---- release-in-sync ----
    cur_objs, assembled = assemble_from_ssot()
    cur = {str(o['problem_id']): o for o in cur_objs}
    on_disk = open(JSONL, encoding='utf-8').read()
    if on_disk != assembled:
        fails.append('release-in-sync: problems_test.jsonl != assemble(SSOT) — run tools/assemble.py')

    # ---- baseline ----
    bl_jsonl = os.environ.get('BASELINE_JSONL')
    bl_text = open(bl_jsonl, encoding='utf-8').read() if bl_jsonl else (git_show(JSONL) or b'').decode('utf-8')
    if not bl_text.strip():
        print('NOTE: no baseline release found (first round / uncommitted) — '
              'reverse & coupling checks skipped, only integrity + sync run.')
        baseline = None
    else:
        baseline = load_jsonl_objs(bl_text)

    # ---- ledger ----
    ledger = []
    if args.round:
        lp = os.path.join(ROOT, 'ledger', f'{args.round}.jsonl')
        if os.path.exists(lp):
            ledger = [json.loads(l) for l in open(lp, encoding='utf-8') if l.strip()]

    # ---- diff baseline vs current ----
    changes = []  # (pid, path, before, after)
    if baseline is not None:
        for pid, co in cur.items():
            bo = baseline.get(pid)
            if bo is None:
                fails.append(f'reverse: problem {pid} not in baseline (new problem, no ledger model)')
                continue
            for p, b, a in deep_diff(bo, co):
                changes.append((pid, p, b, a))

    # ---- forward: every ledger entry landed ----
    for e in ledger:
        pid, fld = str(e['id']), e['field']
        try:
            cur_val = get_path(cur[pid], fld)
        except Exception as ex:
            fails.append(f'forward: ledger {pid}.{fld} not resolvable in SSOT ({ex})'); continue
        if e.get('verdict') != 'keep' and cur_val != e['after']:
            fails.append(f'forward: ledger {pid}.{fld} after-text not present in SSOT')
        if baseline is not None:
            try:
                bl_val = get_path(baseline[pid], fld)
                if bl_val != e['before']:
                    fails.append(f'forward: ledger {pid}.{fld} before-text != baseline (stale ledger?)')
            except Exception:
                pass

    # ---- reverse: every change has a ledger entry ----
    ledger_keys = {(str(e['id']), e['field']) for e in ledger}
    for pid, p, b, a in changes:
        if (pid, p) not in ledger_keys:
            fails.append(f'reverse: {pid}.{p} changed vs baseline but has NO ledger entry')

    # ---- coupling: prompt-only round must not touch targets ----
    if args.scope == 'prompt' and baseline is not None:
        bl_man = os.environ.get('BASELINE_MANIFEST')
        bl_man_b = open(bl_man, 'rb').read() if bl_man else git_show(MANIFEST)
        if bl_man_b:
            bl_tset = json.loads(bl_man_b).get('targets_set_md5')
            cur_man = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
            cur_tset = cur_man.get('targets_set_md5')
            if bl_tset and cur_tset and bl_tset != cur_tset:
                fails.append('coupling: scope=prompt but targets set md5 changed vs baseline')

    # ---- integrity: code fields parse ----
    for pid, o in cur.items():
        for i, ss in enumerate(o.get('sub_steps', [])):
            for fld in ('function_header', 'test_cases'):
                code = ss.get(fld)
                chunks = code if isinstance(code, list) else [code]
                for j, c in enumerate(chunks):
                    if not isinstance(c, str) or not c.strip():
                        continue
                    try:
                        ast.parse(c)
                    except SyntaxError as ex:
                        fails.append(f'integrity: {pid} sub_steps[{i}].{fld}[{j}] does not parse: {ex}')

    # ---- report ----
    print(f'scope={args.scope}  round={args.round or "(none)"}  '
          f'ledger={len(ledger)}  changes-vs-baseline={len(changes)}')
    if fails:
        print(f'\n❌ VERIFY FAILED ({len(fails)} issue(s)):')
        for m in fails:
            print('   -', m)
        sys.exit(1)
    print('\n✅ VERIFY PASSED — decided==shipped, undecided==unchanged, integrity OK')


if __name__ == '__main__':
    main()
