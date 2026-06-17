# Paper Writing Guide — Cleaning and Re-Releasing SciCode

A concrete, precedent-grounded plan for writing the paper about auditing, cleaning,
and re-releasing the SciCode scientific-coding benchmark ("SciCode v2"). Every
precedent below was verified by fetching the source page (arXiv / ACL Anthology /
PMLR / NeurIPS proceedings / publisher DOI). Items that could not be fully verified
are flagged explicitly.

Internal defect statistics in this guide are pulled from our own
`review/DEFECT_REGISTRY.md` and `review/INDEX.md` (397 reviewer-confirmed defects
across 80 problems, two-round audit). Replace the placeholder numbers in the
"before/after" tables once the v2 re-eval run completes.

---

## 0. The one-sentence pitch (use this to anchor every section)

> A large fraction of apparent LLM "failures" on SciCode are artifacts of the
> benchmark's own defects — internal contradictions, desynced regenerated targets,
> method/rounding-lottery tolerances, unit traps, under-specified conventions, and
> information that lives only in hidden test code — and once these are fixed, model
> scores and rankings change, and the *remaining* failures cleanly separate into
> code-bugs vs. physics-understanding gaps.

This is the same rhetorical move that carried the three strongest precedents:
**Pervasive Label Errors** (Northcutt et al., NeurIPS 2021 D&B), **EvalPlus**
(Liu et al., NeurIPS 2023), and **SWE-bench Verified** (OpenAI). All three convert
an abstract "data quality" worry into a concrete "your leaderboard is wrong" result.

---

## 1. Recommended title options

Primary:
- **"SciCode-Clean: Auditing and Re-Releasing a Scientific Coding Benchmark, and What It Reveals About LLM Failures"**

Alternatives (pick by emphasis):
- *"How Much of SciCode Measures the Model? A Defect Audit and Corrected Re-Release"* (eval-validity emphasis)
- *"Code Bugs vs. Physics Gaps: Disentangling Model and Benchmark Errors in SciCode"* (the novel-lens emphasis)
- *"When the Benchmark Is Wrong: A Taxonomy of Defects in SciCode and Their Effect on Model Rankings"* (taxonomy emphasis)

Naming convention precedent: corrected re-releases are conventionally named
`<Benchmark>-Redux` / `-Plus` / `-Verified` / `-Pro` (MMLU-Redux, HumanEval+/EvalPlus,
SWE-bench Verified, MMLU-Pro). Using `SciCode-Clean` or `SciCode v2` signals genre
membership to reviewers immediately.

---

## 2. Abstract sketch (≈200 words, fill the bracketed numbers)

> Benchmarks are only as trustworthy as their ground truth. SciCode (NeurIPS 2024
> D&B) is a widely used scientific-coding benchmark in which an LLM implements
> multi-step physics/math/chemistry/biology routines that are scored against hidden
> numeric targets stored in an HDF5 file. We conduct a systematic two-pass expert
> audit of all 80 main problems (338 subproblems) and find **[397]** confirmed
> defects spanning **[6]** field categories: internal contradictions between the
> problem text and the hidden target's convention; regenerated targets never
> resynced with the prompt; "method/rounding-lottery" test tolerances that admit
> only the reference integrator/RNG and reject correct alternatives; unit traps;
> under-specified conventions (ddof, branch cuts, neighbor ordering, reference
> planes); unconvergeable or wrong frozen targets; and missing-information traps
> where the required formula appears only in invisible test code. We release a
> cleaned version (SciCode v2) and re-evaluate **[N]** models. We find that
> **[XX]%** of original sub-step failures by the strongest models were caused by
> dataset defects rather than model error, that model **[rankings change / ordering
> of the top-3 shifts]**, and that genuine failures partition into *code-bugs*
> (correct physics, buggy code) and *physics-understanding gaps*. We further show
> that scores are highly sensitive to harness choices (per-step timeout,
> gold-injection, prompt trimming). We release the corrected data, the audit logs,
> the defect taxonomy, and the re-eval harness.

---

## 3. Section-by-section outline (tailored to our work)

The structure below is the consensus skeleton across EvalPlus, MMLU-Redux,
MMLU-Pro, SWE-bench+/Verified, and Pervasive Label Errors. Each precedent does the
same seven moves: motivate via eval validity → taxonomize defects → describe a
reproducible audit method → describe the cleaning protocol → validate that clean is
better → show the conclusion changes (rankings) → discuss limits + release.

