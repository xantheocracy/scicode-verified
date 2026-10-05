# Vendored upstream SciCode files

Byte-identical copies of the minimal upstream files the evaluation harness needs,
so this repository is runnable from a plain `git clone` without cloning the
original SciCode repository. Licensed under Apache-2.0 (see `LICENSE` in this
directory, copied from upstream).

Source: the SciCode repository (upstream project
<https://github.com/scicode-bench/SciCode>), taken from a local clone at commit
`b1989980d9920dd1897c6159d31090a3f556d3d1`.

| File | md5 | Role |
|---|---|---|
| `scicode/parse/parse.py` | `6ea59d60e2d47aea1403d4668b392748` | `process_hdf5_to_tuple` — reads gold targets from the h5 during grading |
| `scicode/__init__.py` | `430455751c2c71030474a72d63291c85` | package shim (upstream file) |
| `scicode/parse/__init__.py` | (empty) | package shim |
| `eval_data/multistep_template.txt` | `5de36afe17f57d4813f0848789af3d7c` | official with-background prompt template |
| `eval_data/background_comment_template.txt` | `3a376df5a28940040ef8ec1719fecd69` | official no-background prompt template |
| `eval_data/13.6.txt`, `62.1.txt`, `76.3.txt` | see above | gold code for the three officially skipped sub-steps (injected into cumulative code, never generated or scored) |

The harness prefers a local `SciCode/` clone at the repository root when one
exists and falls back to these copies otherwise; the grading subprocess prepends
this directory to `sys.path`, so an installed `scicode` package (if any) takes
precedence.

The Inspect sandbox also includes `scicode/compare/cmp.py` and its package initializer from upstream SciCode commit `e3158ea011d4235245a547460d3688d7ccbf9900`, under the same Apache-2.0 license. The comparison module has MD5 `c64e699b4fc6d7ae822d8119934bb786`. Released test cases import `cmp_tuple_or_list` and `are_dicts_close` from this module.

Note: the upstream `test_data.h5` (~1 GB, distributed separately by upstream,
md5 `96d5d815aee54434deba01eb27646f22`) is **not** vendored. It is only needed to
reproduce the paper's *before* (original-benchmark) measurements via
`--dataset original`. The corrected benchmark released here
(`scicode_verified/test_data_cleaned.h5`) is self-contained and is the standard.
