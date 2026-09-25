# SIH 26170 · Module B — the complete guide

**Everything from scratch: the problem, the data, the method, the research, the
results, the decisions, and the limitations that are carried into the freeze.**
*(Subtitle corrected 19 Sep, round 2: it read "and what is still open". No technical
decision about current-release behaviour is open — D11 was the last one and it closed
on 19 Sep. What remains is a set of measured limitations, and future work is parked in
`docs/FUTURE_RELEASE_ITEMS.md`.)*

| | |
|---|---|
| Problem statement | SIH 2026 · PS **26170** · *AI-Driven Anomaly Detection in Component Burn-In & Screening* · posed by **ISRO** · Software category · Smart Automation theme |
| Module | **B** — early 168 h drift forecasting |
| Owner | **Nirmik** |
| Dataset | **`SIH26170-FINAL-01`** · generator `v4-final1` · split `LOTSPLIT-05` |
| Package | `Desktop\SIH26170_ModuleB\08_final_01` |
| Status | **FROZEN 20 Sep 2026** on a recorded team sign-off; the one-shot holdout run is **spent** (1,343 rows / 18 lots). Everything below §8 describes the work that led to that freeze and is unchanged by it |
| Results quoted from | the recorded run of **18 Sep 2026**, config digest `8d0621941f86fbb8…` |
| Guide written | 19 Sep 2026 |
| **Revision** | **R1, 19 Sep 2026** — independent adversarial review adjudicated. Findings F1, F3, F5, F6, F7, A1, A2 accepted; F2 accepted as a wording correction; F4 accepted and D11 closed. Stage 9 re-run as a corrective run; §15 numbers superseded. See `docs/ROUND1_ADJUDICATION.md`. |

---

## 0. How to read this, and the provenance rules

This is the single document for Module B. It is written so that someone who has
never seen the project can follow it end to end, and so that someone who has can
check any number against a file.

Four rules govern every figure in it:

1. **FINAL-01 only.** Every result is computed on `SIH26170-FINAL-01`. The earlier
   mock datasets (`SIH26170-MOCK-02`, Mock v1) are **excluded entirely** — different
   seed, different split, different drift shape, one renamed column. Quoting a mock
   number against FINAL-01 is the single easiest way to publish something untrue.
2. **Candidate V1 appears only as the labelled before-state.** It is not a mock; it
   is the previous candidate release and it is the reason the model configuration
   is frozen. Where a Candidate V1 number appears it is marked *(Candidate V1)* and
   it is never mixed into a FINAL-01 table.
3. **Nothing was re-run to write this.** All figures come from the recorded 18 Sep
   run whose inputs are hashed in `results/00_input_hashes.csv`. The code may have
   moved since; a document that mixes a fresh run with an old one puts two versions
   of the same number into circulation.
4. **Two MAE statistics exist and are never used interchangeably.** *Row-weighted
   pooled* MAE (`results/03_cv_metrics.csv`) weights every component equally.
   *Macro-lot* MAE (`results/03_paired_lot_test.csv`) weights every lot equally.
   They differ slightly because lots are not the same size. Each table below says
   which it is.

5. **Corrected numbers carry their own provenance.** Where a review found a
   metric that measured the wrong quantity, the corrected figure is labelled as a
   **corrective run** and the superseded figure is kept in `results/` under its
   own name. Nothing is presented as though the 18 Sep run had produced the
   corrected value.

Anything this guide does not know, it says it does not know.

---

## 1. The problem, and where Module B sits

### 1.1 Burn-in in one paragraph

Burn-in (also environmental stress screening, ESS) runs a batch of components hot
and powered for a fixed period so that parts with latent manufacturing defects fail
or drift before they reach a customer — or, for ISRO, before they reach a launch
vehicle. Electrical parameters are measured at checkpoints. A part whose parameters
wander is suspect even if it never crosses a datasheet limit. The expensive failure
mode is the part that *passes* every static limit and still degrades.

### 1.2 The measurement structure

Every component is measured at four epochs: **0 h, 24 h, 96 h, 168 h**, on six
parameters:

| Parameter | Unit | What it is |
|---|---|---|
| `IDDQ` | µA | quiescent supply current — the classic CMOS defect indicator |
| `Input_Leakage_Current` | µA | leakage into an input pin |
| `Active_Supply_Current` | µA | switching current, characterised at 1 MHz, one gate, no external load (`I ≈ Cpd·VCC·f`) — **distinct from IDDQ** |
| `Propagation_Delay` | ns | input-to-output delay, `tpd` |
| `Output_Rise_Time` | ns | output transition time, low→high |
| `Output_Fall_Time` | ns | output transition time, high→low |

Three device variants, all `DIGITAL_CMOS`, each anchored to a real TI NAND gate:

| Variant | Reference device | VCC |
|---|---|---|
| `CMOS_A` | TI SN74HC00 | 4.5 V |
| `CMOS_B` | TI SN74AHC00 | 5.0 V |
| `CMOS_C` | TI SN74LVC00A | 3.3 V |

One row = one physical component. Components are grouped into manufacturing **lots**,
and a lot is the unit that matters: parts from one lot share process conditions, so
they are not independent of one another.

### 1.3 The two modules

| | Module A — Riddhi | Module B — Nirmik |
|---|---|---|
| Question | which components are outliers *relative to their own lot*, across parameters | what will each component read at 168 h, given only 0 h and 24 h |
| Nature | dynamic anomaly detection, unsupervised | early forecasting, supervised on 168 h targets |
| Output | score, disposition, primary parameter, `A_` reason codes | six forecasts, six p95 envelopes, primary parameter, `B_` reason codes |

Anushka's fusion layer joins the two by `component_id` and produces the final
**PASS / MONITOR / REJECT**. Sanskruti scores both blind against hidden truth.
Tanisha validates the domain and standards claims. Chaitany owns the data.

### 1.4 Module B's job, stated exactly

> Using only information available at 0 h and 24 h, predict each component's six
> parameter values at 168 h, and emit forecast-risk evidence alongside each forecast.

**Primary metric: MAE at 168 h**, per parameter. MAPE is deliberately excluded —
`Input_Leakage_Current` runs down to ~0.007 µA and a percentage metric would be
dominated by its smallest denominators. `nMAE_pct` (MAE as a percentage of the
median 168 h value) is used instead where a cross-parameter comparison is needed.

**Module B does not decide anything.** It forecasts and it supplies evidence. The
disposition belongs to fusion. This is decision D1 and it is load-bearing throughout.

### 1.5 Why the problem is hard, physically

Burn-in drift is **sub-linear in time** — fast early settling, then slowing. On
FINAL-01 the implied exponent is `t^0.58` to `t^0.80` (§9.2.2). A perfectly linear
process would put 24/168 = 14.3 % of the total move at the 24 h checkpoint. Sub-linear
drift puts more there, but the total move is small — a few percent of the level — so
the *early delta is a low-signal-to-noise estimator of the drift rate by construction*.
On three of six parameters the median early move is smaller than the assumed
measurement noise on that delta. That is not a flaw in the data; it is the shape of
the problem, and it is why a well-calibrated constant beats a learned model on some
parameters.

---

## 2. The team, and the file-distribution discipline

### 2.1 Six members

| Member | Owns |
|---|---|
| **Chaitany** | synthetic data: schema, generator, splits, versioning. Custodian of the master ZIP. |
| **Riddhi** | Module A — lot-relative dynamic outlier detection |
| **Nirmik** | Module B — 168 h forecasting, plus the technical specification and change log |
| **Tanisha** | domain research and standards validation |
| **Sanskruti** | validation, testing, blind evaluation |
| **Anushka** | integration, fusion, explainability, dashboard, demo — team lead |

Working pattern: each member gets a long structured "PART 1–16" master research
prompt scoped strictly to their own lane, which produces that member's role guide.

### 2.2 The distribution rule, and why it matters for Module B

`SIH26170_FINAL_Team_Group_Bundle.zip` went to the group. It contains one named ZIP
per member plus the distribution guide. **Each member opens only their own ZIP.**

| Where | File | Who |
|---|---|---|
| Group | `SIH26170_FINAL_Team_Group_Bundle.zip` | Riddhi, Nirmik, Anushka, Tanisha |
| Private | `SIH26170_FINAL_Sanskruti_Evaluator.zip` | Sanskruti only — contains `Hidden_Ground_Truth.csv` and `ModuleB_Holdout_168h_Targets.csv` |
| Never sent | `SIH26170_FINAL_RELEASE_01_Master.zip` | Chaitany only |

If Nirmik or Riddhi sees the evaluator or master files, the final evaluation stops
being blind and the result is worth nothing. **This has been honoured.** Only
`NIRMIK_ModuleB.zip` was opened. Riddhi's, Tanisha's and Anushka's ZIPs were never
extracted; the evaluator and master ZIPs were never in Nirmik's possession.

### 2.3 The five-step team workflow

1. Riddhi and Nirmik build and re-run on the FINAL-01 train files.
2. Both use their calibration files and freeze model / thresholds / features.
3. Both run holdout **only after freeze** and send outputs to Sanskruti.
4. Sanskruti scores against hidden truth; reports false negatives and MAE.
5. Anushka joins A and B by `component_id` and runs fusion and the dashboard.
6. Tanisha finishes domain validation in parallel.
7. Chaitany keeps `SIH26170-FINAL-01` fixed. **No regeneration for a better score.**

Module B is at the end of step 2, with step 3 gated behind team sign-off.

---

## 3. The dataset — `SIH26170-FINAL-01`

### 3.1 Identity

```json
{
  "dataset_id": "SIH26170-FINAL-01",
  "status": "FINAL",
  "generator_version_public": "v4-final1",
  "split_id": "LOTSPLIT-05",
  "rows": 5400,
  "lots": 72,
  "variants": ["CMOS_A", "CMOS_B", "CMOS_C"],
  "epochs_h": [0, 24, 96, 168],
  "parameters": ["IDDQ", "Input_Leakage_Current", "Active_Supply_Current",
                 "Propagation_Delay", "Output_Rise_Time", "Output_Fall_Time"],
  "join_key": "component_id"
}
```

Two notes carried in the manifest and worth repeating: **`component_id` is an
identifier, not a time order**, and **`Active_Supply_Current` is the final name** —
`Supply_Current_ICC` must not appear in new code.

### 3.2 The three splits Module B receives

| Split | File | Rows | Lots | Lots per variant | 168 h targets | SHA-256 (first 16) |
|---|---|---|---|---|---|---|
| Build | `01_BUILD/ModuleB_Train.csv` | 3,151 | 42 | 14 / 14 / 14 | present | `f4965db3803b9c93` |
| Calibrate | `02_CALIBRATE/ModuleB_Calibration.csv` | 906 | 12 | 4 / 4 / 4 | present | `5f6e977e2ea746dc` |
| Holdout | `03_HOLDOUT_AFTER_FREEZE/ModuleB_Holdout.csv` | 1,343 | 18 | 6 / 6 / 6 | **absent by design** | `e8082400cc815049` |

3,151 + 906 + 1,343 = **5,400 rows**; 42 + 12 + 18 = **72 lots**. Both match the
manifest exactly. Rows per variant in train: CMOS_A 1,051 · CMOS_B 1,041 · CMOS_C 1,059.
Rows per lot run 68–82.

**No lot and no `component_id` is shared between any two splits.** Verified for all
three pairs.

### 3.3 Reference files

| File | What it gives |
|---|---|
| `REFERENCE/Device_Specs.csv` | per variant × parameter: working VCC, synthetic 0 h baseline, `static_spec_max` where one exists, provenance labels, test conditions, source URL |
| `REFERENCE/Schema_Data_Dictionary.csv` | every column's type, unit, meaning **and its Module B rule** (`allowed predictor` / `never Module B predictor` / `target only; hidden in holdout`) |
| `REFERENCE/ModuleB_Output_Contract.csv` | the exact 15-column header integration expects |
| `REFERENCE/Dataset_Version_Safe.json` | the identity block above |

### 3.4 Device_Specs in full

| Variant | Parameter | 0 h baseline | `static_spec_max` | Baseline provenance |
|---|---|---|---|---|
| CMOS_A | IDDQ | 1.5 µA | 40.0 | engineering baseline anchored to datasheet |
| CMOS_A | Input_Leakage_Current | 0.02 µA | 0.1 | engineering baseline anchored to datasheet |
| CMOS_A | Active_Supply_Current | 90.0 µA | — | derived from datasheet `Cpd` |
| CMOS_A | Propagation_Delay | 9.0 ns | 18.0 | **datasheet typical** |
| CMOS_A | Output_Rise_Time | 8.0 ns | 15.0 | derived from datasheet transition time |
| CMOS_A | Output_Fall_Time | 7.5 ns | 15.0 | derived from datasheet transition time |
| CMOS_B | IDDQ | 0.6 µA | 2.0 | engineering baseline anchored to datasheet |
| CMOS_B | Input_Leakage_Current | 0.08 µA | 1.0 | engineering baseline anchored to datasheet |
| CMOS_B | Active_Supply_Current | 47.5 µA | — | derived from datasheet `Cpd` |
| CMOS_B | Propagation_Delay | 5.2 ns | 7.5 | **datasheet typical** |
| CMOS_B | Output_Rise_Time | 3.2 ns | — | synthetic characterisation |
| CMOS_B | Output_Fall_Time | 3.0 ns | — | synthetic characterisation |
| CMOS_C | IDDQ | 0.3 µA | 1.0 | engineering baseline anchored to datasheet |
| CMOS_C | Input_Leakage_Current | 0.15 µA | 1.0 | engineering baseline anchored to datasheet |
| CMOS_C | Active_Supply_Current | 62.7 µA | — | derived from datasheet `Cpd` |
| CMOS_C | Propagation_Delay | 3.5 ns | 4.1 | **datasheet typical** |
| CMOS_C | Output_Rise_Time | 1.8 ns | — | synthetic characterisation |
| CMOS_C | Output_Fall_Time | 1.7 ns | — | synthetic characterisation |

**Seven of eighteen cells carry no `static_spec_max`**: `Active_Supply_Current` on
all three variants, and `Output_Rise_Time` / `Output_Fall_Time` on CMOS_B and CMOS_C.
Per decision D1 **no limit is invented for them.** They stay `NaN`, the limit-based
reason codes never fire there, and `evidence_<p>_limit` is `NaN` rather than zero —
because `NaN` is the true answer and zero would read as "at the limit".

### 3.5 Column contract — what Module B may and may not read