### 1. Introduction
- Lead with eval validity, not "we found bugs." Frame: leaderboards drive model
  selection and research direction; if the ground truth is wrong, the leaderboard
  measures the wrong thing. Cite the construct-validity literature (Raji et al.;
  Bowman & Dahl; Jacobs & Wallach) and the "data work is undervalued" framing
  (Sambasivan et al., *Data Cascades*).
- State that this is *not* a SciCode takedown — SciCode is valuable precisely
  because it is hard and scientist-authored; that is *why* it deserves cleaning.
  (Mirror "Are We Done with ImageNet?" — they conclude ImageNet stays useful *if*
  relabeled.) This pre-empts the "you're trashing other people's work" reviewer.
- Contributions list (4–5 bullets, see §4).
- Headline number in the first column-inch: "**[XX]%** of failures were dataset
  bugs," analogous to EvalPlus's "scores drop up to ~29 points."

### 2. Background: the SciCode benchmark and its eval harness
Verified facts to state precisely (source: arXiv:2407.13168 + the GitHub harness):
- 80 main problems → 338 subproblems; 5 domains (Physics, Math, Materials, Biology,
  Chemistry), 16 subdomains; median 3 subproblems/problem, max 15.
- Split: 15 main / 50 sub = dev; 65 main / 288 sub = test.
- Each subproblem ships an optional scientist-written **background**, a gold
  reference solution, and test cases. Targets/test data live in
  `eval/data/test_data.h5`, read via `process_hdf5_to_tuple`.
- **Two eval modes:** `with_background` vs `without_background`. Critically (and a
  point our registry stresses): a defect in the *background* field only contaminates
  `with_background` mode, whereas defects in description / function contract / tests
  / targets contaminate **both** modes. Make this distinction early; it scopes every
  later count.
- Official per-step timeout is **1800 s**; main-problem solved only if **all**
  subproblems pass **and** the integrated main solution passes; prior steps can be
  injected as **gold** or **model-generated**.
- Reported original scores (gold-prior): best is Claude 3.5 Sonnet 26.0% sub /
  4.6% main (no-bg), 35.4% / 12.3% (with-bg).

### 3. Threats to validity in SciCode (motivating examples)
Open with 2–3 worked vignettes from our registry that a reader can verify by eye —
this is the EvalPlus "show one concrete wrong ground-truth" move, which is far more
convincing than aggregate counts alone. Candidates from the registry:
- A docstring/background that states `f(x)=½xᵀAx − xᵀAx` where the second term must
  be `xᵀb` (problem 1) — an internal contradiction visible in the text.
- A target where `d` parameter provably has no effect on the gold intensity
  (problem 2.1: test 2 vs test 3 differ only by float noise) — under-specified
  convention baked into the target.
- A "missing-information trap" where the observation-plane position needed to
  produce the gold target appears nowhere in prompt/background/docstring (problem
  2.1) — the model cannot in principle derive the target.
- A weak test where `np.zeros`, `np.ones`, and wrong-shape arrays *all* pass
  (problem 2.1 test 4) — a test that fails to discriminate.

### 4. Defect taxonomy
We already have a working code (D2 missing-info, D4 under-specified convention,
D7 wrong target, D8 weak test, D10 documentation contradiction, D12 dependency
drift, …). Present it as a 2D taxonomy because that is our genuine contribution
beyond prior single-axis taxonomies:
- **Axis A — defect type** (the D-codes), each with a one-line definition + a
  canonical example.
- **Axis B — affected field × eval mode** (description / function contract /
  background / test cases / target / dependency), with the with-bg-only vs
  all-modes scoping.
Include the registry's summary table verbatim (counts per field × severity 🔴/🟡/⚪).
Compare explicitly to the MMLU-Redux taxonomy (Bad Question Clarity, Bad Options
Clarity, No Correct Answer, Multiple Correct Answers, Wrong Ground Truth) and the
SWE-bench+ taxonomy (solution leakage, weak tests) to show ours subsumes and
extends them for a *numeric, multi-step, execution-scored* setting — which is the
gap none of the MCQ-oriented audits cover.

