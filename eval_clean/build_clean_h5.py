"""Flat, single-pass build of the cleaned test_data.h5.

Design (replaces the layered build_h5.py -> build_h5_round2.py chain):
  - SRC     : the ORIGINAL, downloaded SciCode test_data.h5 (never modified).
  - TARGETS : ONE consolidated patch folder (all rounds merged at problem level;
              later rounds already folded in by the merge step). Only CHANGED tests
              are stored here; everything else is copied verbatim from SRC.
  - OUT     : the cleaned h5, rebuilt from scratch every run.

There is NO intermediate cleaned h5 and NO round nesting: the cleaned dataset is
fully defined by (original h5) + (this one targets/ folder). To reproduce, download
the original h5 and run this script.

Patch formats (one .json per problem in TARGETS):
  FLAT      : {"<step>": {"<test_idx>": value, ...}}                       (only changed tests)
  NESTED    : {"problem_id":.., "targets": {"<step>": [v0, v1, ...] | {"<idx>": v}}, ..}
  TRANSFORM : targets[step] == {"_transform":.., ..} when the new arrays are too large to
              inline (28.3: square the Intensity component -> |E|^2); applied in-place.
Complex numbers are encoded {"__complex__": [re, im]}.

Usage:
  python3 eval_clean/build_clean_h5.py
  # overrides: SRC=... TARGETS=... OUT=... python3 eval_clean/build_clean_h5.py
"""
import h5py, json, os, re, shutil, numpy as np

ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC     = os.environ.get('SRC',     os.path.join(ROOT, 'SciCode/eval/data/test_data.h5'))
TARGETS = os.environ.get('TARGETS', os.path.join(ROOT, 'scicode_verified/targets'))
OUT     = os.environ.get('OUT',     os.path.join(ROOT, 'scicode_verified/test_data_cleaned.h5'))
STEP = re.compile(r'^\d+\.\d+$')

assert os.path.exists(SRC), f"original h5 not found: {SRC} (download it first — see README)"
assert os.path.abspath(OUT) != os.path.abspath(SRC), "OUT must differ from SRC (never clobber the original)"
os.makedirs(os.path.dirname(OUT), exist_ok=True)


def conv(v):
    if isinstance(v, dict) and '__complex__' in v: return complex(v['__complex__'][0], v['__complex__'][1])
    if isinstance(v, list): return [conv(x) for x in v]
    return v


# --- gather ALL patches from the single consolidated folder ---
patches = {}      # step -> {test_idx(int): value}
transforms = {}   # step -> transform spec dict
for fn in sorted(os.listdir(TARGETS)):
    if not fn.endswith('.json'): continue
    d = json.load(open(os.path.join(TARGETS, fn)))
    # FLAT top-level step keys
    for step, idxs in d.items():
        if STEP.match(step) and isinstance(idxs, dict):
            patches.setdefault(step, {}).update({int(k): conv(v) for k, v in idxs.items()})
    # NESTED under "targets"
    if isinstance(d.get('targets'), dict):
        for step, vals in d['targets'].items():
            if not STEP.match(step): continue
            if isinstance(vals, dict) and '_transform' in vals:
                transforms[step] = vals
            elif isinstance(vals, list):
                patches.setdefault(step, {}).update({i: conv(v) for i, v in enumerate(vals)})
            elif isinstance(vals, dict):
                patches.setdefault(step, {}).update({int(k): conv(v) for k, v in vals.items()
                                                     if str(k).lstrip('-').isdigit()})


def write_test(f, step, testno, value, nvars):
    gp = f'{step}/test{testno}'
    if gp in f: del f[gp]
    g = f.create_group(gp)
    comps = list(value) if (nvars > 1 and isinstance(value, (list, tuple)) and len(value) == nvars) else [value]
    for i, c in enumerate(comps):
        g.create_dataset(f'var{i+1}', data=np.array(c))


# --- per-step test_cases counts from the SSOT (to trim orphan h5 targets) ---
PROB_DIR = os.path.join(ROOT, 'scicode_verified', 'problems')
SKIP_STEPS = {'13.6', '62.1', '76.3'}
step_ntc = {}
if os.path.isdir(PROB_DIR):
    for fn in os.listdir(PROB_DIR):
        if not fn.endswith('.json'):
            continue
        d = json.load(open(os.path.join(PROB_DIR, fn)))
        for s in d.get('sub_steps', []):
            step_ntc[str(s.get('step_number'))] = len(s.get('test_cases') or [])

shutil.copy(SRC, OUT)
print(f"SRC     = {SRC}")
print(f"TARGETS = {TARGETS}")
print(f"OUT     = {OUT}\n")

with h5py.File(OUT, 'a') as f:
    skey = lambda s: (int(s.split('.')[0]), int(s.split('.')[1]))
    for step in sorted(patches, key=skey):
        nvars = len([k for k in f[f'{step}/test1'].keys()])
        for idx, val in sorted(patches[step].items()):
            write_test(f, step, idx + 1, val, nvars)
    # transform-spec patches (28.3: var3 -> var3**2), applied against the copied-in original arrays
    for step in sorted(transforms, key=skey):
        spec = transforms[step]
        squared = 0
        for t in sorted([k for k in f[step] if k.startswith('test')], key=lambda t: int(t[4:])):
            g = f[f'{step}/{t}']
            if 'var3' not in g: continue
            arr = np.asarray(g['var3'][()])
            if arr.ndim == 2 and np.issubdtype(arr.dtype, np.floating):
                del g['var3']; g.create_dataset('var3', data=arr ** 2); squared += 1
        exp = spec.get('verify_corner_new_intensity')
        if exp:
            got = [float(np.asarray(f[f'{step}/test{i+1}/var3'][()]).flat[0]) for i in range(len(exp))]
            assert all(abs(a - b) < 1e-9 for a, b in zip(got, exp)), f'{step} corner mismatch: {got} != {exp}'
        print(f'  transform {step}: squared Intensity in {squared} tests (corner-check OK)')

    # --- trim orphan tests: h5 must not have more test{N} than the SSOT has test_cases ---
    trimmed = []
    for sn, ntc in sorted(step_ntc.items(), key=lambda kv: skey(kv[0])):
        if sn in SKIP_STEPS or sn not in f:
            continue
        h5tests = sorted((k for k in f[sn] if k.startswith('test')), key=lambda x: int(x[4:]))
        if len(h5tests) < ntc:
            print(f'  WARNING: {sn} has {len(h5tests)} h5 targets but {ntc} test_cases (MISSING target!)')
        for t in h5tests:
            if int(t[4:]) > ntc:
                del f[f'{sn}/{t}']
                trimmed.append(f'{sn}/{t}')
    if trimmed:
        print(f'  trimmed {len(trimmed)} orphan test target(s): {", ".join(trimmed)}')

print(f'wrote {OUT} with {len(patches)} patched steps and {len(transforms)} transform steps')

# sanity: tests added in cleaning + transform landed
with h5py.File(OUT, 'r') as f:
    for step in ['37.1', '37.2', '45.3', '79.1', '73.9']:
        if step in f:
            print(f'  {step}: tests =', sorted([k for k in f[step] if k.startswith('test')], key=lambda t: int(t[4:])))
    if '28.3' in f:
        print('  28.3 var3 corners =', [round(float(np.asarray(f[f'28.3/test{i}/var3'][()]).flat[0]), 9) for i in (1, 2, 3)])
