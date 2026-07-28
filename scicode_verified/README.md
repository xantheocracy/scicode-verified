# SciCode-Verified dataset

This directory contains the source of truth and the derived v2 release for the corrected
SciCode test benchmark.

## Release snapshot

| Item | Value |
|---|---:|
| Main problems | 64 |
| Total subproblems | 290 |
| Scored subproblems | 287 |
| Problem files changed from upstream | 63 |
| Problems with target patches | 39 |
| Dataset version | v2 |

The three unscored subproblems (`13.6`, `62.1`, and `76.3`) are official SciCode skip steps. Their
reference implementations are inserted into the cumulative program for later steps, but they are
not generated or counted.

## Files

### Source of truth

| Path | Contents |
|---|---|
| `problems/<id>.json` | Canonical prompt, background, substeps, function headers, tests, and return lines |
| `targets/<id>.json` | Corrected target values or reproducible target transforms |
| `refs/` | Reference code used by target transforms |

Edit only these source files when changing the dataset.

### Derived release artifacts

| Path | Produced by | Contents |
|---|---|---|
| `problems_test.jsonl` | `tools/assemble.py` | Flattened 64-problem evaluation dataset |
| `manifest.json` | `tools/assemble.py` | Dataset version and content hashes |
| `test_data_cleaned.h5` | `eval_clean/build_clean_h5.py` | Corrected frozen grading targets |

`test_data_cleaned.h5` is approximately 1.1 GB and is intentionally not stored in Git. Download it
from the [v2 data release](https://github.com/flyingwagner/scicode-verified/releases/tag/data):

```bash
gh release download data \
  --repo flyingwagner/scicode-verified \
  --dir scicode_verified
```

Expected HDF5 MD5:

```text
2b41a7df40ddc23ce651ec05b8ecb6f8
```

The evaluation harness refuses to run when the released JSONL or HDF5 does not match
`manifest.json`.

## Maintenance workflow

After editing the source of truth:

```bash
# Required after prompt/problem changes
python tools/assemble.py

# Required after target changes; needs upstream SciCode/eval/data/test_data.h5
python eval_clean/build_clean_h5.py

# Required before release; use the ledger round containing the change
python tools/verify.py --scope full --round <ROUND>
```

Each accepted change must also have a provenance record in `ledger/<round>.jsonl`.

The verification gate enforces:

- derived JSONL equals the per-problem source files;
- every ledger decision is present in the release;
- every release change is represented in the ledger;
- prompt-only rounds do not silently alter target data;
- executable headers and tests parse successfully.

Never edit `problems_test.jsonl`, `manifest.json`, or `test_data_cleaned.h5` by hand.