Call out two SciCode-specific defect classes that have *no* precedent analogue and
are therefore the freshest contributions:
- **Method/rounding lottery**: a tolerance so tight that only the reference
  integrator/RNG/quadrature passes; a mathematically correct alternative fails.
  This is the numeric-execution analogue of EvalPlus's "insufficient tests," but
  inverted — here the test is *over*-fit to one implementation, not too weak.
- **Desynced regenerated target**: targets regenerated at some point but never
  re-synced with the evolving problem text (our `h5 build bug` finding is the
  mechanism: nested-format patches never reached the eval h5).

### 5. Audit methodology
- Two-pass design: per-problem deep audit (80 problems), then an adversarial
  fresh-agent recheck that only retains *reconfirmed* defects (mirrors Pervasive
  Label Errors' two-stage detect→human-validate, and MMLU-Redux's expert
  cross-check against the original source). Report the false-positive rate
  (registry: 1 false positive, 1 disputed out of 398) — this directly answers the
  "your detector is just noise" objection.
- For numeric defects, the audit *executes probes*: load the actual h5 targets,
  run candidate-correct and candidate-wrong implementations through the official
  step test, and record which pass. This is what lets us distinguish "weak test"
  (wrong code passes) from "lottery test" (correct alt fails) from "wrong target"
  (gold itself is unreachable). Emphasize that classification is grounded in
  execution, not opinion — this is the construct-validity defense.
- State annotator expertise (scientist/physics background) and per-domain coverage,
  echoing GPQA's and SWE-bench Verified's "experts did the review" credibility.
- Report inter-rater / second-pass agreement if available. NOTE: MMLU-Redux and
  GPQA were both dinged for not reporting a kappa; we should report ours or
  explicitly explain the adversarial-recheck design as the agreement substitute.

### 6. The cleaning protocol
- State the principle: minimal, defensible edits. For tolerance defects, **loosen
  minimally** — admit only genuine method ambiguity, still reject wrong answers
  (our tolerance-loosening principle; e.g. period `< 0.11`, energies `atol=1e-5`).
  This is the single most important pitfall-avoidance argument (see §8).
- Distinguish the four fix actions: fix the text to match the target; fix/regenerate
  the target to match the text; loosen/replace a lottery test; quarantine
  unconvergeable/wrong problems. Report counts per action.
- Decision rule for "fix vs leave," with the leakage guardrail: a clarification is
  legitimate only if it specifies a *convention* the task always presupposed (ddof,
  branch cut, neighbor order) — never if it reveals the algorithm the model was
  supposed to derive. Worked example of both a legitimate and a rejected fix.
- Reproducibility of the rebuild: the h5 build pipeline, schema purity checks, and
  the QA review pass (no solution/target leakage into prompts).

### 7. Results — does cleaning change conclusions?
This is the load-bearing section. Three subsections, each mirroring a precedent:
- **7.1 Failures that were dataset bugs (the headline).** For each model, partition
  original sub-step failures into {dataset-defect-caused, genuine}. Report the
  fraction. (EvalPlus-style: the flaw is *consequential*.)
- **7.2 Score and ranking change after cleaning.** Original vs v2 sub-step and
  main-problem accuracy per model, both eval modes. If any pairwise ordering flips,
  feature it prominently (Pervasive Label Errors' ranking-reversal is the
  canonical convincer). If nothing flips, report magnitude of score change and that
  *relative* gaps shrink/grow — still a valid finding ("Are We Done with ImageNet?"
  made shrinking gaps the result).
- **7.3 The code-bug vs physics-gap lens (novel contribution).** Of the *genuine*
  failures, classify each as CODE-BUG (missing imports, off-by-one, shape/dtype,
  un-vectorized → timeout) vs PHYSICS-UNDERSTANDING (e.g., could not derive the 2D
  Lindhard closed form). Per-model and per-domain breakdown. This is the lens no
  prior benchmark-cleaning paper offers, and it reframes the cleaned benchmark as a
  *diagnostic*, not just a corrected scoreboard.

### 8. Harness sensitivity (secondary contribution)
Show that eval-harness choices materially move scores, independent of model quality:
- Per-step timeout 300 s vs official 1800 s (un-vectorized-but-correct code times
  out at 300 s → counted wrong).