| Columns | Rule |
|---|---|
| `component_id`, `lot_id`, `device_family`, `device_variant` | context, allowed |
| `<p>_0h`, `<p>_24h` for all six | **allowed predictors** |
| `<p>_96h` | **never a Module B predictor** — and not present in Module B's files at all |
| `<p>_168h` | **target only**, hidden in the holdout |

The holdout file has 16 columns; train and calibration have 22.

### 3.6 Provenance labelling

Every numeric generator constant carries a source status — `VERIFIED`,
`CALIBRATED` or `ASSUMED`. That discipline matters downstream: the measurement-noise
CVs Module B uses for its `B_NO_EARLY_SIGNAL` flag and its noise-floor comparison are
**`ASSUMED`** values from the design record §6.3, not measurements, and everything
derived from them inherits that status. This guide says so at every point of use.

Declared measurement-noise CVs:

| Parameter | CV | Noise on a 0→24 h delta (`CV·√2`) |
|---|---|---|
| IDDQ | 1.0 % | 1.41 % |
| Input_Leakage_Current | 2.0 % | 2.83 % |
| Active_Supply_Current | 0.5 % | 0.71 % |
| Propagation_Delay | 0.35 % | 0.50 % |
| Output_Rise_Time | 0.45 % | 0.64 % |
| Output_Fall_Time | 0.45 % | 0.64 % |

---

## 4. The contract — nine rules, and why each exists

These are enforced in code, not by convention. Each one raises rather than warns.

| # | Rule | Why | Where enforced |
|---|---|---|---|
| 1 | No `*_96h` column may reach a feature matrix | Module B's whole point is *early* prediction; 96 h would make it a trivially easier problem and a dishonest one | `guards.find_forbidden_epoch_columns`, checked on the file **and** on the matrix handed to each estimator |
| 2 | No `*_168h` value may be a feature | that is the target | `guards.assert_feature_matrix_clean` |
| 3 | No hidden label, defect mode, severity or onset may be read | those are Sanskruti's; reading them destroys the blind evaluation | `guards.find_hidden_label_columns`, 22 substring tokens |
| 4 | Every split is by **whole lot** | components in a lot share process conditions; a row split leaks a lot's behaviour into its own validation score | `guards.assert_folds_are_whole_lots`, asserted on every CV pass |
| 5 | The holdout is opened once, after freeze | a blind test stops being blind the moment a result is seen and acted on | gated `scripts/12` |
| 6 | No static limit is invented | a fabricated limit manufactures false positives that look authoritative | `dataio.load_specs` keeps `NaN`; `reason_codes` skips cells without limits |
| 7 | No `module_b_disposition` column | an always-null column invites a fusion rule built against a field Module B has no authority over | `guards.assert_output_contract` |
| 8 | Differences under 5 % MAE are ties | a **pre-declared practical threshold** agreed before the results were seen, paired with a per-lot significance test; rank order is not evidence. No formal power analysis was run, so this is a stated convention, not a demonstrated resolution limit for 42 lots *(corrected 19 Sep, S5)* | `metrics.verdict` |
| 9 | The p95 envelope is evidence, never a screen | its tail coverage is measured and is far below nominal | stated in the model card, integration note and the envelope module's own docstring |

**Why guards raise instead of warning.** A silently wrong CSV reaching Anushka's
fusion layer is far more expensive than a crashed script. A run that cannot be
trusted must not produce a file.

Two distinct exception types, because they mean different things:

- `LeakageError` — a contract rule was broken. Never recoverable in code; the input
  file or the call is wrong. Escalate.
- `DataQualityError` — the file is structurally broken (nulls, duplicate ids,
  non-positive magnitudes, unknown variant). Escalate to Chaitany; **do not patch
  the data locally.**

Neither is raised for "the MAE is worse than I hoped". That is a model problem.

---

## 5. The history that still binds — Candidate V1 and decisions D1–D5

*(Candidate V1 numbers in this section are labelled and are not FINAL-01 results.)*

Before FINAL-01 there was `SIH26170-CANDIDATE-01` — 3,147 train rows, 21 lots,
split `LOTSPLIT-04`. Nirmik audited and benchmarked it on 14 Sep 2026 and sent
Chaitany a review. On 15 Sep Chaitany responded with five decisions. Those decisions
are why FINAL-01 looks the way it does and why the model configuration was frozen
before FINAL-01 arrived.

### D1 — Module B does not own the disposition *(decided)*

The Candidate V1 review raised one blocker: only **5 of 3,147** components breached
any available static limit at 168 h, all five in CMOS_C `Propagation_Delay`, and
seven of eighteen cells had no limit at all. A limit-based disposition cannot be
built or validated on five positive examples confined to one cell.

Decision: **final PASS / MONITOR / REJECT belongs to Module A + fusion.**
`module_b_disposition` is withdrawn from Module B's contract entirely — not emitted
as `NOT_SET` either, so nobody can build a fusion rule against a column Module B has
no authority over. Carried instruction: **do not invent missing static limits.**

### D2 — the architecture is frozen so the comparison is fair *(decided)*

Calibration was put on hold and Candidate V2 generated first. To keep the
V1 → V2 comparison attributable to the data, none of these may change:

- the two feature groups (`own` for current/leakage, `own+lot+cross` for timing)
- Huber on the relative delta from 24 h, ε = 1.35, α = 1e−3
- the pooled-with-variant-one-hot structure
- the whole-lot GroupKFold protocol and the 7-fold map
- the conformalised envelope at τ = 0.95

**This is honoured.** The `FROZEN_V1` block in `moduleb/config.py` is value-for-value
the Candidate V1 freeze.

### D3 — five generator changes accepted *(delivered in FINAL-01)*

1. strengthen the existing lot-ageing effect
2. recalibrate `Input_Leakage_Current` early signal-to-noise
3. more independent lots, keeping ~5,400 total rows
4. improve clean-lot coverage across variants
5. create enough static-fail cases while keeping static-pass anomalies the majority

Stated principle: **the generator is not changed to improve Module B's MAE.**
§9.3 checks each of the five against the delivered data rather than taking them on
trust.

### D4 — FDI-5 retracted; the earlier claim was wrong *(closed)*

Nirmik had claimed the CMOS_C propagation-delay baseline of 3.5 ns was a misread
datasheet maximum and should be ~2.0–2.5 ns. **That was wrong.** TI's SN74LVC00A
switching-characteristics table gives, for `tpd` A or B → Y at VCC = 3.3 V ± 0.3 V,
TA = 25 °C:

```
MIN 1      TYP 3.5      MAX 4.1     (ns)
```

3.5 ns is a genuine datasheet **typical**. The error came from reading the MIN and
TYP columns as a min-to-max range and ignoring MAX. Two consequences, both against
the original argument: the 5.5 → 4.1 ns limit change was a **correction**, not a
regression (5.5 ns is the max over −40 °C to +125 °C; 4.1 ns is the max at 25 °C, and
the design record characterises at a standardised 25 °C checkpoint); and a typical
LVC00A part really does sit at ~85 % of its 25 °C maximum. Mock v1 review item C4 is
withdrawn on the same grounds.

What survives, restated without the false premise: CMOS_C propagation delay was the
**only near-binding limit in Candidate V1**, which is why all five static breaches
landed there — a fact about which cells can produce static-fail cases at all, and
the direct motivation for V2 change 5.

### D5 — standing instruction *(honoured)*

No retraining, no tuning, no configuration changes until the new dataset is
benchmarked with the same code. Candidate V1 is the before-state; when V2 lands, run
the same audit and the same benchmark **unchanged**, so the difference is
attributable to the data.

### What Candidate V1 established that still stands

Two findings from the V1 benchmark are structural and survive into FINAL-01 as the
*reason* for the frozen configuration, not as current numbers:

- **The target parameterisation is the single most consequential choice.** Fitting a
  regularised model to the raw 168 h level shrinks it toward the target mean, which
  is a terrible prior. Fitting it to the **relative delta from 24 h** shrinks it
  toward persistence, which is a good one. That change alone flipped learned models
  from losing to median-ratio to beating it.
- **Huber, not squared loss.** Defect injection puts a heavy right tail on the drift
  distribution and squared loss chases it. Huber won 17 of 18 cells *(Candidate V1)*.

And one negative result that still governs what may be claimed:

- **EXP-03 closed with a negative result.** The conformalised envelope achieved
  calibrated *marginal* coverage but caught only **38 %** of the worst-drifting decile
  at τ = 0.95 *(Candidate V1)*. It ships as evidence, never as a screen.

---

## 6. The build — what was made, and why it is shaped this way

### 6.1 The brief that drove the architecture

Nirmik's constraints were explicit: **do not ship one large script that makes VS Code
crawl**; make it fail-safe; and above all **do not produce false positives**. The
Candidate V1 pipeline was a single 900-line file — correct, but hard to open, harder
to review line by line, and impossible to unit-test in pieces. FINAL-01's package
splits the same logic into sixteen modules, none over 230 lines, each doing one thing
and tested for that one thing.

### 6.2 Layout

```
08_final_01/
├── moduleb/        the package — 16 modules, 1,780 lines, no module imports upward
├── scripts/        15 thin runners, numbered in run order; all logic lives in moduleb/
├── tests/          6 files, 65 tests
├── notebooks/      4 notebooks importing the same package
├── docs/           this guide, model card, runbook, decision log, integration note
├── data/           the four files Module B is allowed to read
├── results/        every CSV the scripts produce (generated; safe to delete)
├── models/         the frozen artifact, once stage 11 has run — currently absent
├── run_all.py      runs every ungated stage in order
└── requirements.txt
```

89 files, 2.1 MB. Import order is deliberate and shallow — `constants → config →
guards → dataio/features → featureset → models/baselines → metrics/cv → envelope →
reason_codes → contract → freeze/predict` — so any module can be read on its own.

### 6.3 Every module, and what it is for

| Module | Lines | Responsibility |
|---|---|---|
| `constants.py` | 77 | the dataset's vocabulary. Parameter order is load-bearing — it fixes the output column order. If this file ever disagrees with `Schema_Data_Dictionary.csv`, the CSV wins and the file is the bug. |
| `config.py` | 129 | **every tunable number, in one place.** The freeze stage hashes this module's *values* into the manifest, so a comment edit does not invalidate a model but a changed number does. Contains the `FROZEN_V1` block. |
| `guards.py` | 224 | the fail-safe layer. Every mechanically checkable contract rule, raising not warning. |
| `dataio.py` | 132 | the only place file paths are written down. Every load goes through `load_split`, so no stage can read a file that skipped the guards. SHA-256 of every input is recorded. |
| `features.py` | 100 | derived columns, all computable at prediction time, plus deterministic whole-lot fold assignment |
| `featureset.py` | 104 | which derived columns each model receives, and the full-rank basis rule for linear models |
| `models.py` | 134 | estimator construction, fit and predict for one parameter; the relative-delta target; optimiser-convergence tracking |
| `baselines.py` | 73 | persistence, linear extrapolation, median-ratio — refit inside the same folds |
| `metrics.py` | 103 | the metric panel and the per-lot paired test |
| `cv.py` | 68 | whole-lot cross-validation — the only place a model is scored out-of-fold |
| `envelope.py` | 120 | conformalised GBR quantile regression, and the coverage report that keeps it honest |
| `reason_codes.py` | 201 | the evidence layer and the false-positive discipline |
| `contract.py` | 82 | assembles and validates the frame integration consumes |
| `freeze.py` | 119 | turns a configuration into an immutable, digest-checked artifact |
| `predict.py` | 94 | inference, plus the clip guards that sit in front of it |
| `__init__.py` | 20 | the import map |

### 6.4 The model, stated plainly

One regressor per parameter. All three variants pooled, with a variant one-hot.

| Parameter | Model | Feature set |
|---|---|---|
| IDDQ | Huber | `own` |
| Input_Leakage_Current | Huber | `own` |
| Active_Supply_Current | Huber | `own` |
| Propagation_Delay | Huber | `own+lot+cross` |
| Output_Rise_Time | Huber | `own+lot+cross` |
| Output_Fall_Time | Huber | `own+lot+cross` |

`HuberRegressor(epsilon=1.35, alpha=1e-3, max_iter=800)` behind a `StandardScaler`,
refit inside every fold so the scaler never sees a validation lot. All fits converge
well inside `max_iter` on FINAL-01 — the run reports zero capped optimisations.

**The target.** The model does not predict the 168 h level. It predicts the relative
change from the 24 h reading:

```
y = (x₁₆₈ − x₂₄) / x₂₄        prediction = x₂₄ × (1 + ŷ)
```

Two reasons. It makes the three variants commensurable, so one pooled model replaces
three thin ones. And it means the model learns only the drift instead of re-deriving
a level that has already been measured — otherwise a large, easy, uninformative
component of the variance would dominate the fit.

**The three feature sets.**

| Name | Contents |
|---|---|
| `own` | the parameter's own 0 h and 24 h levels |
| `own+lot` | + the same two statistics for the component's own lot (median) |
| `own+lot+cross` | + the other five parameters' 0 h/24 h levels and own-lot medians |

`pooled=True` normalises every level column by the `Device_Specs` 0 h baseline for
that parameter and variant, then appends a three-way variant one-hot. That is what
lets one model span CMOS_A/B/C: a delay in ns and a current in µA become comparable
multiples of a fixed external constant, and the one-hot carries whatever
variant-specific offset survives.

**Why two groups and not eighteen per-cell picks.** Choosing the best configuration
independently for each of 18 variant × parameter cells on 42 lots is selection
overfitting. Two groups, split on an identifiable physical mechanism, is what can be
defended: the current/leakage block's early delta is noise-dominated and its
cross-block coupling is near zero; the timing block shares a latent slew factor and
its members' early deltas cross-predict.

**Why linear models get fewer columns.** `delta = x₂₄ − x₀` and `dev = x − lot_median`
are *exact linear combinations* of the level terms. Handing all of them to
OLS/Ridge/Huber at once is exact collinearity, which makes coefficients unstable.
The redundant forms go only to the tree model, which cannot construct them itself.
`tests/test_features.py::test_linear_basis_is_full_rank` checks the rank of every
linear design matrix.

### 6.5 Feature purity — the rule every derived column obeys

A feature may be a function of (a) this component's own 0 h and 24 h measurements,
(b) the 0 h/24 h measurements of other components **in this component's own lot**, and
(c) the fixed `Device_Specs` 0 h baseline. Nothing else.

Why that is enough to be safe:

- Lot medians are computed within the component's own lot, so they are available for
  an unseen holdout lot with no information from any training lot. They therefore
  cannot leak across a whole-lot fold boundary either — **the fold is the lot, and
  the statistic never crosses it.**
