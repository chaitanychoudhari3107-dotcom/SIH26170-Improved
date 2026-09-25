# Module A → Chaitany · data

**Model** `ModuleA-FINAL01` · **package** `final01.5.0` · dataset `SIH26170-FINAL-01` ·
state **HOLDOUT_PREDICTION_DELIVERED**
**Model digest** `2b2fa4da5ee36e7c…` · **runtime digest** `d73ea59a16361e23…` ·
**source digest** `e6d86298540fc98b…` (at freeze `820d0201e3162a07…`)
**Sign-off** RECORDED · **holdout run** SPENT · **build mismatch** False

All six packets carry the same `RELEASE_IDENTITY.json`. If two disagree on
**model_config** or **runtime_contract**, one is from a different build and must not be
used. `source_tree` moving on its own is explained in `PROVENANCE_ADDENDUM.json`.

Two findings about `SIH26170-FINAL-01` that belong to the dataset rather than the model.
Neither is a request to regenerate FINAL-01, which stays frozen.

## 1 · The train split is not a "Normal-reference split"

The handoff describes it that way. The hidden ground truth records **180 anomalies among
its 3,151 components**, about 5.7%.

Nothing is broken by it — Module A fits its reference without labels, and median and MAD
have a 50% breakdown point, so 5.7% contamination does not move them materially. But the
description is wrong and has been corrected everywhere in this release.

Detectable without opening a label: 45 train components exceed
a datasheet `static_spec_max`, which is only possible if the split is not anomaly-free.

## 2 · Calibration and holdout are composed very differently for one defect class

This one matters.

| | calibration | holdout |
|---|---:|---:|
| static outliers that **fail** spec | 6 of 10 | 1 of 18 |
| static outliers rated SUBTLE | 3 of 10 | 10 of 18 |

Detection tracks that flag almost perfectly: **7 of 7** caught where spec fails,
**6 of 21** where it does not.

So the published "8 of 10 on calibration, 4 of 18 on holdout" is one detector at one
threshold looking at two different populations — not a model that degrades.

**The consequence is the ask.** Nothing selected on calibration can be tuned for
within-spec static offsets, because calibration contains four of them against the
holdout's seventeen. No validation protocol fixes a population that is not there.

**Request:** balance `static_fail_target` across splits in the next dataset version. Same
generator, new seeds — F3 in `docs/FUTURE_RELEASE_ITEMS.md`.

## What is in here

`data_findings/` holds `01_audit.json`, `02_spec_witness.csv`,
`05_static_composition.csv` and `05_blindspot.csv`; `docs/LIMITATIONS.md` sections 1–2
has the reasoning.