- Gold-injection vs model-generated prior steps.
- Prompt trimming.
Precedent: *The Benchmark Lottery* (Dehghani et al.) and Bowman & Dahl both argue
configuration choices masquerade as algorithmic progress. Frame this as: even with
clean data, the *harness* is a validity threat, and report exact, reproducible
settings (the construct-validity hygiene reviewers reward).

### 9. Related work
Group into: (a) label-error/test-set-quality (Northcutt et al.; Confident Learning;
ReaL; Tsipras et al.; CIFAR-N; AUM); (b) benchmark errata & corrected re-releases
(MMLU-Redux, MMLU-Pro, EvalPlus, SWE-bench+/Verified, GSM-Symbolic, GSM1k);
(c) contamination (positioned as a *different* failure mode — we audit correctness,
not leakage — but cite to show we are aware); (d) eval validity & documentation norms
(Raji et al.; Bowman & Dahl; Jacobs & Wallach; Datasheets; Data Cards). Explicitly
state the gap: prior cleaning work is overwhelmingly MCQ (MMLU) or
single-function code with discrete pass/fail (HumanEval); none addresses
*multi-step, numeric-target, execution-scored scientific* benchmarks where the
defect modes (lottery tolerances, unit traps, desynced numeric targets) are unique.

### 10. Limitations
- Audit is expert-judgment-based; some D4/convention calls are debatable.
- We re-evaluated [N] models, not all; rankings beyond the tested set unknown.
- Cleaning could itself introduce errors; we mitigate with the adversarial recheck
  and release all logs for community correction.
- Quarantined problems shrink the benchmark; we report results both with and without
  them.

### 11. Ethics, credit, and release
- Credit original SciCode authors prominently; frame as collaborative stewardship
  (offer to upstream fixes). Cite SWE-bench Verified as precedent that an
  independent corrected subset is a recognized, non-adversarial contribution.
- Release: corrected dataset, full audit logs, defect registry, taxonomy codebook,
  re-eval harness, and the rebuild scripts. Provide a Datasheet/Data Card for v2
  and (for NeurIPS D&B) Croissant metadata + an explicit license.

---

## 4. Key arguments / contributions a reviewer will want

State these explicitly as the contributions list:
1. **A defect-validity argument**: quantified evidence that a measurable fraction of
   SciCode failures are benchmark errors, not model errors — threatening the
   benchmark's construct validity.
2. **A 2D defect taxonomy** (type × affected-field-and-mode) that subsumes prior
   MCQ/code taxonomies and adds numeric-execution-specific classes (method/rounding
   lottery, desynced numeric target, unit trap).
3. **A reproducible, execution-grounded audit method** with an adversarial recheck
   and a reported false-positive rate.
4. **Quantified before/after**: defects per field/severity, fraction of failures
   that were dataset bugs, and any ranking change after cleaning.
5. **The code-bug vs physics-gap diagnostic lens** — a novel way to read what a
   *cleaned* scientific-coding benchmark actually measures.
6. **Harness-sensitivity findings** — scores move materially with timeout /
   gold-injection / trimming, an orthogonal validity threat.
7. **A cleaned, fully documented re-release** with logs and harness.

Evidence each contribution needs (see §5 for the exact table/figure list).

---

## 5. Tables & figures to produce

Tables:
- **T1. Defect taxonomy codebook** — D-code, definition, one canonical example,
  count, severity. (Anchor of §4.)
- **T2. Defects by affected field × eval mode × severity** — the registry's summary
  table (97 description, 108 contract, 61 background, 107 test, 22 target, 2 dep).
- **T3. Cleaning actions** — fix-text / fix-target / loosen-test / quarantine,
  with counts and a couple of before→after diffs.
- **T4. Score table** — per model × {with-bg, no-bg} × {sub-step %, main %} ×
  {original, v2}. Bold any ordering flip.
- **T5. Failure attribution** — per model: % of original failures that were
  dataset-defect vs genuine; and within genuine, CODE-BUG vs PHYSICS-GAP.
- **T6. Harness sensitivity** — score under 300 s vs 1800 s timeout, gold vs
  generated prior steps, trimmed vs full prompt.

Figures:
- **F1. Worked-example panel** — 2–3 screenshots/snippets of real defects (the
  EvalPlus/labelerrors.com "show, don't tell" move). The `f(x)` contradiction and
  the all-arrays-pass weak test are visually self-evident.