- The `Device_Specs` baseline is an external constant fixed before the data existed.
  Using it to normalise scale is not learning anything from the fold.

Two tests prove this rather than asserting it. One perturbs every `168h` column
wildly and checks that no derived feature moves. The other tampers with one lot's
measurements and checks that no other lot's features move.

**The consequence that was missed until review finding F1.** "Computable at
prediction time" is not the same as "computable from one row". The own-lot median
needs the lot. `predict_frame` recomputes it from whatever rows are in the
request, so the timing forecasts are a property of the **cohort**, not of a single
component. Measured on calibration lot `B_L23`: every one of its 72 components
changes when scored alone instead of with its lot — median |Δ| 0.55–0.66 %, **max
7.18 % on `Propagation_Delay`**, which is most of the 8.95 % advantage the model
has over the baseline on that parameter. The three `own` parameters are bit-identical,
because they have no lot terms.

Module B's serving contract is therefore **cohort-level**, and
`moduleb.config.MIN_LOT_COHORT` enforces it. §16.2 states it for integration.

### 6.6 The whole-lot fold map

Seven folds. Lots are sorted by name and dealt round-robin within each variant, so
every fold holds out two complete lots of each variant — six lots, 434–464 rows.
Fully deterministic: the same file always gives the same fold map, which is what
makes a benchmark rerun comparable rather than merely similar.

| Fold | CMOS_A lots | CMOS_B | CMOS_C | Rows |
|---|---|---|---|---|
| 0 | 2 | 2 | 2 | 444 |
| 1 | 2 | 2 | 2 | 453 |
| 2 | 2 | 2 | 2 | 458 |
| 3 | 2 | 2 | 2 | 464 |
| 4 | 2 | 2 | 2 | 434 |
| 5 | 2 | 2 | 2 | 447 |
| 6 | 2 | 2 | 2 | 451 |

---

## 7. The fail-safe layer

### 7.1 What is checked, and where

**On every input file** (`assert_input_clean` + `assert_data_quality`): forbidden
epoch columns; hidden-label columns against 22 substring tokens; required context
columns; all twelve 0 h/24 h predictors; targets present-or-absent as the stage
requires; emptiness; nulls; duplicate `component_id`; unknown `device_variant`;
unexpected `device_family`; non-numeric measurement columns; non-positive values;
non-finite values.

**On every feature matrix handed to an estimator** (`assert_feature_matrix_clean`):
forbidden columns, target leakage, non-finite values. This is the one that would
catch a feature-engineering mistake, because it inspects what the model actually sees
rather than what the file contained.

**Between splits** (`assert_lots_disjoint`): shared lots and shared `component_id`s.

**On every CV pass** (`assert_folds_are_whole_lots`): no lot split across folds.

**On every prediction** (`assert_predictions_sane`): shape, non-finite, non-positive.

**On every output frame** (`assert_output_contract`): all contract columns present,
no forbidden disposition column, row count matches, `component_id` order matches,
forecast columns finite, `module_b_primary_parameter` is one of the six parameters.

### 7.2 The two clip guards, and why they are loud

Two guards clip rather than raise, and both report what they did:

- **Non-positive point forecast → replaced by the 24 h reading.** All six parameters
  are magnitudes; a negative forecast is meaningless, and falling back to "no drift"
  is the conservative answer. If this fires on more than a handful of rows, the model
  is wrong and the count in the log is the evidence.
- **Envelope below the point forecast → raised to it.** An upper bound beneath its own
  central estimate is incoherent.

Neither is allowed to be silent. A quiet repair is how a real problem reaches the
fusion layer wearing a clean face.

### 7.3 Two bugs the test suite found before anyone else did

Both are recorded because they are the argument for having the suite at all.

**1. A string column swept into a numeric check.** `assert_output_contract` selected
its numeric columns with `c.startswith(("predicted_", "module_b_p"))`. But
`module_b_primary_parameter` also starts with `module_b_p` and holds a *string*, so
the finiteness check crashed on it. Fixed by requiring the epoch suffix as well, and
by asserting that exactly twelve numeric forecast columns are matched. Three tests
caught it.

**2. A claim its own test did not test.** `test_prediction_is_batch_size_invariant`
was cited in the guide, the integration note and acceptance criterion F5 as proof
that a one-component API call is safe. It never called the production prediction
path. Found by independent review (F1), not by the suite — which is the honest
lesson: a test can pass and still be evidence for nothing. The test is replaced,
the claim withdrawn, and the serving contract is now enforced in code.

**3. A firing rate above 100 %.** The reason-code summary's "ANY" row summed the
per-parameter counts, so a component flagged on two parameters was counted twice and
the report read **133 % of components flagged**. Fixed to count components carrying
the code on at least one parameter. Both fixes now have regression tests.

### 7.4 The test suite — 65 tests in six files

| File | Tests | What it protects |
|---|---|---|
| `test_guards.py` | 21 | every guard fires. A guard nobody has seen fail is a comment, not a guard. Includes eight parametrised hidden-label names and an explicitly random row split. |
| `test_features.py` | 8 | feature purity (the two tampering tests), deterministic folds, full-rank linear basis, predict-time column alignment raising instead of zero-filling |
| `test_pipeline.py` | 16 | determinism, row-order invariance, the **cohort serving contract** (F1), contract shape, envelope ≥ forecast, conformal quantile edges, **tail ranked by true drift** (F3) |
| `test_reason_codes.py` | 9 | the false-positive tests — no invented limits, the qualifier never alone, sparsity, scale-freeness, zero-dispersion safety |
| `test_edge_cases.py` | 11 | empty input, single component, single-row lot, unseen variant, too few lots, extreme values, metric guards, the tie rule, lots-not-rows counting |
| `conftest.py` | — | a small synthetic fixture so behaviour tests run in seconds without depending on FINAL-01 |

Three that are worth calling out specifically:

- **`test_predict_time_missing_column_raises_not_zero_fills`.** A column present at
  fit time and missing at predict time raises. A silent `0.0` in a level column is not
  a missing value — it is a *wrong measurement*, and it would corrupt the prediction
  quietly. Only the variant one-hot columns may legitimately be absent-and-zero.
- **`test_raw_request_composition_changes_timing_forecasts`.** This *replaced* a
  test that claimed the opposite. The old one split an already feature-engineered
  frame, so the lot medians had been computed before the split and could not move;
  it proved the estimator does not care how rows are chunked, and was then cited as
  evidence for a single-component API. The new test exercises `predict_frame` from
  raw input and pins the real behaviour. Three more tests cover the refusal, the
  deliberate override, and the degeneracy of the evidence layer on one row.
- **`test_paired_test_counts_lots_not_rows`.** 500 rows in 10 lots must report
  `n_lots == 10`, not 500.

### 7.5 Determinism

Single seed (`GLOBAL_SEED = 0`), deterministic fold assignment from lot names, sorted
iteration throughout, and the only stochastic step — the conformal lot draw — is
seeded. The rehearsal stage predicts the same file twice and asserts the forecasts and
reason codes are bit-identical.

---

## 8. The method — fifteen stages, and what each one decides

`python run_all.py` runs every ungated stage in order. The recorded run took **505 s**
(~8.5 min), of which the 24-configuration grid is 385 s.

| Stage | Script | Decides | Recorded outcome |
|---|---|---|---|
| 0 | `00_selfcheck.py` | are the code and inputs what we think they are | PASS — 65 tests, 7 hashes, totals match the manifest |
| 1 | `01_audit.py` | data bug, or a modelling problem to live with | **clean; nothing to escalate** |
| 2 | `02_drift_structure.py` | is the thing being predicted learnable at all | learnable; see §9.2 |
| 3 | `03_benchmark_frozen_v1.py` | the frozen V1 config on FINAL-01, **unchanged** | 4 of 6 parameters beat the baseline |
| 4 | `04_benchmark_grid.py` | 24 configurations, evidence only | frozen config stands; max gap 4.5 % |
| 5 | `05_calibration_report.py` | held-out score on 12 calibration lots | see §11 |
| 6 | `06_predeclared_falltime_rule.py` | the one pre-declared change | **did not fire** |
| 7 | `07_extrapolation_risk.py` | where a forecast is untrustworthy | evidence for D11, **closed 19 Sep** |
| 8 | `08_reason_code_audit.py` | are the `B_` codes sparse enough to act on | PASS — 14.9 % flagged |
| 9 | `09_envelope_coverage.py` | what the p95 envelope may be called | evidence, not a screen |
| 10 | `10_dryrun_freeze_predict.py` | rehearse freeze + holdout on a stand-in | PASS |
| 11 | `11_freeze.py` | **GATED** — freeze the model | ⏸ awaiting team sign-off; no open decision remains |
| 12 | `12_predict_holdout.py` | **GATED** — the one-shot holdout run | ⏸ not run |
| 13 | `13_build_validation_summary.py` | assemble the summary **from `results/`** | done |
| 14 | `14_verify_claims.py` | do the documents **and the scripts** match the numbers | pass; the count is in `RELEASE_MANIFEST.json` |
| 15 | `15_release_manifest.py` | write `RELEASE_MANIFEST.json` — the release identity card | pass |

### 8.1 Stage 10 — rehearsing a one-shot

The holdout run is a one-shot. If stage 11 or 12 has a bug, the team finds out after
the only blind run has been spent. So stage 10 exercises both code paths end to end on
a stand-in: it freezes on **train lots only**, then predicts on the calibration file
with its `168h` columns **stripped** — structurally identical to the holdout, same
guard path, no answers. The script asserts the stand-in's column list matches the real
**declared** holdout header — `moduleb.holdout_manifest.COLUMNS`, verified against the
delivery SHA-256 — before proceeding. The rehearsal artifact is written to a temporary
directory, stamped `release_state="REHEARSAL"` with a placeholder sign-off that
`freeze.load_frozen` refuses for production use, and deleted at the end of the stage.

Because the real calibration answers exist, the rehearsal can also be scored, which
previews what the holdout run will look like. The rehearsal passed, including the
bit-identical determinism check.

*(Corrected 19 Sep, round 2 / P1-G1. Before this release stage 10 read the real holdout's
header to compare column lists, and this paragraph said the file "was not opened by it".
It now reads the declared manifest instead and hashes the file for provenance. The full
recorded access history is decision **D14** and `moduleb/holdout_manifest.py`.)*

### 8.2 Stage 14 — checking the prose against the numbers

Documentation drifts. Someone reruns a stage, a number moves, and the model card still
quotes the old one — and a model card that quotes a stale number is worse than no model
card, because it will be believed. Stage 14 asserts every load-bearing figure and
structural guarantee in the README, the docs, **the runner scripts' own printed output,
the notebooks, the package source and `RELEASE_MANIFEST.json`** against the CSVs in
`results/`. It is what caught the row-weighted / macro-lot MAE confusion described in
§0 rule 4.