- **F2. Stacked bar of failure attribution** per model (dataset-bug / code-bug /
  physics-gap) — the paper's signature figure; makes contribution #5 instantly
  legible.
- **F3. Ranking before vs after** (slopegraph) — directly echoes Pervasive Label
  Errors' ranking-reversal figure.
- **F4 (optional). Reasoning-token cost** — single-shot "mentally execute"
  code-gen vs agentic execute-and-debug, motivating the harness discussion.

---

## 6. Target venues & submission norms

Primary:
- **NeurIPS Datasets & Benchmarks Track** (now folding into the *Evaluations &
  Datasets* track) — SciCode itself was published here, so a corrected re-release is
  squarely in scope and reviewers expect it. Requirements to satisfy up front:
  dataset publicly accessible without contacting authors; open-source code; explicit
  license (CC BY 4.0 / CC0 typical); reproducibility; **Croissant** machine-readable
  metadata (auto-generated if hosted on HF/Kaggle/OpenML); and increasingly RAI
  Croissant fields. Provide a Datasheet (Gebru et al.) / Data Card (Pushkarna et al.).
  Source: NeurIPS 2024/2025 Call for Datasets & Benchmarks + FAQ.

Strong secondary / alternative:
- **ICLR / ACL / EMNLP main or Findings** — MMLU-Redux (NAACL), EvalPlus (NeurIPS
  main), GSM-Symbolic (ICLR) all landed at top ML/NLP venues, so a strong version is
  not confined to a D&B track.
- **Workshops on evaluation** (e.g., NeurIPS/ICLR eval & data-centric workshops,
  DMLR) for an early/short version if timing is tight.

Reproducibility/release checklist (do all of these — D&B reviewers grade on them):
- Public corrected dataset + license + Datasheet/Data Card + Croissant.
- Full audit logs and defect registry (so the community can contest fixes).
- Re-eval harness pinned to exact versions; document the timeout and gold-injection
  settings used.
- Explicit, prominent credit to the original SciCode authors.

---

## 7. Reviewer-pushback / pitfalls checklist

For each likely pushback, the pre-emption (and where in the paper it lives):

1. **"Your 'fixes' are just opinions / your detector is noisy."**
   → Execution-grounded audit + adversarial fresh-agent recheck retaining only
   reconfirmed defects + reported false-positive rate (§5). Mirror Pervasive Label
   Errors' detect→human-validate and report the ≈agreement.

2. **"You're overfitting fixes to specific models."**
   → Fixes are derived from the *text↔target↔test* internal consistency, never from
   "model X failed here." Show that a fix is justified by a defect that exists
   independent of any model (e.g., the `f(x)` contradiction; a target the prompt
   cannot in principle determine). Re-evaluate models *not* used to find defects to
   show fixes generalize. (Biggest single risk — give it its own paragraph.)

3. **"Clarifying defeats the test's purpose / you leaked the answer."**
   → The leakage guardrail (§6): clarify only presupposed *conventions* (ddof, branch
   cut, neighbor order, reference plane), never the algorithm to be derived. Show one
   rejected fix that *would* have leaked and why we declined it.

4. **"How do we know it's a benchmark defect and not a model shortcoming?"**
   → Operational test: a defect is something where a *correct* reference
   implementation (or a provably-equivalent alternative) fails, OR the target is not
   determined by the visible task, OR the text internally contradicts the target.
   A model shortcoming is when the visible spec is self-consistent and a correct
   solution passes. State this rule and classify every defect by it.

5. **"Loosening tolerances lets wrong answers through."**
   → Tolerance-loosening principle: loosen minimally to admit only genuine method
   ambiguity while still rejecting wrong answers; show, by probe, that wrong
   implementations still fail under the loosened test (§6).

6. **"This is just trashing SciCode."**
   → Stewardship framing + ImageNet-relabeling precedent (benchmark stays valuable
   *because* it's cleaned); credit original authors; offer to upstream.

7. **"Rankings didn't flip, so who cares?"**
   → Even absent a flip, report the magnitude of score correction, the
   dataset-bug fraction of failures, and gap shrinkage — "Are We Done with ImageNet?"
   built its result on shrinking gaps, not flips.

8. **"No statistical power / N too small."**
   → Report CIs on per-model deltas; acknowledge 65-problem test split limits power
   (cite Card et al., *With Little Power…*); avoid over-claiming small flips.

9. **"Contamination, not correctness, is the real issue."**
   → Scope explicitly: we audit *correctness/specification*, a distinct and
   under-studied failure mode; cite the contamination literature to show awareness
   and position as complementary.

Additional self-imposed guardrails:
- Don't claim a "convention" defect if a *prior* cumulative-context step already
  establishes that convention (our D4 calibration lesson) — over-strict audits
  inflate counts and invite pushback.
- Keep the cleaned set and the audit findings in separate artifacts so reviewers can
  check fixes against evidence.

---

## 8. Annotated bibliography (verified)

URLs verified by fetching unless marked. Use these as the citation backbone.

### A. Label errors & test-set quality (the "your ground truth is wrong" canon)
- **Northcutt, Athalye, Mueller — Pervasive Label Errors in Test Sets Destabilize
  Machine Learning Benchmarks.** NeurIPS 2021 Datasets & Benchmarks.
  https://arxiv.org/abs/2103.14749 · demo https://labelerrors.com
  *≥3.3% avg test-set label errors across 10 benchmarks (~6% ImageNet val);
  correcting labels flips model rankings. Two-stage detect (confident learning) →
  crowd-validate. The canonical ranking-reversal argument.*
- **Northcutt, Jiang, Chuang — Confident Learning: Estimating Uncertainty in Dataset
  Labels.** JAIR 2021. https://arxiv.org/abs/1911.00068 ·
  DOI https://doi.org/10.1613/jair.1.12125 · `cleanlab`.
  *The method engine behind the above: jointly estimate noisy↔true label
  distribution; prune/count/rank.*
- **Beyer, Hénaff, Kolesnikov, Zhai, van den Oord — Are We Done with ImageNet?**
  2020. https://arxiv.org/abs/2006.07159 (arXiv preprint; **no formal venue found**).
  *Re-annotates ImageNet val ("ReaL", multi-label); recent accuracy gains shrink
  under cleaner labels. Use for the "benchmark stays useful if relabeled" framing
  and "shrinking gaps are a result" argument.*
- **Tsipras, Santurkar, Engstrom, Ilyas, Madry — From ImageNet to Image
  Classification.** ICML 2020, PMLR 119:9625–9635.
  https://arxiv.org/abs/2005.11295 · https://proceedings.mlr.press/v119/tsipras20a.html
  *Critiques the dataset-creation pipeline itself (annotators only validate one
  proposed label). Precedent for "the construction process injects systematic error."*
- **Wei, Zhu, Cheng, Liu, Niu, Liu — CIFAR-10N/CIFAR-100N.** ICLR 2022.
  https://arxiv.org/abs/2110.12088 *Real human label noise is instance-dependent.*
- **Pleiss, Zhang, Elenberg, Weinberger — Identifying Mislabeled Data using AUM.**
  NeurIPS 2020. https://arxiv.org/abs/2001.10528 *Complementary detector; calibrate
  threshold by inserting known-mislabeled samples — design echo for our recheck.*
- **Shankar, Roelofs, Mania, Fang, Recht, Schmidt — Evaluating Machine Accuracy on
  ImageNet.** ICML 2020, PMLR 119. https://proceedings.mlr.press/v119/shankar20c.html
  *(partially verified — PMLR listing, abstract not fetched). Multi-label human
  re-annotation; single-label top-1 underestimates accuracy.*

### B. Benchmark errata & corrected re-releases (closest genre precedents)
- **Liu, Xia, Wang, Zhang — Is Your Code Generated by ChatGPT Really Correct?
  (EvalPlus / HumanEval+).** NeurIPS 2023.
  https://arxiv.org/abs/2305.01210 ·
  https://proceedings.neurips.cc/paper_files/paper/2023/hash/43e9d647ccd3e4b7b5baab53f0368686-Abstract-Conference.html
  · https://github.com/evalplus/evalplus
  *MOST DIRECTLY ANALOGOUS. Augmented HumanEval tests ×80 (9.6→764 tests/problem),
  MBPP ×35; pass@k drops up to ~19–29 points across 26 models; **fixed 18 wrong
  ground-truth solutions (~11% of HumanEval tasks).** NOTE: the "80" figure is the
  test multiplier, NOT a count of wrong solutions — do not conflate.*
- **Gema et al. — Are We Done with MMLU? (MMLU-Redux).** NAACL 2025, pp. 5069–5096.
  https://arxiv.org/abs/2406.04127 · https://aclanthology.org/2025.naacl-long.262/
  *Re-annotated 5,700 questions; ~6.49% error rate (57% in Virology). Hierarchical
  taxonomy: Question Assessment (clarity) + Ground Truth Verification (no/multiple/
  wrong answer). NOTE: reports no kappa — we should do better.*
- **Wang et al. — MMLU-Pro.** NeurIPS 2024 D&B (Spotlight).
  https://arxiv.org/abs/2406.01574 · https://github.com/TIGER-AI-Lab/MMLU-Pro
  *Harder + more robust: removed trivially-easy items, 4→10 options; accuracy drops
  16–33%; prompt sensitivity falls; CoT now helps. Precedent for "robustness
  improved" as a validity argument.*
- **OpenAI — Introducing SWE-bench Verified.** Blog (NOT peer-reviewed).
  https://openai.com/index/introducing-swe-bench-verified/
  *93 developers reviewed; 68.3% of sampled tasks removed → curated 500-task subset.
  Strongest precedent that expert manual cleaning of someone else's benchmark is a
  legitimate, citable contribution.*
- **Aleithan et al. — SWE-Bench+.** 2024. https://arxiv.org/abs/2410.06992
  *32.67% solution leakage in issue text; 31% weak/insufficient tests; agent
  resolution 12.47%→3.97% after filtering. Precedent for leakage + weak-test
  taxonomy and "headline numbers collapse after cleaning."*
- **Liang, Garg, Zilouchian Moghaddam — The SWE-Bench Illusion.** 2025.
  https://arxiv.org/abs/2506.12286 *Memorization probes; in- vs out-of-benchmark gap.*
- **Mirzadeh et al. — GSM-Symbolic.** ICLR 2025. https://arxiv.org/abs/2410.05229
  *Template-perturbed GSM8K; variance across instantiations; GSM-NoOp (one inert
  clause) drops accuracy up to 65%. Precedent for controlled perturbation isolating
  brittleness — relevant to our method/rounding-lottery argument.*
- **Zhang et al. (Scale AI) — A Careful Examination of LLM Performance on Grade
  School Arithmetic (GSM1k).** NeurIPS 2024 D&B. https://arxiv.org/abs/2405.00332
  *Distribution-matched unseen twin of GSM8K. NOTE: v1 said "up to 13%" drop; current
  abstract says "up to 8%" (r²=0.36) — cite the current number.*

### C. Construct validity & "is our evaluation valid?" critiques
- **Raji, Bender, Paullada, Denton, Hanna — AI and the Everything in the Whole Wide
  World Benchmark.** NeurIPS 2021 D&B. https://arxiv.org/abs/2111.15366
- **Bowman & Dahl — What Will it Take to Fix Benchmarking in NLU?** NAACL 2021.
  https://arxiv.org/abs/2104.02145 *(criteria confirmed via Anthology; PDF fetch was
  corrupted — verify the four criteria before quoting verbatim).* Four criteria:
  validity, reliable annotation, statistical power, disincentivize biased models.