The current check count is **not quoted here on purpose**: a number that has to be
hand-edited every time a check is added is a number that goes stale. Stage 14 prints it,
and `RELEASE_MANIFEST.json` records it under `verification.claim_check` alongside the
test result. *(Corrected 19 Sep, round 2 / P2: this paragraph said "53 load-bearing
figures" long after the checker had grown past it.)*

Round 2 extended the checker in one structurally important way: the **executable**
surfaces are scanned as well as the prose. A withdrawn claim that survives in a
`print()` is still a claim the project makes — it just makes it to a terminal.

### 8.3 The two gates

**Stage 11 refuses** when the unit tests fail, when the pre-declared fall-time rule has
not been executed, when `moduleb/config.py` disagrees with that executed decision, or
when a frozen artifact already exists without `--force --reason`. `--team-signoff` is
required and is written into the manifest, so the approval travels with the model.

**Stage 12 refuses** when there is no frozen artifact, when the config digest no longer
matches the artifact's, when the holdout carries `168h` columns, or when the output file
already exists — because the one-shot is spent.

Both gates were verified to refuse. Neither has been overridden.

---

## 9. The research — what FINAL-01 actually contains

*All figures: recorded run of 18 Sep 2026, training split unless stated.*

### 9.1 Audit — is anything here a data bug?

| Check | train | calibration | holdout |
|---|---|---|---|
| Rows | 3,151 | 906 | 1,343 |
| Lots | 42 | 12 | 18 |
| Columns | 22 | 22 | 16 |
| Duplicate `component_id` | 0 | 0 | 0 |
| Null values | 0 | 0 | 0 |
| Non-positive measurements | 0 | 0 | 0 |
| Columns containing `96` | 0 | 0 | 0 |
| All six `168h` targets | yes | yes | **no (correct)** |
| Unexpected columns | none | none | none |
| Rows per lot (min–max) | 68–82 | 70–82 | 69–82 |

Whole-lot separation: **no shared lot and no shared `component_id`** between any of
the three pairs. Variant balance is exact — 14/14/14, 4/4/4, 6/6/6 lots.

**Verdict: clean. Nothing to escalate to Chaitany.**

#### Static-limit headroom

This is context for fusion, not a Module B job, but it is what makes the limit-based
reason codes able to fire at all.

Across train + calibration there are **58 breaches of an available static limit at
168 h, out of 14,889 checkable component × parameter cells (0.39 %)**, spread across
**10 distinct variant × parameter combinations**. Candidate V1 had **5**, all in
CMOS_C `Propagation_Delay`.

One cell is worth naming: **CMOS_A IDDQ has a 40 µA limit against a 1.5 µA baseline**
— the maximum observed is 6.7 % of limit, so that code can never fire there. That is
a fact about the reference device, not a defect.

### 9.2 Drift structure — is the thing being predicted learnable?

Three quantities decide this, and none of them is the MAE.

#### 9.2.1 How well does the early move predict the late move?

`r(early relative move, late relative move)`, computed **within variant** — pooling
A/B/C would manufacture correlation out of three different baselines alone.

| Parameter | CMOS_A | CMOS_B | CMOS_C |
|---|---|---|---|
| IDDQ | 0.103 | 0.189 | 0.125 |
| Input_Leakage_Current | 0.216 | **0.076** | **0.558** |
| Active_Supply_Current | 0.322 | 0.334 | 0.114 |
| Propagation_Delay | 0.440 | 0.406 | 0.362 |
| Output_Rise_Time | 0.311 | 0.250 | 0.251 |
| Output_Fall_Time | **0.642** | 0.341 | 0.387 |

This is a diagnostic of the **simple linear** early→late relationship, and `r²` —
from **0.006** (Input_Leakage on CMOS_B) to **0.412** (Output_Fall_Time on CMOS_A)
— is the share of late-drift variance that linear association explains. A low value
means weak *linear* signal. It is **not** an upper bound on predictability: a
nonlinear function, or an interaction between the 0 h and 24 h readings, is not
constrained by a Pearson correlation. *(Corrected 19 Sep, review finding F6; this
paragraph previously called it "the ceiling".)* A parameter near zero is still not a
modelling failure — its late drift is barely visible at 24 h by this measure, and
saying so is part of the job.

Between 10 % and 32 % of components move **downward** from 0 h to 24 h, depending on
parameter and variant — consistent with measurement noise exceeding the tiny early drift.

`Input_Leakage_Current`'s late-drift dispersion is by far the largest in the file:
standard deviation of the late relative move is **18.6 % / 70.7 % / 21.0 %** by variant,
against 1.9–10.8 % for everything else. That single fact explains most of §13.

#### 9.2.2 Is drift linear in time?

Fitting `late_total ~ (t/24)^k` against the median 0→24 h and 0→168 h moves:

| Parameter | CMOS_A | CMOS_B | CMOS_C |
|---|---|---|---|
| IDDQ | 0.749 | 0.762 | 0.724 |
| Input_Leakage_Current | 0.577 | 0.628 | 0.594 |
| Active_Supply_Current | 0.734 | 0.803 | 0.770 |
| Propagation_Delay | 0.725 | 0.728 | 0.768 |
| Output_Rise_Time | 0.687 | 0.725 | 0.784 |
| Output_Fall_Time | 0.755 | 0.735 | 0.683 |

Range **0.577 – 0.803**. `k = 1` is linear; `k < 1` is sub-linear, the physically
expected burn-in shape. `k = 1` is also exactly what the `LinExtrap` baseline assumes,
which is why it is expected to overshoot — and does, badly (§10.1).

*(Candidate V1 measured t^0.76–0.83. FINAL-01 is slightly more sub-linear.)*

#### 9.2.3 How much of the late drift is a lot effect?

Between-lot share of the variance in per-component late relative drift, computed
inside each variant:

| Parameter | CMOS_A | CMOS_B | CMOS_C |
|---|---|---|---|
| IDDQ | 10.45 % | 2.86 % | 2.99 % |
| Input_Leakage_Current | **2.56 %** | **1.16 %** | **1.46 %** |
| Active_Supply_Current | 13.90 % | **17.76 %** | 11.92 % |
| Propagation_Delay | 2.26 % | 4.65 % | 14.40 % |
| Output_Rise_Time | 4.67 % | 3.71 % | 9.44 % |
| Output_Fall_Time | 8.05 % | 10.71 % | **17.37 %** |

Range **1.16 % – 17.76 %**. On Candidate V1 this sat at **1.3 – 5.1 %**, flat, which is
why the review asked for stronger lot ageing. It is the direct measurement of whether
generator change 1 landed — and it did, **unevenly**: strongest on
`Active_Supply_Current` and CMOS_C timing, still near-absent on `Input_Leakage_Current`.

**This matters for Riddhi.** Lot *ageing* structure is now real where in V1 it was not.
Her lot-relative assumptions should behave differently on FINAL-01 — probably better.

#### 9.2.4 Early signal-to-noise

Median absolute early move ÷ assumed noise on that delta (`CV·√2`). The CV is an
**assumption** from the design record, not a measurement.

| Parameter | CMOS_A | CMOS_B | CMOS_C | % of parts below the noise floor |
|---|---|---|---|---|
| IDDQ | 0.855 | 0.917 | 0.876 | 52–57 % |
| Input_Leakage_Current | **0.634** | **0.737** | **0.498** | **65–80 %** |
| Active_Supply_Current | 0.938 | 0.924 | 0.890 | 52–56 % |
| Propagation_Delay | 0.977 | 1.180 | 1.105 | 43–51 % |
| Output_Rise_Time | 1.010 | 1.045 | 0.943 | 48–53 % |
| Output_Fall_Time | 0.946 | 0.998 | 1.140 | 45–52 % |

Everything sits within a factor of two of its own noise floor. That is the shape of the
problem, and it is why the gains in §10 are single-digit percentages rather than
transformative.

#### 9.2.5 Cross-parameter structure of the drift, within variant

The mechanism behind the timing group's `own+lot+cross` feature set.

**Timing block** — correlation of late relative drift:

| Pair | CMOS_A | CMOS_B | CMOS_C |
|---|---|---|---|
| Propagation_Delay ↔ Output_Rise_Time | 0.141 | 0.364 | 0.516 |
| Propagation_Delay ↔ Output_Fall_Time | 0.205 | 0.464 | 0.594 |
| Output_Rise_Time ↔ Output_Fall_Time | 0.235 | 0.590 | 0.577 |

**Current block:**

| Pair | CMOS_A | CMOS_B | CMOS_C |
|---|---|---|---|
| IDDQ ↔ Active_Supply_Current | 0.492 | 0.356 | 0.268 |
| IDDQ ↔ Input_Leakage_Current | 0.139 | 0.115 | 0.191 |
| Input_Leakage_Current ↔ Active_Supply_Current | 0.259 | 0.159 | 0.169 |

Cross-block coupling stays near zero (−0.07 to +0.10).

**Two honest observations, neither acted on:**

- The timing block's coupling is **much weaker on CMOS_A (0.14–0.24)** than on CMOS_B
  and CMOS_C (0.36–0.59). On Candidate V1 it was a uniform 0.65–0.73. The mechanism that
  justifies `own+lot+cross` for timing is therefore **variant-dependent on FINAL-01** in
  a way it was not on V1.
- The current block now has real internal structure (IDDQ ↔ Active_Supply at 0.27–0.49)
  where V1 reported the current block's early deltas as non-cross-predictive.

Both point at configuration changes. **Neither was made**, because decision D5 froze the
configuration for exactly this comparison — and because the grid in §10.3 says no
configuration change clears the tie threshold anyway.

Maximum |correlation| between a parameter's late drift and *any other* parameter's early
move runs 0.05–0.31, with `Input_Leakage_Current` lowest (0.05–0.09) and
`Output_Rise_Time` on CMOS_C highest (0.308).

### 9.3 Were the five V2 generator changes delivered?

Checked against the data, not taken on trust.

| # | Change | Candidate V1 | FINAL-01 | Landed? |
|---|---|---|---|---|
| 1 | strengthen lot ageing | lot explains 1.3–5.1 % of late-drift variance | **1.16–17.76 %** | **Yes, unevenly** — strong on Active_Supply and CMOS_C timing, still ~1–3 % on Input_Leakage |
| 2 | recalibrate `Input_Leakage_Current` early SNR | ~0.7–0.9 | **0.50–0.74** | **No — it moved the wrong way on this measure** |
| 3 | more independent lots | 21 train lots | **42** train lots, 72 total | **Yes** |
| 4 | clean-lot coverage across variants | uneven | 14 per variant; every split exactly balanced | **Yes** |
| 5 | spread the static-fail cases | 5 breaches, one cell | **58 breaches across 10 cells (0.39 %)** | **Yes**, and static-pass remains the overwhelming majority |

**Change 2 needs a paragraph.** Measured as "median early move ÷ declared noise",
input leakage's early signal got *weaker*, not stronger. But its early→late correlation
improved sharply on two variants (CMOS_A 0.10→0.22, CMOS_C 0.14→0.56) while CMOS_B fell
to 0.08, and its late-drift dispersion is now very large. The parameter became more
*predictable in the mean* and much more *volatile in the tail* at the same time. That is
not a complaint — it is the cause of the finding in §13.

**This is reported to Chaitany for the record, not as a request to regenerate.**
FINAL-01 stays frozen.

---

## 10. Results — the frozen configuration on FINAL-01

The headline discipline: **the Candidate V1 configuration was rerun untouched.** No
number in the `FROZEN_V1` block was changed to produce any of this. Only the dataset
changed, so the difference is attributable to the data.

### 10.1 Whole-lot cross-validation, 42 training lots

**Row-weighted pooled MAE**, native units (µA / ns):

| Parameter | Persistence | LinExtrap | Median-ratio | **Module B** | gain vs MR |
|---|---|---|---|---|---|
| IDDQ | 0.03308 | 0.06881 | 0.02422 | **0.02412** | +0.42 % |
| Input_Leakage_Current | 0.00616 | 0.00998 | 0.00476 | **0.00442** | +7.14 % |
| Active_Supply_Current | 1.54454 | 2.75629 | 1.08227 | **1.04117** | +3.80 % |
| Propagation_Delay | 0.13427 | 0.20092 | 0.09838 | **0.08956** | +8.97 % |
| Output_Rise_Time | 0.10213 | 0.17537 | 0.07410 | **0.06773** | +8.59 % |
| Output_Fall_Time | 0.10048 | 0.16497 | 0.07382 | **0.06781** | +8.15 % |

The baselines, for the record: **persistence** predicts no drift at all;
**linear extrapolation** assumes the first day's rate continues for the whole week
(`x₂₄ + (x₂₄ − x₀) × 6`); **median-ratio** multiplies `x₂₄` by one constant per
variant per parameter, fitted on the training rows of that fold.

`LinExtrap` is **worse than doing nothing**, by a factor of two to three, on every
parameter. That is the cleanest available confirmation that the 24 h checkpoint is a
poor drift-*rate* estimator: extrapolating a noise-dominated delta by 6× amplifies the
noise, not the signal. Beating persistence is trivial. **Beating median-ratio is the
real question.**

### 10.2 The paired per-lot test — the number to quote

Held-out **lots** are the unit of independence. Components in a lot share whatever that
lot did, so treating 3,151 rows as 3,151 independent observations would overstate
significance by roughly the lot size. **42 lots is the sample size.**

**Macro-lot MAE** (every lot weighted equally), two-sided Wilcoxon signed-rank:

| Parameter | Module B | Median-ratio | gain | lots won | Wilcoxon p | **verdict** |
|---|---|---|---|---|---|---|
| IDDQ | 0.02416 | 0.02426 | +0.44 % | 22 / 42 | 0.603 | **TIE** |
| Input_Leakage_Current | 0.00442 | 0.00475 | +6.83 % | 34 / 42 | 0.000094 | **BETTER** |
| Active_Supply_Current | 1.04367 | 1.08556 | +3.86 % | 25 / 42 | 0.0336 | **TIE** |
| Propagation_Delay | 0.08972 | 0.09854 | +8.95 % | 31 / 42 | 0.00132 | **BETTER** |
| Output_Rise_Time | 0.06801 | 0.07456 | +8.77 % | 33 / 42 | 0.00002 | **BETTER** |
| Output_Fall_Time | 0.06840 | 0.07464 | +8.36 % | 30 / 42 | 0.00145 | **BETTER** |

**Four of six, up from two on Candidate V1.** Fall time, which failed at 5 % on V1, now
passes. Input leakage, a tie on V1, now passes on the train CV.

Note `Active_Supply_Current` at **+3.86 % with p = 0.0336**: statistically significant,
but under the 5 % tie threshold, so it is **reported as a tie**. The threshold exists
precisely so that a p-value cannot promote a small effect.

Comparing to Candidate V1 is done on **effect sizes, never p-values**. FINAL-01 has
twice the independent lots, so the p-values are not comparable across versions and the
percentage gains are.

### 10.3 Twenty-four configurations — nothing beats the frozen one

2 structures × 4 model families × 3 feature sets, on the same folds. Deliberately a
small enumerable grid, not a hyper-parameter search: blind optimisation over 42 lots
finds fold noise, and the 5 % tie rule already says so.

| Parameter | Frozen config | Frozen MAE | Best in grid | Best MAE | Best − frozen |
|---|---|---|---|---|---|
| IDDQ | pooled/Huber/own | 0.02416 | pooled/Huber/own+lot+cross | 0.02389 | **+1.11 %** |
| Input_Leakage_Current | pooled/Huber/own | 0.00442 | per-variant/Huber/own | 0.00436 | **+1.51 %** |
| Active_Supply_Current | pooled/Huber/own | 1.04367 | pooled/GBR/own+lot+cross | 0.99647 | **+4.52 %** |
| Propagation_Delay | pooled/Huber/own+lot+cross | 0.08972 | *(same)* | 0.08972 | 0.00 % |
| Output_Rise_Time | pooled/Huber/own+lot+cross | 0.06801 | *(same)* | 0.06801 | 0.00 % |
| Output_Fall_Time | pooled/Huber/own+lot+cross | 0.06840 | *(same)* | 0.06840 | 0.00 % |

**Maximum 4.52 %, below the 5 % tie threshold on every parameter.** The frozen
configuration stands on its own evidence, not only on the freeze protocol. On the three
timing parameters the frozen config *is* the grid optimum.

Two grid observations worth recording: **per-variant structures with the wide feature
set collapse** (`per-variant/OLS/own+lot+cross` scores −296 % on input leakage — 27
features fitted on 12 lots per variant), and **OLS and Ridge lose to median-ratio on
most parameters** while Huber wins. That is **consistent with robust loss being
beneficial here** — defect injection puts a heavy right tail on the drift and squared
loss chases it — but the grid varies loss and structure together, so it does not isolate
the loss causally. *(Wording corrected 19 Sep, secondary audit S6; this previously read
"the robust loss is doing real work, exactly as the Candidate V1 analysis predicted".)*

### 10.4 Per-variant — is one variant carrying the result?

Module B MAE, and gain over median-ratio, by variant:

| Parameter | A MAE | B MAE | C MAE | gain A | gain B | gain C |
|---|---|---|---|---|---|---|
| IDDQ | 0.04034 | 0.02250 | 0.00961 | −0.61 % | +1.82 % | +1.37 % |
| Input_Leakage_Current | 0.00076 | 0.00661 | 0.00590 | **+13.49 %** | **+13.15 %** | **−1.55 %** |
| Active_Supply_Current | 1.44820 | 0.76932 | 0.90445 | +4.46 % | +6.37 % | +0.42 % |
| Propagation_Delay | 0.12979 | 0.08789 | 0.05127 | +5.44 % | +12.89 % | +10.56 % |
| Output_Rise_Time | 0.12842 | 0.04903 | 0.02589 | +8.52 % | +9.51 % | +7.18 % |
| Output_Fall_Time | 0.12590 | 0.04717 | 0.03044 | +7.52 % | +8.65 % | +9.90 % |

The timing gains hold across all three variants, which is what makes them credible.
Input leakage's gain is carried entirely by CMOS_A and CMOS_B and is slightly negative
on CMOS_C — a hint of the instability that §11 and §13 develop.

### 10.5 Bias and stability — what a pooled MAE hides

| Parameter | MAE | MedAE | P90AE | RMSE | MeanSignedError | UnderPredRate | MacroLotMAE | WorstLotMAE | nMAE % |
|---|---|---|---|---|---|---|---|---|---|
| IDDQ | 0.02412 | 0.01262 | 0.05341 | 0.05504 | −0.00606 | 0.471 | 0.02416 | 0.07265 | 3.79 |
| Input_Leakage_Current | 0.00442 | 0.00133 | 0.00587 | 0.04026 | −0.00213 | 0.479 | 0.00442 | 0.01795 | 5.02 |
| Active_Supply_Current | 1.04117 | 0.74259 | 2.24123 | 1.56732 | −0.22531 | 0.481 | 1.04367 | 2.61525 | 1.62 |
| Propagation_Delay | 0.08956 | 0.05262 | 0.17838 | 0.26799 | −0.02580 | 0.467 | 0.08972 | 0.22741 | 1.68 |
| Output_Rise_Time | 0.06773 | 0.03558 | 0.13531 | 0.20567 | −0.01671 | 0.467 | 0.06801 | 0.21548 | 2.05 |
| Output_Fall_Time | 0.06781 | 0.03578 | 0.13402 | 0.21565 | −0.01916 | 0.484 | 0.06840 | 0.37056 | 2.20 |

**Every parameter under-predicts on average.** `MeanSignedError` is negative on all six,
with 46.7–48.4 % of forecasts sitting low. This is expected — drift is positive and
right-skewed, and the deployed models are **Huber** regressors, whose objective
down-weights large residuals instead of chasing the mean. That is an empirically robust
fit; it is not an estimator of the conditional median, and describing it as one (as this
paragraph did before 19 Sep, secondary audit S3) overstates what the loss does. The bias
is smaller than the
median-ratio baseline's bias in every case. But it is **the dangerous direction for a
screening application**, so it is reported next to the MAE rather than buried.

`WorstLotMAE / MacroLotMAE` is the spread across held-out lots. `Output_Fall_Time` is
the widest at **5.4×**, `Input_Leakage_Current` next at 4.1×.

`RMSE ≫ MAE` on `Input_Leakage_Current` (0.040 vs 0.0044, a ratio of 9) is the
signature of a few very large errors among many small ones. §13 identifies them.

### 10.6 How close is this to the noise floor?

If forecast error were driven entirely by the assumed measurement noise, MAE would be
about `0.7979 × CV × level` (`E|N(0,σ)| = σ√(2/π)`).

| Parameter | median 168 h | assumed noise-floor MAE | Module B MAE | ratio |
|---|---|---|---|---|
| IDDQ | 0.63668 | 0.00508 | 0.02412 | **4.75×** |
| Input_Leakage_Current | 0.08808 | 0.00141 | 0.00442 | **3.15×** |
| Active_Supply_Current | 64.11858 | 0.25580 | 1.04117 | **4.07×** |
| Propagation_Delay | 5.34356 | 0.01492 | 0.08956 | **6.00×** |
| Output_Rise_Time | 3.30704 | 0.01187 | 0.06773 | **5.70×** |
| Output_Fall_Time | 3.08733 | 0.01109 | 0.06781 | **6.12×** |

**3.1× – 6.1× above the floor.** What this bounds is how much of the error the *assumed
measurement noise* can account for: most of it cannot be explained that way. It does
**not** show that the remainder is predictable from the 0 h and 24 h features Module B is
allowed to use — the residual may be process variation that no early measurement carries.
*(Wording corrected 19 Sep, secondary audit S4: this previously read "there is real
predictable drift still being missed", which asserts reducibility the measurement does not
establish. Candidate V1: 2.4×–5.0×. The problem got harder, consistent with stronger lot
ageing and larger late dispersion.)*

The floor is derived from **assumed** CVs and inherits that status.

### 10.7 The honest summary of §10

On FINAL-01, **all six deployed point models are Huber regressors**. Module B
**materially beats median-ratio on four parameters and ties it on two under the 5 % rule**
— on `IDDQ` and `Active_Supply_Current` a single per-variant constant is as good as the
fitted model. That is a defensible position and it is worth stating deliberately rather
than being caught out on it. Telling judges it beats the baseline on six would be false,
and the per-lot test is in the repository for anyone who checks.

*(Wording corrected 19 Sep, secondary audit S7. This previously read "a learned forecaster
for four parameters and a well-calibrated scaling rule for two", which describes the two
tied parameters as if a different kind of model were deployed for them. The same Huber
model is deployed for all six; what differs is whether it beats a constant.)*

---

## 11. Calibration — the 12 held-out lots

The calibration lots were never trained on and share no lot and no `component_id` with
train. This is a genuinely held-out score and the **last honest estimate of holdout
performance the team gets before the holdout itself.**

It is not for redesigning the model around. The protocol allows exactly one
pre-declared decision at this point, and that is §12.

### 11.1 The score

Model fitted on all 42 train lots, scored on the 12 calibration lots.
**Row-weighted pooled MAE:**

| Parameter | Module B | Median-ratio | Module B vs MR |
|---|---|---|---|
| IDDQ | 0.02104 | 0.02147 | +2.02 % |
| Input_Leakage_Current | **0.00402** | **0.00305** | **−31.51 %** |
| Active_Supply_Current | 1.05614 | 1.12043 | +5.74 % |
| Propagation_Delay | 0.07661 | 0.08254 | +7.19 % |
| Output_Rise_Time | 0.07378 | 0.07827 | +5.74 % |
| Output_Fall_Time | 0.07041 | 0.07925 | +11.16 % |

### 11.2 Did the cross-validation flatter the model?

| Parameter | CV (train) | Calibration | change |
|---|---|---|---|
| IDDQ | 0.02412 | 0.02104 | −12.79 % (better) |
| Input_Leakage_Current | 0.00442 | 0.00402 | −9.18 % (better) |
| Active_Supply_Current | 1.04117 | 1.05614 | +1.44 % |
| Propagation_Delay | 0.08956 | 0.07661 | −14.46 % (better) |
| Output_Rise_Time | 0.06773 | 0.07378 | +8.93 % |
| Output_Fall_Time | 0.06781 | 0.07041 | +3.84 % |

Span **−14.5 % to +8.9 %**, three parameters better and three slightly worse. The
absence of a one-direction shift is reassuring against a large *global* optimism
effect. *(Corrected 19 Sep, review finding F7: this paragraph previously called it
"the strongest single piece of evidence that the validation protocol is sound". It is
not. It compares **absolute** Module B MAE, which is confounded by whether these 12
lots are intrinsically easier, and it cannot see whether the **baseline-relative**
effect transferred. `Input_Leakage_Current` is the counter-example: its absolute MAE
improves by 9.2 % while its comparison against median-ratio reverses.)*

#### The diagnostic that does test the relative effect

Added 19 Sep, permitted data only — the median per-lot advantage over median-ratio,
computed the same way on the 42 CV lots and the 12 calibration lots
(`results/05_relative_effect_transfer.csv`):

| Parameter | CV median lot advantage | lots won | Calibration | lots won | shift |
|---|---|---|---|---|---|
| IDDQ | +1.27 % | 22/42 | +0.69 % | 7/12 | −0.58 pp |
| Input_Leakage_Current | +7.02 % | 34/42 | **+2.64 %** | 8/12 | **−4.39 pp** |
| Active_Supply_Current | +1.87 % | 25/42 | +4.04 % | 10/12 | +2.17 pp |
| Propagation_Delay | +7.90 % | 31/42 | +10.10 % | 8/12 | +2.19 pp |
| Output_Rise_Time | +9.23 % | 33/42 | +7.46 % | 9/12 | −1.76 pp |
| Output_Fall_Time | +6.34 % | 30/42 | +8.92 % | 9/12 | +2.58 pp |

**Five of six transfer within ±2.6 percentage points.** `Input_Leakage_Current`
shifts furthest and in the wrong direction — and note that even here the *typical
lot* keeps a +2.6 % advantage while the *mean* reverses to −33 %. The gap between
those two sentences is one component, and it is §13.

### 11.3 The paired test on 12 lots

Twelve lots has far less power than 42. A non-significant p here means *"not enough
lots to tell"*, **not** a contradiction of §10.2.

**Macro-lot MAE:**

| Parameter | Module B | Median-ratio | gain | lots won | p | verdict |
|---|---|---|---|---|---|---|
| IDDQ | 0.02074 | 0.02114 | +1.89 % | 7 / 12 | 0.569 | TIE |
| Input_Leakage_Current | 0.00410 | 0.00308 | **−33.08 %** | 8 / 12 | 0.970 | TIE |
| Active_Supply_Current | 1.04710 | 1.10928 | +5.61 % | 10 / 12 | 0.0269 | **BETTER** |
| Propagation_Delay | 0.07589 | 0.08178 | +7.20 % | 8 / 12 | 0.0772 | TIE |
| Output_Rise_Time | 0.07315 | 0.07776 | +5.93 % | 9 / 12 | 0.0640 | TIE |
| Output_Fall_Time | 0.06986 | 0.07877 | +11.31 % | 9 / 12 | 0.0923 | TIE |

`Active_Supply_Current` — a tie on the 42-lot CV — turns **BETTER** here at +5.6 %,
10 of 12 lots. The two results are not in conflict: +3.9 % and +5.6 % straddle a 5 %
line drawn for a reason.

`Input_Leakage_Current` **wins 8 of 12 lots and still loses on MAE by 33 %.** That
signature — better median, much worse mean — is the whole of §13.

### 11.4 Per-lot detail

Module B MAE by calibration lot:

| Lot | IDDQ | Leak | ActI | tPD | tRise | tFall |
|---|---|---|---|---|---|---|
| A_L10 | 0.04705 | 0.00076 | 1.33357 | 0.12972 | 0.12773 | 0.18205 |
| A_L12 | 0.02312 | 0.00041 | 1.15513 | 0.11179 | 0.15320 | 0.19865 |
| A_L18 | 0.03792 | 0.00055 | 1.50849 | 0.10891 | 0.10723 | 0.07119 |
| A_L24 | 0.03252 | 0.00069 | 1.55837 | 0.09564 | 0.14706 | 0.12323 |
| B_L11 | 0.01476 | 0.00157 | 0.76823 | 0.06526 | 0.03309 | 0.03291 |
| B_L13 | 0.01997 | 0.00242 | 0.69030 | 0.05946 | 0.07287 | 0.03121 |
| B_L22 | 0.01548 | 0.00241 | 1.23047 | 0.10383 | 0.06327 | 0.03693 |
| **B_L23** | 0.01573 | **0.01640** | 0.56110 | 0.08510 | 0.05177 | 0.06208 |
| C_L05 | 0.00808 | 0.00744 | 0.67179 | 0.03190 | 0.02661 | 0.01688 |
| C_L08 | 0.00507 | 0.00604 | 1.09387 | 0.03772 | 0.03381 | 0.03222 |
| C_L16 | 0.01545 | 0.00410 | 1.20161 | 0.05129 | 0.03987 | 0.02838 |
| C_L19 | 0.01378 | 0.00643 | 0.79228 | 0.03006 | 0.02125 | 0.02257 |

**B_L23's input-leakage MAE is 0.01640 — seven times the next-worst B lot.** One lot,
one parameter. §13 names the component.

---

## 12. The pre-declared decision — executed and spent

### 12.1 The rule, as written

Declared **14 Sep 2026**, before `ModuleB_Calibration.csv` existed, and carried forward
unexecuted through the V1 freeze:

> Move `Output_Fall_Time` from the timing feature set (`own+lot+cross`) to the
> current-group feature set (`own`) **if and only if both** hold on the calibration lots:
> **(a)** `own` beats `own+lot+cross` by more than **3 % MAE**, and
> **(b)** `own` wins on more than half the calibration lots.

The reason it existed: on Candidate V1, `own` scored *better* for fall time (7.6 % vs
6.2 % mean gain over median-ratio, 18 of 21 lots vs 15), and putting fall time in the
timing group cost 5.2 % on CMOS_C specifically. Rather than switch post-hoc — which
would have been exactly the cherry-picking the protocol forbids — the switch was
written down as a rule to be executed later, on data not yet seen.

### 12.2 One re-reading, recorded rather than done quietly

Condition (b) was originally written as "≥ 4 of 6 lots", because Candidate V1's
calibration file had six lots. **FINAL-01 ships twelve.** Applying "4 lots" literally
would silently weaken the rule from two-thirds of lots to one-third, so it was applied
as the proportion it was written to express: **more than half, ≥ 7 of 12.**

*(Ambiguity recorded 19 Sep, secondary audit S2. The two readings are not identical:
`≥ 4 of 6` is two-thirds, and a two-thirds translation onto 12 lots would be `≥ 8`, while
"more than half" gives `≥ 7`. The looser reading was used. The observed result — `own`
wins **2 of 12** — fails `≥ 4`, fails `≥ 7` and fails `≥ 8`, so D10's outcome is the same
under every reading and no interpretation was selected after seeing it.)*

It fails under either reading.

### 12.3 The result

| | `own+lot+cross` (frozen) | `own` (candidate) |
|---|---|---|
| MAE | 0.070410 | 0.071484 |
| MedAE | 0.032445 | 0.036255 |
| P90AE | 0.171572 | 0.172994 |
| RMSE | 0.130095 | 0.128228 |
| MeanSignedError | −0.024442 | −0.027077 |

| Condition | Threshold | Measured | Met? |
|---|---|---|---|
| (a) `own` MAE gain over `own+lot+cross` | > 3 % | **−1.525 %** (`own` is *worse*) | **NO** |
| (b) lots won by `own` | ≥ 7 of 12 | **2 of 12** | **NO** |

`own` wins only A_L10 and A_L24 — both CMOS_A, which is the variant where the timing
block's coupling is weakest (§9.2.5). That is internally consistent and it is not
enough.

### 12.4 Decision

**Neither condition met. The rule does not fire. `Output_Fall_Time` keeps
`own+lot+cross`. No configuration change.**

This is the rule working as intended: it was written to license exactly one change on
strong evidence, and the evidence is not there. **The rule is now executed and spent.**
It cannot be re-run on the holdout, and no second pre-declared decision exists.

---

## 13. Extrapolation risk — the finding, and how D11 closed

This was the most important open item in Module B and the direct answer to the brief's
*"it should not give false positives"*. **D11 closed on 19 Sep with the cap OFF** —
§13.7 gives the reasoning. The finding itself stands and is carried into freeze as a
known limitation.

### 13.1 The symptom

On the calibration lots, `Input_Leakage_Current` is **33 % worse** than a constant
median ratio, reversing its train-CV result. But it wins 8 of 12 lots. Both facts are
true because **one component of 906 carries 27.7 % of the parameter's entire calibration
error.**

| Parameter | calibration MAE | worst row's share of total error | top 5 rows | top 1 % |
|---|---|---|---|---|
| IDDQ | 0.02104 | 2.53 % | 8.83 % | 12.64 % |
| **Input_Leakage_Current** | 0.00402 | **27.73 %** | **42.15 %** | **45.21 %** |
| Active_Supply_Current | 1.05614 | 1.33 % | 4.34 % | 6.60 % |
| Propagation_Delay | 0.07661 | 3.23 % | 10.64 % | 13.91 % |
| Output_Rise_Time | 0.07378 | 2.58 % | 10.26 % | 13.67 % |
| Output_Fall_Time | 0.07041 | 1.23 % | 5.75 % | 9.63 % |

A parameter where one component of 906 carries a quarter of the total error does not
have an accuracy problem spread across the fleet. **It has one forecast that went
wrong**, which is a different thing to fix and a different thing to report.

### 13.2 The component, in full

```
component  C03478      lot B_L23      CMOS_B
  measured   0h    0.51133 µA
  measured  24h    0.69613 µA     early move   +36.14 %
  true      168h   1.04689 µA     true drift   +50.39 %   (from 24h)
  forecast  168h   2.05571 µA     predicted    +195.30 %
  absolute error   1.00882 µA  =  27.7 % of this parameter's total
                                  calibration error, from 1 row of 906
  static limit     1.0 µA (CMOS_B Input_Leakage_Current)
```

Remove that single row and Module B is **1.075×** median-ratio. Keep it and Module B
is **1.315×** worse. Nothing else about the parameter changes.

*(Wording corrected 19 Sep, secondary audit S1. This previously called 1.075× "a tie".
It is not: 1.075× is a **7.5 % MAE deficit**, outside the pre-declared 5 % tie band in
either direction. The tie rule is `metrics.verdict` — an effect smaller than 5 %, **or**
a per-lot paired test that does not reach α = 0.05 — and no such paired test was run for
the row-removed variant, so no verdict is claimed for it here. What the row removal
shows is where the error is concentrated, not a different verdict.)*

### 13.3 Why it happens

The `Input_Leakage_Current` training target has a very heavy right tail:

| Parameter | p01 | median | p99 | p99.9 | max | **max ÷ p99** |
|---|---|---|---|---|---|---|
| IDDQ | −0.0189 | 0.0290 | 0.1840 | 1.0543 | 2.7361 | 14.9× |
| **Input_Leakage_Current** | −0.0097 | 0.0357 | 0.2472 | 7.8097 | **13.3193** | **53.9×** |
| Active_Supply_Current | −0.0094 | 0.0172 | 0.0968 | 0.1757 | 0.2730 | 2.8× |
| Propagation_Delay | −0.0056 | 0.0147 | 0.1079 | 0.4071 | 1.2659 | 11.7× |
| Output_Rise_Time | −0.0076 | 0.0158 | 0.0986 | 0.3164 | 0.9774 | 9.9× |
| Output_Fall_Time | −0.0075 | 0.0168 | 0.1130 | 0.3034 | 0.7702 | 6.8× |

The largest training target is **13.3× the 24 h reading**, which is **54× its own 99th
percentile**. No other parameter exceeds 15×.

Huber downweights outliers **in the loss**. It does not stop the fitted function from
*returning* a drift far outside anything it should assert when a component's inputs
resemble a tail case. That is what happened here.

The emitted predicted relative deltas confirm it is confined to one parameter:

| Parameter | split | min | p99 | max | \|rel δ\| > 0.25 | > 0.50 | > 1.00 |
|---|---|---|---|---|---|---|---|
| IDDQ | train OOF | 0.017 | 0.046 | 0.190 | 0 | 0 | 0 |
| IDDQ | calibration | 0.015 | 0.046 | 0.105 | 0 | 0 | 0 |
| **Input_Leakage_Current** | train OOF | −0.017 | 0.104 | **1.966** | 3 | 2 | 2 |
| **Input_Leakage_Current** | calibration | −0.234 | 0.101 | **1.953** | 3 | 1 | 1 |
| Active_Supply_Current | train OOF | 0.004 | 0.032 | 0.056 | 0 | 0 | 0 |
| Active_Supply_Current | calibration | 0.001 | 0.033 | 0.046 | 0 | 0 | 0 |
| Propagation_Delay | train OOF | −0.013 | 0.049 | 0.164 | 0 | 0 | 0 |
| Propagation_Delay | calibration | −0.039 | 0.040 | 0.090 | 0 | 0 | 0 |
| Output_Rise_Time | train OOF | −0.014 | 0.044 | 0.137 | 0 | 0 | 0 |
| Output_Rise_Time | calibration | −0.029 | 0.040 | 0.075 | 0 | 0 | 0 |
| Output_Fall_Time | train OOF | −0.020 | 0.049 | 0.138 | 0 | 0 | 0 |
| Output_Fall_Time | calibration | −0.059 | 0.046 | 0.107 | 0 | 0 | 0 |

**Every other parameter stays inside ±0.19 on 4,057 forecasts.**

### 13.4 This is not a data bug

The training file genuinely contains those components. The model is extrapolating from
**real data, not corrupt data**. It is a modelling decision about what Module B is
willing to assert, and it belongs in `moduleb/config.py` — not in a message to Chaitany.

### 13.5 The proposal

A hard cap on the predicted relative delta, applied **after** the model and **before**
the output contract. Not a retune: the fitted coefficients are untouched. It is a
statement that Module B will not assert a drift larger than *c*.

*(Denominators corrected 19 Sep, review finding F5. This table previously said
"of 5,400", which silently counted the 1,343 holdout rows that have never been
predicted. Only train-OOF and calibration forecasts exist.)*

| cap | calibration (906 rows) | train OOF (3,151 rows) | Input_Leakage calibration MAE | effect on the other five |
|---|---|---|---|---|
| none (current) | — | — | 0.00402 | — |
| ±1.00 | 1 capped | 2 capped | 0.00328 (−18.2 %) | **untouched** |
| **±0.50** | **1 capped** | **2 capped** | **0.00290 (−27.7 %)** | **untouched** |
| ±0.25 | 3 capped | 3 capped | 0.00308 (−23.3 %) | **untouched** |

On the train OOF predictions those caps move MAE by +0.75 % / +0.05 % / −1.89 %
respectively — i.e. **nothing**.

So on the **4,057 forecasts that exist**, ±0.50 clips three: one calibration row and
two train-OOF rows, all `Input_Leakage_Current`. **No statement is made about how
many of the 1,343 holdout rows it would clip**, because the holdout has not been
predicted and will not be until after freeze.

### 13.6 Three honest caveats

1. **A cap also limits how alarming Module B can be.** On this very component both the
   true value (1.047 µA) and the capped forecast (0.696 × 1.5 = 1.044 µA) still exceed
   CMOS_B's 1.0 µA limit, so `B_FORECAST_EXCEEDS_LIMIT` **survives** — the flag was a
   *true* positive and stays one. That is reassuring for this case and is not a general
   proof.
2. **It is tuned against one component.** That is the thinnest possible evidence. It is
   defensible as a **fail-safe bound on what the model may assert**, not as an accuracy
   improvement, and it should be argued on the first ground only.
3. **±0.25 is worse than ±0.50 on this data** (−23.3 % vs −27.7 %), because it also
   clips two legitimate large-drift forecasts. The optimum is not monotone, which is
   itself a warning that the curve is being read off very few points.
4. **A cap justified independently of calibration would not have caught this.** The
   natural independent bound is "do not assert a drift larger than anything the
   training targets contain". For `Input_Leakage_Current` that is p99.9 = **7.81** or
   max = **13.32** — both far above the offending +1.95 forecast, so neither would
   clip it. The only train-derived bound tight enough is roughly p99 = **0.247**,
   which is well inside the range the training data says is legitimate and which
   would also start clipping timing forecasts (train-OOF maxima 0.137–0.190 against
   per-parameter p99 of 0.099–0.184). That has never been measured. **There is
   currently no independently-justified cap that is also effective.**

### 13.7 Status: **CLOSED, 19 Sep 2026 — D11 = LEAVE_OFF**

`moduleb.config.FORECAST_REL_DELTA_CAP` stays **`None`**. The code path remains,
documented and unit-tested, as a candidate safeguard for a future release. Four
reasons, in order of weight:

1. **The value would be selected after seeing calibration truth.** ±0.50 is
   attractive precisely because it is the value that most improves the one extreme
   calibration forecast. Calling it "not a retune" was too narrow — the coefficients
   are untouched, but choosing an inference transformation from observed calibration
   outcomes is still post-hoc pipeline selection, and the protocol allowed exactly
   one pre-declared calibration decision, which was the fall-time rule (§12) and is
   spent.
2. **The motivating case is not a false positive.** Both the true value (1.047 µA)
   and the forecast exceed CMOS_B's 1.0 µA limit, so `B_FORECAST_EXCEEDS_LIMIT` was
   *correct*. The defect is the magnitude of the assertion, not its direction. A cap
   fixes an exaggeration, not a false alarm.
3. **No independent bound exists that would have worked** — caveat 4 above.
4. **A hard cap can suppress a future legitimate extreme forecast**, and nothing in
   the evidence distinguishes the two cases.

**What would reopen it:** a cap fixed independently of the observed calibration
outcome — a source-backed engineering or physical assertion bound, or a genuinely
pre-specified train-only rule — followed by a calibration check showing it controls
the intended failure mode without creating materially worse misses.

Recorded in `docs/DECISION_LOG.md` as **D11 — LEAVE_OFF, closed 19 Sep 2026**.

---

## 14. The evidence layer, and the false-positive discipline

### 14.1 Why this module is the most conservative code in the package

A forecast that is 4 % off is a number someone can reason about. **A reason code that
fires on a third of the fleet is worse than no reason code at all** — it trains the
fusion layer and the operator to ignore it, and the one component that actually
mattered goes out with the crowd.

Module B's forecasts get checked against a target. Its reason codes do not: there is no
label saying "this component deserved a flag", and by design there never will be,
because the hidden truth is Sanskruti's and the disposition is fusion's. So the only
discipline available is to **measure how often each code fires and refuse to ship one
that fires so often it carries no information.**

### 14.2 The three design rules

1. **Reference class.** A component's primary parameter is *by construction* the one
   with its highest drift z. Ranking those primaries against the whole variant would
   flag roughly a third of them purely by that construction. So the drift flag uses an
   **absolute z threshold**, and envelope width is ranked **only among the components
   that this same parameter drives**.
2. **No invented limits.** The limit-based codes use the static limit itself as the
   threshold. Seven cells carry none, and those cells **never fire** — no default, no
   proxy, no "conservative" stand-in. A fabricated limit manufactures false positives
   that look authoritative.
3. **Qualifiers do not stand alone.** `B_NO_EARLY_SIGNAL` is true of roughly 40 % of
   components. On its own that is a fact about the dataset, not evidence about a part.
   It is emitted **only where a risk flag already fired**, where it reads as "this
   component is flagged, and the forecast behind the flag has no early evidence under
   it" — which is exactly the caveat fusion needs.

### 14.3 The six codes and their measured rates

Calibration lots, model and envelope fitted on train only:

| Code | Fires when | rate | n |
|---|---|---|---|
| `B_WIDE_ENVELOPE:<p>` | envelope width in the top decile among components this parameter drives | 10.93 % | 99 |
| `B_HIGH_FORECAST_DRIFT:<p>` | the primary parameter's predicted drift z ≥ 3 | 5.85 % | 53 |
| `B_LOT_OUTLIER_24H:<p>` | \|robust z\| ≥ 3 against the component's own lot at 24 h | 2.76 % | 25 |
| `B_NO_EARLY_SIGNAL:<p>` | 0→24 h move below the noise scale — **and a risk flag already fired** | 1.43 % | 13 |
| `B_FORECAST_EXCEEDS_LIMIT:<p>` | the forecast reaches an **available** static limit | 0.66 % | 6 |
| `B_ENVELOPE_REACHES_LIMIT:<p>` | the envelope does and the forecast does not | 0.55 % | 5 |
| **any code at all** | | **14.90 %** | **135** |

`B_WIDE_ENVELOPE` at ~11 % is *by construction* a top-decile ranking, so ~10 % is the
expected and correct value, not drift.

Train-OOF rates agree closely (any code 14.66 %), with the envelope-based codes mildly
optimistic there because the envelope is fitted on all train lots.

### 14.4 How many codes does a component carry?

| codes | components | % |
|---|---|---|
| 0 | 771 | 85.10 |
| 1 | 87 | 9.60 |
| 2 | 34 | 3.75 |
| 3 | 10 | 1.10 |
| 4 | 4 | 0.44 |

**85 % of components carry nothing.** That is the design goal: a worklist, not wallpaper.

### 14.5 Primary parameter distribution

Every component gets one, flagged or not. A wildly uneven distribution would mean the
scale-free z is not doing its job.

| Parameter | CMOS_A | CMOS_B | CMOS_C | total | % |
|---|---|---|---|---|---|
| IDDQ | 62 | 69 | 71 | 202 | 22.30 |
| Input_Leakage_Current | 65 | 60 | 77 | 202 | 22.30 |
| Active_Supply_Current | 61 | 55 | 53 | 169 | 18.65 |
| Propagation_Delay | 24 | 18 | 52 | 94 | 10.38 |
| Output_Rise_Time | 49 | 40 | 21 | 110 | 12.14 |
| Output_Fall_Time | 47 | 59 | 23 | 129 | 14.24 |

Spread 10–22 %, with sensible variant structure (CMOS_C's tight propagation-delay
headroom shows up as 52 primaries against 24 and 18).

### 14.6 The two structural guarantees, tested not asserted

- **No limit-based code fires for any of the seven cells with no `static_spec_max`.**
  Checked explicitly per code per parameter per variant: all zero. A unit test also
  feeds forecasts inflated by 10⁶ and asserts the codes still do not fire there.
- **`B_NO_EARLY_SIGNAL` never appears alone.** Measured: 0 components.

### 14.7 Acceptance

| Metric | Limit | Measured |
|---|---|---|
| any single code's firing rate | ≤ 25 % | **10.93 %** |
| components carrying any code | ≤ 60 % | **14.90 %** |

**PASS.** Every code passes the pre-declared sparsity gate. *(Corrected 19 Sep,
review finding A1: this previously read "sparse enough to be actionable". Sparsity
limits alert flooding. It does not establish precision, usefulness or downstream
actionability — and as §14.1 says, Module B has no correctness label for its codes
and by design never will.)*

---

## 15. The p95 envelope — what may and may not be claimed

### 15.1 Method

Conformalised gradient-boosted quantile regression (CQR — Romano, Patterson & Candès,
2019). A GBR with the pinball loss at τ predicts an upper quantile of the relative
drift; **six whole training lots** are held back to supply conformity scores, and the
finite-sample conformal quantile of those scores is added as an offset.

Holding back whole *lots* rather than random rows prevents any fit lot from also being
a calibration lot. The conformal quantile is the `ceil((n+1)(1−α))`-th smallest score;
when the required rank exceeds `n`, the answer is the maximum score, which is the
honest statement that this many calibration points cannot certify that level.

**What is and is not guaranteed** *(corrected 19 Sep, review finding F2).* This guide
previously said the `(n+1)` construction makes the result "finite-sample valid rather
than asymptotic". That is the textbook split-conformal statement, and it rests on the
calibration and test scores being **exchangeable**. Here they are not obviously so: the
conformity scores are computed **per component** inside the six held-back lots, and
this project treats components within a lot as dependent strongly enough to forbid
row-level significance testing everywhere else. Whole-lot holdback removes the leakage;
it does not turn correlated within-lot component scores into exchangeable calibration
units.

No cluster-conformal derivation has been produced for the score construction actually
implemented. So the defensible claim is the **empirical** one, and it is the one made
below: six complete training lots are withheld from envelope fitting, and marginal
coverage was then *measured* on twelve unseen calibration lots. That is an
out-of-lot measurement, not a theorem.

### 15.2 Measured on the calibration lots — **corrective run, 19 Sep 2026**

**Review finding F3.** Until 18 Sep the "tail" was ranked by `y_true − point`, the
forecast **residual**, while every document described it as the worst-drifting decile.
Those are different populations: a component can be badly under-predicted while barely
drifting, and a heavy drifter the model saw coming never enters the residual tail at
all. Worse, ranking by residual makes the tail definition depend on the forecast, so
changing the model silently changes which components are called the worst drifters.

The tail is now ranked by **observed relative drift from 24 h**, `(y₁₆₈ − x₂₄)/x₂₄` —
a property of the component and the truth alone. A unit test pins it: scrambling the
point forecast must not move the tail membership.

The 18 Sep figures are kept as
`results/09_envelope_coverage_SUPERSEDED_2026-09-18_residual_ranked.csv`. They are not
bad arithmetic; they measure a different quantity than the documents claimed. **Do not
quote them as tail coverage.**

**τ = 0.95, the operating point (corrected):**

| Parameter | marginal coverage | **tail coverage** | *(superseded)* | mean rel. width | conformal offset |
|---|---|---|---|---|---|
| IDDQ | 0.9669 | **0.6813** | *0.8022* | 7.66 % | 0.00917 |
| Input_Leakage_Current | 0.9735 | **0.7692** | *0.7363* | 10.04 % | 0.02247 |
| Active_Supply_Current | 0.9547 | **0.5934** | *0.6044* | 4.96 % | 0.01022 |
| Propagation_Delay | 0.9581 | **0.6044** | *0.6154* | 4.18 % | 0.01261 |
| Output_Rise_Time | 0.9327 | **0.4066** | *0.4725* | 4.43 % | 0.01036 |
| Output_Fall_Time | 0.9415 | **0.4505** | *0.5495* | 4.89 % | 0.00767 |

**Marginal coverage is unchanged** — it never depended on the tail definition. Tail
coverage falls on five of six parameters: the corrected range is **0.407 – 0.769**
against the superseded 0.473 – 0.802. The correction makes the envelope's limitation
*larger*, not smaller, so the conclusion below is strengthened rather than rescued.

"Tail coverage" is the fraction of the **worst-drifting decile** (91 components, ranked
by true relative drift) whose true value falls under the bound.

**The τ sweep**, to show the price of buying tail coverage:

| Parameter | tail @ 0.90 | tail @ 0.95 | tail @ 0.99 | width @ 0.95 | width @ 0.99 |
|---|---|---|---|---|---|
| IDDQ | 0.352 | 0.681 | 0.923 | 7.7 % | 17.8 % |
| Input_Leakage_Current | 0.440 | 0.769 | 0.967 | 10.0 % | **59.0 %** |
| Active_Supply_Current | 0.374 | 0.593 | 0.945 | 5.0 % | 7.7 % |
| Propagation_Delay | 0.319 | 0.604 | 0.945 | 4.2 % | 13.1 % |
| Output_Rise_Time | 0.187 | 0.407 | 0.857 | 4.4 % | 8.7 % |
| Output_Fall_Time | 0.220 | 0.451 | 0.978 | 4.9 % | 12.5 % |

### 15.3 The claim boundary

**MAY be said:** the envelope is **marginally calibrated** — across the whole
population its stated level (0.95) is close to the level it delivers (0.933–0.974).

**MUST NOT be said:** that it catches 95 % of the parts that drift worst. That is
conditional coverage on the tail, it is a different quantity, and it measures
**0.407–0.769**. A part inside its p95 envelope is **not thereby safe.**

Never "95 % safety guarantee", never "95 % defect detection". The envelope is
**evidence for the fusion layer; the outlier judgement belongs to Module A.**

**Worst case: `Output_Rise_Time` at 0.407** — the envelope misses nearly six of every
ten of its worst drifters. If anyone builds a fusion rule that treats "inside the
envelope" as a pass, that is where it fails first. Anushka needs that sentence, not
just the CSV.

*(Candidate V1 measured 0.38 at τ = 0.95, but on the old residual-ranked definition,
so it is not directly comparable to the corrected FINAL-01 figures.)*

---

## 16. The output contract and integration

### 16.1 What Anushka receives

One row per component, joined on `component_id`, **never by row number**. Fifteen
contract columns, in this order:

```
component_id
predicted_IDDQ_168h                     module_b_p95_IDDQ_168h
predicted_Input_Leakage_Current_168h    module_b_p95_Input_Leakage_Current_168h
predicted_Active_Supply_Current_168h    module_b_p95_Active_Supply_Current_168h
predicted_Propagation_Delay_168h        module_b_p95_Propagation_Delay_168h
predicted_Output_Rise_Time_168h         module_b_p95_Output_Rise_Time_168h
predicted_Output_Fall_Time_168h         module_b_p95_Output_Fall_Time_168h
module_b_primary_parameter
module_b_reason_codes
```

Plus **24 additive `evidence_*` columns**, four per parameter: the static limit (`NaN`
where none exists), the forecast as a fraction of that limit, the predicted relative
delta from 24 h, and the component's lot-relative deviation at 24 h. Ignore them and
nothing breaks; use them and fusion can apply its own thresholds instead of inheriting
Module B's.

**There is no `module_b_disposition`, and no `NOT_SET` placeholder.** Please do not add
one downstream and attribute it to Module B.

`module_b_reason_codes` is an **empty string** when nothing fired — the common case,
85 %. `module_b_primary_parameter` is never blank.

### 16.2 Calling it from the backend

```python
import pandas as pd
from moduleb import freeze, predict

ART = freeze.load_frozen("models/module_b_final01.joblib")   # once, at startup

def forecast(rows: pd.DataFrame) -> pd.DataFrame:
    out, report = predict.predict_frame(ART, rows, name="api")
    if not report.clean:
        for line in report.lines():
            log.warning(line)          # a clip happened — do not swallow it
    return out
```

`load_frozen` **raises** if the artifact was produced by a different `moduleb/config.py`
than the one running. A stale artifact scored as if it were the frozen model is worse
than a startup failure.

**Required input:** 16 columns — the four context columns and the six parameters at 0 h
and 24 h — for **a whole lot at a time**. Any `96h` or `168h` column present makes the
call **raise**, not warn.

#### The serving contract is cohort-level, not per component

*(Corrected 19 Sep, review finding F1. This section previously promised that "batch
size does not matter" and that one component gives the same answer as 1,343. That was
wrong, and the test cited for it did not exercise this code path.)*

Two parts of Module B read the other rows in the request:

- the three **timing** models use own-lot medians, recomputed by `add_features` from
  whatever is in the request;
- the **evidence layer** ranks each component's predicted drift against the other
  components of the same variant in the request, and ranks envelope width among the
  components a parameter drives.

Measured on calibration lot `B_L23`: scoring a component alone instead of with its lot
moves the timing forecasts by up to **7.18 %**, and `module_b_primary_parameter`
collapses to `IDDQ` for every single-row call, because with one row every robust z is
zero. The three current/leakage forecasts are bit-identical, since they carry no lot
terms.

So: **send the complete lot.** `predict_frame` refuses a request in which any lot
carries fewer than `moduleb.config.MIN_LOT_COHORT` (30) rows, with an error naming the
offending lots. `allow_partial_lot=True` proceeds anyway and sets
`report.partial_lot_override`, which makes `report.clean` false — at that point the
timing forecasts and every evidence column are computed against the partial cohort and
are **not comparable** to full-lot output.

This is not a restriction Module B invented for convenience. Burn-in is performed in
lots, the lot is what makes lot-relative context meaningful, and the frozen pipeline has
always scored whole cohorts — the 1,343-row holdout is eighteen complete lots in one
call. Only the *promise about the API* was wrong.

`MIN_LOT_COHORT` is deliberately outside the frozen configuration block and **does not
change the config digest**: it alters no fitted parameter and no forecast that was ever
valid. It converts a silently wrong output into an explicit error.

**Error handling:**

| Exception | Cause | API response |
|---|---|---|
| `LeakageError` | forbidden column, or stale artifact | 500 — a wiring bug, not bad user input |
| `DataQualityError` | null, duplicate id, non-positive value, unknown variant | 400 — reject the batch, name the failed check |
| `report.clean == False` | a forecast was clipped | 200, but log it; non-positive forecasts are not normal |

**Two properties that are unit-tested and can be relied on:** **row order** does not
change any forecast and the output preserves the input's order; and a rerun on the same
cohort is bit-identical. Cohort *composition* is a third thing entirely and is covered
above.

**Operational data must not retrain anything.** Live measurements entering the
operational demo must not modify or retrain the frozen benchmark model.

---

## 17. Acceptance criteria — current status

### Contract compliance — all MUST

| # | Criterion | Status |
|---|---|---|
| C1 | No `*_96h` column reaches any feature matrix | PASS |
| C2 | No `*_168h` value is used as a predictor | PASS |
| C3 | No hidden label column is readable | PASS |
| C4 | Every validation split is by whole lot | PASS |
| C5 | Train / calibration / holdout share no lot and no component | PASS |
| C6 | No static limit is invented for the 7 empty cells | PASS |
| C7 | No `module_b_disposition` column is emitted | PASS |
| C8 | Output matches `ModuleB_Output_Contract.csv` exactly | PASS |
| C9 | The holdout is opened by exactly one gated script | PASS |

### Fail-safe — all MUST

| # | Criterion | Status |
|---|---|---|
| F1 | No NaN or inf in any emitted forecast | PASS |
| F2 | No non-positive forecast is emitted | PASS |
| F3 | Every envelope value ≥ its point forecast | PASS |
| F4 | Output row count and `component_id` order match the input | PASS |
| F5 | Prediction identical across row order, and bit-identical on a rerun of the same cohort | PASS *(rewritten 19 Sep — the old criterion said "batch size" and was never tested)* |
| F5b | A request too small to support the lot features is refused, and a deliberate override is recorded | PASS *(new, F1)* |
| F6 | Prediction bit-identical on a rerun | PASS |
| F7 | A missing feature column at predict time raises, never zero-fills | PASS |
| F8 | A stale frozen artifact is refused | PASS |
| F9 | Every clipping guard reports what it did | PASS |

### Evidence quality — all MUST

| # | Criterion | Threshold | Measured | Status |
|---|---|---|---|---|
| E1 | No single `B_` code fires too often | ≤ 25 % | 10.93 % | PASS |
| E2 | Not too many components carry any code | ≤ 60 % | 14.90 % | PASS |
| E3 | `B_NO_EARLY_SIGNAL` never appears alone | 0 | 0 | PASS |
| E4 | Marginal coverage near τ | 0.95 ± 0.05 | 0.933–0.974 | PASS |
| E5 | Tail coverage measured and reported, never assumed | must be stated | 0.407–0.769, stated | PASS *(corrective run, F3)* |
| E6 | The tail population is defined by the truth, not by the forecast | must not move with the model | pinned by test | PASS *(new, F3)* |

### Model quality — SHOULD

| # | Criterion | Measured | Status |
|---|---|---|---|
| M1 | Beats median-ratio on ≥ 2 parameters, whole-lot CV | 4 of 6 | PASS |
| M2 | No parameter worse than median-ratio on train CV | none | PASS |
| M3 | No grid configuration beats the frozen one by > 5 % | max 4.52 % | PASS |
| M4 | Calibration MAE within ~15 % of CV MAE | −14.5 % to +8.9 % | PASS |
| M5 | `Input_Leakage_Current` calibration ≥ median-ratio | **−33 %** | **FAIL — open (§13)** |

**M5 is reported as a failure rather than reframed.** It is driven by the single
component in §13, and D11 closed with the cap **off**, so it stands as a known
limitation carried into freeze rather than an open decision.

### Not checkable in this environment

- Whether the holdout predictions are accurate. Only Sanskruti can score them, after
  the freeze, and asking earlier would defeat the exercise.
- Whether the declared measurement-noise CVs are true. They are assumptions from the
  design record, labelled as such wherever used.
- Whether the fusion layer uses the evidence columns correctly. That is Anushka's
  integration; §16 states the constraints.

---

## 18. Consolidated decision log

Newest first. Superseded entries are marked, never deleted.

| ID | Date | Decision | Status |
|---|---|---|---|
| **D12** | 19 Sep 2026 | Serving contract is **cohort-level**. `MIN_LOT_COHORT = 30` enforced in `predict_frame`; the single-component claim is withdrawn and its test replaced. Config digest unchanged. | closed (§16.2, F1) |
| **D11** | **19 Sep 2026** | `FORECAST_REL_DELTA_CAP` — **LEAVE_OFF**. The value would be post-hoc on calibration; the motivating case is a true positive with an exaggerated magnitude; no independently-justified bound is both available and effective. Code path kept, disabled. | **closed** (§13.7) |
| **D10** | 18 Sep 2026 | The pre-declared `Output_Fall_Time` rule **did not fire**: −1.5 % MAE, 2 of 12 lots. Keeps `own+lot+cross`. Rule spent. | closed (§12) |
| **D13** | 19 Sep 2026 | Tail coverage is ranked by observed relative drift, not by forecast residual. Stage 9 re-run as a corrective run; 18 Sep figures superseded and retained. | closed (§15.2, F3) |
| **D9** | 18 Sep 2026 | The frozen configuration stands. 4 of 6 beat the baseline; the 24-config grid finds nothing better by > 4.52 %. No change. | closed (§10) |
| **D8** | 18 Sep 2026 | FINAL-01 accepted with no escalation. Changes 1, 3, 4, 5 visible in the data; change 2 did not land on its own SNR measure — recorded, not a regeneration request. | closed (§9.3) |
| **D5** | 15 Sep 2026 | Standing instruction: no retraining or tuning until the new dataset is benchmarked with the same code. | **honoured** |
| **D4** | 15 Sep 2026 | FDI-5 / C4 retracted. TI SN74LVC00A gives tpd MIN 1 / TYP 3.5 / MAX 4.1 ns at 3.3 V ± 0.3 V and 25 °C, so 3.5 ns is a genuine typical and 5.5 → 4.1 was a correction. | closed |
| **D3** | 15 Sep 2026 | Five V2 generator changes accepted. Principle: the generator is not changed to improve Module B's MAE. | delivered |
| **D2** | 15 Sep 2026 | Architecture frozen for a fair V1 → V2 comparison: two feature groups, Huber ε 1.35 α 1e−3 on relative delta, pooled + variant one-hot, whole-lot GroupKFold 7 folds, CQR envelope τ 0.95. | **honoured** |
| **D1** | 15 Sep 2026 | Module B does not own the disposition. No `module_b_disposition` column at all. Do not invent missing static limits. | **honoured and tested** |

---

## 19. What was deliberately not done

Listing these explicitly, because each was a live option and each was declined for a
stated reason.

| Not done | Why |
|---|---|
| The holdout was not predicted on **before the freeze** | it is a one-shot. It was finally opened by stage 12 on 20 Sep 2026, after the freeze, exactly once *(row updated 20 Sep; before that date this read "was never predicted on", which was true when written)* |
| The model was not frozen **while any decision was open** | a freeze needs a recorded team sign-off and every decision closed. Both held on 20 Sep 2026 and stage 11 ran then |
| No configuration was changed to chase the grid | the best grid result is 4.52 % better, inside the tie threshold — switching would be leaderboard behaviour |
| The extrapolation cap was not enabled | D11 closed LEAVE_OFF: the value would be post-hoc on calibration and no independent bound is both available and effective (§13.7) |
| The reason-code reference distributions were not frozen from training | it would make single-component evidence stable, but it changes evidence semantics, needs a full firing-rate re-audit, and alters the digest — the cohort contract makes it unnecessary (F1) |
| The timing models' lot features were not removed to simplify serving | that is a model change under D2/D5, and the grid says no configuration change clears the tie threshold |
| A per-parameter train-p99 cap was not measured | it is a different and more principled proposal than ±0.50, but measuring it now, after seeing calibration, is the same post-hoc selection D11 rejected |
| The timing feature set was not split by variant, despite CMOS_A's weak coupling | D5 froze the configuration, and the grid says no change clears the threshold |
| Cross features were not added to the current group, despite new IDDQ ↔ Active_Supply structure | same |
| Huber's `max_iter` was not raised | nothing hit the cap; raising it would be a `FROZEN_V1` change for no reason |
| No dataset regeneration was requested | FINAL-01 is frozen; change 2's SNR miss is recorded, not escalated |
| Other members' ZIPs were never opened | the distribution rule |
| MAPE was never computed | input leakage runs to ~0.007 µA and a percentage metric would be dominated by its smallest denominators |

---

## 20. Open items, by person

### Chaitany
- **Nothing to escalate.** FINAL-01 passes every structural check.
- For the record only: generator change 2 (`Input_Leakage_Current` early SNR) did not
  land on the measure it was written against — SNR moved from ~0.7–0.9 to 0.50–0.74.
  **Not a request to regenerate.**

### Anushka
- **CHANGED 19 Sep — the serving contract is cohort-level.** Send whole lots. A request
  with any lot under 30 rows is refused; `allow_partial_lot=True` overrides it and marks
  the report not-clean. A one-component call is *not* equivalent to a full-lot call:
  timing forecasts move by up to 7.18 % and `module_b_primary_parameter` degenerates.
  This corrects a wrong promise in the previous integration note.
- The schema is final: **no `module_b_disposition`**, not even `NOT_SET`.
- **The p95 envelope is evidence, not a screen.** Tail coverage **0.407–0.769**
  (corrected 19 Sep). A fusion rule treating "inside the envelope" as a pass fails
  first on `Output_Rise_Time`, where it misses nearly six of every ten worst drifters.
- 14.9 % of components carry any reason code; the most common single code fires on
  10.9 %. Designed as a worklist.
- `evidence_<p>_limit` is `NaN` for seven variant × parameter cells. `NaN` means "no
  source-backed limit" — not zero, not a pass.
- The predict path is tested to be identical for one component or all of them.

### Tanisha
- The seven cells with no `static_spec_max` are unchanged: `Active_Supply_Current` on
  all three variants, `Output_Rise_Time` / `Output_Fall_Time` on CMOS_B and CMOS_C.
  **If any can be given a source-backed limit, that directly increases the evidence
  Module B can supply.**
- C4 is withdrawn (D4). The other Mock v1 device-spec items are not affected by this work.
- The declared measurement-noise CVs are `ASSUMED`, not measured. Anything that could
  turn them into `VERIFIED` (replicate measurements, even two repeats on a subsample)
  would let every module state an error floor instead of assuming one.

### Riddhi
- **Lot ageing structure is now real** where on Candidate V1 it was not — the lot share
  of late-drift variance moved from a flat 1.3–5.1 % to 1.16–17.76 %, strongest on
  `Active_Supply_Current` and CMOS_C timing. Lot-relative assumptions should behave
  differently, probably better.
- Interface only. No Module A labels or hidden anomaly truth enter Module B.

### Sanskruti
- Will receive `ModuleB_Final_Holdout_Predictions.csv` **after** freeze, for blind
  evaluation against the hidden 168 h targets.
- Nirmik will not ask for the targets, and will not change anything in response to the
  errors reported. A worse holdout score than calibration is an ordinary result.

### Nirmik — the remaining sequence
1. ~~Close **D11**~~ **done, 19 Sep — LEAVE_OFF** (§13.7).
2. `python scripts/11_freeze.py --team-signoff "<who, when>"`
3. `python scripts/12_predict_holdout.py --frozen` — **once**.
4. Send the CSV to Sanskruti and to Anushka, with `docs/INTEGRATION_NOTE.md`.
5. No retuning afterwards, whatever comes back.

---

## 21. Glossary

| Term | Meaning |
|---|---|
| **Burn-in / ESS** | running components hot and powered so latent defects surface before delivery |
| **Epoch** | a measurement checkpoint: 0 h, 24 h, 96 h, 168 h |
| **Lot** | a manufacturing batch; the unit of independence for every split and every test |
| **Whole-lot CV** | cross-validation where each fold holds out complete lots, never individual rows |
| **Macro-lot MAE** | mean of the per-lot MAEs — every lot weighted equally |
| **Row-weighted pooled MAE** | mean absolute error over all rows — every component weighted equally |
| **Relative delta** | `(x₁₆₈ − x₂₄) / x₂₄`, the quantity the model actually predicts |
| **Median-ratio baseline** | `x₂₄ ×` one constant per variant per parameter, fitted on training rows |
| **Persistence** | predict no drift: `x₁₆₈ = x₂₄` |
| **LinExtrap** | assume the first day's rate continues: `x₂₄ + (x₂₄ − x₀) × 6` |
| **CQR** | conformalised quantile regression — a quantile model plus a finite-sample conformal offset |
| **Marginal coverage** | fraction of all components whose true value falls under the bound |
| **Tail coverage** | the same fraction, restricted to the decile with the largest **observed relative drift from 24 h**. Corrected 19 Sep; it was previously the decile with the largest forecast residual, which is a different population |
| **Cohort** | the set of components in one prediction request. Module B's timing features and its whole evidence layer are cohort statistics, so the request must carry whole lots |
| **`static_spec_max`** | a source-backed datasheet limit; absent in 7 of 18 cells |
| **Config digest** | SHA-256 of the frozen configuration's *values*; changes when a number changes |
| **One-shot** | the holdout run: performed once, after freeze, never repeated |
| **Tie rule** | MAE differences under 5 % are ties regardless of rank or p-value |
| **`B_` namespace** | Module B's reason codes; observable evidence, never generator vocabulary |

---

## 22. Reproducing any of this

```bash
cd Desktop\SIH26170_ModuleB\08_final_01
pip install -r requirements.txt

python -m pytest tests/ -q        # 65 tests, ~80 s — do this first
python run_all.py                 # stages 0-10, 13, 14 — ~8.5 min
python run_all.py --quick         # skips the GBR half of the grid — ~2 min
python run_all.py --from 5        # resume at a stage
```

Every script prints the config digest it ran under. There is no hidden state and no
randomness outside `GLOBAL_SEED = 0`. To reproduce a table: check the digest matches,
rerun that stage.

The two gated stages are not run by `run_all.py`:

```bash
python scripts/11_freeze.py --team-signoff "<who approved, and when>"
python scripts/12_predict_holdout.py --frozen
```

---

## Appendix A — every results file and what it answers

| File | Answers |
|---|---|
| `00_input_hashes.csv` | which exact files produced everything else |
| `01_folds.csv` | the whole-lot fold map |
| `01_limit_headroom.csv` | how much static-limit headroom each cell has, and how many breaches |
| `01_ranges_by_variant.csv` | measurement ranges against the Device_Specs baseline and limit |
| `02_early_late.csv` | early vs late movement, and `r(early, late)` per variant |
| `02_drift_exponent.csv` | the implied time exponent `k` |
| `02_lot_variance_share.csv` | how much of the late drift is a lot effect |
| `02_early_snr.csv` | early move against the assumed noise floor |
| `02_cross_early_signal.csv` | whether other parameters' early moves predict this one's late drift |
| `03_cv_metrics.csv` | the full metric panel, all models × parameters × variants (**row-weighted MAE**) |
| `03_paired_lot_test.csv` | the per-lot paired test (**macro-lot MAE**) — the number to quote |
| `03_per_variant.csv` | per-variant MAE and gain |
| `03_noise_floor.csv` | distance from the assumed measurement-noise floor |
| `04_grid.csv` | all 24 configurations × 6 parameters |
| `04_best_vs_frozen.csv` | best in grid against the frozen configuration |
| `05_calibration_metrics.csv` | the metric panel on the calibration lots |
| `05_calibration_vs_cv.csv` | did the CV flatter the model |
| `05_calibration_paired_test.csv` | the paired test on 12 lots |
| `05_calibration_per_lot.csv` | which calibration lots are hard |
| `06_predeclared_falltime_decision.csv` | the executed pre-declared rule and its verdict |
| `06_predeclared_falltime_per_lot.csv` | its per-lot detail |
| `07_target_tails.csv` | how heavy each training target's right tail is |
| `07_predicted_rel_delta.csv` | the relative deltas the frozen model actually emits |
| `07_error_concentration.csv` | is a parameter's MAE really one component |
| `07_cap_sweep.csv` | what a relative-delta cap would do, at three levels |
| `08_reason_code_rates.csv` | every code's firing rate, by parameter and overall |
| `08_calibration_contract_sample.csv` | a full contract frame, as integration will receive it |
| `09_envelope_coverage.csv` | marginal and tail coverage at three τ values — **corrective run, 19 Sep**, tail ranked by true drift |
| `09_envelope_coverage_SUPERSEDED_2026-09-18_residual_ranked.csv` | the 18 Sep figures, kept for provenance. **Not** tail coverage |
| `05_relative_effect_transfer.csv` | does the per-lot advantage over median-ratio transfer from CV to calibration (F7) |
| `dryrun/` | the freeze + predict rehearsal artifacts |

## Appendix B — numbers at a glance

| | |
|---|---|
| Dataset | `SIH26170-FINAL-01`, `v4-final1`, `LOTSPLIT-05` |
| Rows / lots | 5,400 / 72 — train 3,151 / 42, calibration 906 / 12, holdout 1,343 / 18 |
| Variants | CMOS_A, CMOS_B, CMOS_C — 14 / 4 / 6 lots each per split |
| Config digest | `8d0621941f86fbb8…` |
| Folds | 7 whole-lot, 6 lots and 434–464 rows each |
| Cells with no static limit | 7 of 18 |
| Static breaches, train + calibration | 58 of 14,889 checkable cells (0.39 %), 10 cells |
| Drift exponent `k` | 0.577 – 0.803 |
| Lot share of late-drift variance | 1.16 % – 17.76 % |
| Early SNR | 0.50 – 1.18 |
| Parameters beating median-ratio (train CV) | **4 of 6** |
| Gains on those four | +6.83 % to +8.95 %, 30–34 of 42 lots, p ≤ 0.00145 |
| Best grid config vs frozen | ≤ 4.52 % — inside the tie threshold |
| MAE above assumed noise floor | 3.15× – 6.12× |
| Calibration vs CV MAE | −14.5 % to +8.9 % |
| Pre-declared fall-time rule | **did not fire** (−1.5 %, 2 of 12) |
| Components carrying any reason code | **14.90 %** |
| Highest single-code rate | 10.93 % (`B_WIDE_ENVELOPE`, a top-decile rank by construction) |
| Envelope marginal coverage @ τ 0.95 | 0.933 – 0.974 |
| Envelope **tail** coverage @ τ 0.95 | **0.407 – 0.769** (corrected 19 Sep) |
| Serving contract | **cohort-level**; whole lots, `MIN_LOT_COHORT = 30` |
| Unit tests | 65, all passing |
| Documented-claim checks | see `scripts/14_verify_claims.py` |
| Full pipeline runtime | 505 s |
| Open decisions | **0** — D11 closed LEAVE_OFF on 19 Sep |
| Model frozen | **no** |
| Holdout spent | **no** |

---

*End of guide. Companion documents in the same folder: `MODEL_CARD.md`,
`VALIDATION_SUMMARY.md`, `RUNBOOK.md`, `DECISION_LOG.md`, `INTEGRATION_NOTE.md`,
`ACCEPTANCE_CRITERIA.md`, `DATA_BUG_VS_MODEL_PROBLEM.md`, `FINDINGS_FOR_TEAM.md`,
`MASTER_PROMPT.md`, `CHATGPT_REVIEW_PROMPT.md`.*