- **Jacobs & Wallach — Measurement and Fairness.** FAccT 2021.
  https://arxiv.org/abs/1912.05511 *Construct reliability/validity framework for ML
  measurement — cite for the validity vocabulary.*
- **Dehghani et al. — The Benchmark Lottery.** 2021. https://arxiv.org/abs/2107.07002
  *Rankings shift with task/split/config choices — backbone for our harness section.*
- **Card et al. — With Little Power Comes Great Responsibility.** EMNLP 2020.
  https://arxiv.org/abs/2010.06595 *Statistical power neglect; cite for the
  small-N/CIs limitation.*
- **Rein et al. — GPQA.** COLM 2024. https://arxiv.org/abs/2311.12022
  *Positive example of expert validation; expert acc 65%→74% post-correction. NOTE:
  no single IAA coefficient in the abstract.*
- **Liao, Taori, Raji, Schmidt — Are We Learning Yet? (meta-review).** NeurIPS 2021
  D&B. https://openreview.net/forum?id=mPducS1MsEK *Internal vs external validity
  taxonomy across 107 surveys.*

### D. Contamination / leakage (complementary failure mode — cite for awareness)
- Deng et al. — Investigating Data Contamination. NAACL 2024. https://arxiv.org/abs/2311.09783
- Yang et al. — Rephrased Samples (Rethinking Benchmark & Contamination). https://arxiv.org/abs/2311.04850
- Jacovi et al. — Stop Uploading Test Data in Plain Text. EMNLP 2023. https://arxiv.org/abs/2305.10160
- Riddell, Ni, Cohan — Quantifying Contamination in Code Generation. ACL 2024. https://arxiv.org/abs/2403.04811
- Sainz et al. — NLP Evaluation in Trouble. Findings of EMNLP 2023. https://arxiv.org/abs/2310.18018
- Golchin & Surdeanu — Time Travel in LLMs. ICLR 2024. https://arxiv.org/abs/2308.08493
- Jain et al. — LiveCodeBench. ICLR 2025. https://arxiv.org/abs/2403.07974 *(contamination-resistant date-stamped code eval).*

### E. Documentation & governance norms (release section)
- **Gebru et al. — Datasheets for Datasets.** CACM 2021. https://arxiv.org/abs/1803.09010 · DOI 10.1145/3458723
- **Bender & Friedman — Data Statements for NLP.** TACL 2018. https://aclanthology.org/Q18-1041/
- **Mitchell et al. — Model Cards for Model Reporting.** FAccT 2019. https://arxiv.org/abs/1810.03993
- **Pushkarna, Zaldivar, Kjartansson — Data Cards.** FAccT 2022. https://arxiv.org/abs/2204.01075
- **Sambasivan et al. — "Everyone wants to do the model work, not the data work":
  Data Cascades.** CHI 2021. https://dl.acm.org/doi/10.1145/3411764.3445518
  *THE citation for "why dataset cleaning is undervalued" — use in the intro.*
- **NeurIPS Datasets & Benchmarks Track — Call & FAQ** (release requirements:
  accessibility, license, reproducibility, Croissant metadata).
  https://neurips.cc/Conferences/2024/CallForDatasetsBenchmarks ·
  https://neurips.cc/Conferences/2025/DatasetsBenchmarks-FAQ
- **DataPerf** (NeurIPS 2023 D&B) https://arxiv.org/abs/2207.10062 ·
  **DataComp** (NeurIPS 2023 D&B) https://arxiv.org/abs/2304.14108
  *(both search-verified, not individually fetched) — cite for the data-centric
  framing.*

### F. The benchmark under study
- **Tian et al. — SciCode: A Research Coding Benchmark Curated by Scientists.**
  NeurIPS 2024 D&B. https://arxiv.org/abs/2407.13168 ·
  https://github.com/scicode-bench/SciCode · https://scicode-bench.github.io/ ·
  HF: SciCode1/SciCode. *(structure, 1800s timeout, gold-injection, scoring, scores
  all verified from arXiv HTML + GitHub harness source).*

---

## 9. Verification caveats (carry into the manuscript)

- **EvalPlus**: it fixed **18 (~11%)** wrong HumanEval solutions; "80" is the test
  multiplier — do not conflate.
- **GSM1k**: cite "up to **8%**" (current abstract), note the stale "13%" that
  secondary sources repeat.
- **MMLU-Redux / GPQA**: report **no kappa / no single IAA coefficient** — don't
  attribute agreement stats you can't source, and present our recheck as our
  agreement mechanism.
- **SWE-bench Verified** is an **OpenAI blog post**, not a peer-reviewed paper —
  cite as such.
- **"Are We Done with ImageNet?"** has **no formal peer-reviewed venue** (arXiv only).
- **Bowman & Dahl** four criteria confirmed via Anthology, not from a clean PDF fetch
  — re-verify before quoting verbatim.
- **DataPerf / DataComp / Shankar et al.** were search-/listing-verified, not
  individually fetched.
- All **SciCode** structural facts and the **1800 s timeout** were directly verified
  against arXiv:2407.13168 HTML and the GitHub harness source.
- Internal numbers (397 defects; field/severity breakdown; false-positive count) are
  from `review/DEFECT_REGISTRY.md` / `review/INDEX.md` as of this writing — refresh
  the before/after eval numbers (T4–T6, F2–F3) once the v2 re-eval completes.
