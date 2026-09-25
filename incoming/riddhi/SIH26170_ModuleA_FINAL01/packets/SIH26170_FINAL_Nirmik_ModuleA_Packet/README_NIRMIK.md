# Module A → Nirmik · owner · full release custody

**Model** `ModuleA-FINAL01` · **package** `final01.5.0` · dataset `SIH26170-FINAL-01` ·
state **HOLDOUT_PREDICTION_DELIVERED**
**Model digest** `2b2fa4da5ee36e7c…` · **runtime digest** `d73ea59a16361e23…` ·
**source digest** `e6d86298540fc98b…` (at freeze `820d0201e3162a07…`)
**Sign-off** RECORDED · **holdout run** SPENT · **build mismatch** False

All six packets carry the same `RELEASE_IDENTITY.json`. If two disagree on
**model_config** or **runtime_contract**, one is from a different build and must not be
used. `source_tree` moving on its own is explained in `PROVENANCE_ADDENDUM.json`.

Everything, plus the three things that need a decision from you.

## Three decisions

**1 · The operating point.** Frozen at a 1% calibration false-alarm budget, chosen at the
curve's knee. Moving to 3% buys one more anomaly of 54 and costs sixteen more false
alarms. This is a config edit and a re-freeze, not a retrain — the score is unchanged and
the whole curve is already measured (`03_operating_points.csv`). Decision D2 is closed in
code and **open in substance** until someone states a review capacity or a cost ratio.

**2 · Calibration-split Module B forecasts.** The highest-value item open, and you own
both modules so it is one decision. Where Module B corroborates Module A on the same
parameter, 19 of 19 holdout components are real
anomalies, against a much lower rate without. Unusable today: the only data with both
modules and labels is the holdout. One prediction run of a model that already exists
makes it fittable. F1 in `docs/FUTURE_RELEASE_ITEMS.md`.

**3 · A fresh lot-grouped test set.** Until it exists, nothing here should be presented
to judges as a performance claim. F2.

## State

| | |
|---|---:|
| tests | 151 passed |
| claim checks | 166, 0 failed |
| reproducibility | 47 of 47 files identical across two independent runs |
| robustness cases | 19, 0 failures |
| config digest | unchanged since freeze |
| holdout run | SPENT |

Shipped nested estimate: **45 of 54 at 9 false alarms**.
Holdout at 168 h: **65 TP, 13 FP, 25 FN**,
78 flagged, of which 23 CONFIRMED with zero normals.

## What is in here

The complete release, all six packets, and the three master prompts. `CONTINUATION.md`
and `state/CHECKPOINT.json` mean any session can resume this work without conversation
history.

`docs/MASTER_PROMPT_FINAL_VERIFICATION.md` is the protocol for the two independent
re-runs. It has already been executed once and the result is in
`results/19_reproducibility.csv`.

## The two things I would not let pass without saying

**The weight change did not transfer to the holdout.** The frozen configuration ranks
slightly *worse* there than the weights it replaced — PR AUC 0.8166 against 0.8239, one
to two fewer true positives at matched workload. Inside the noise the calibration
bootstrap described, and deliberately not reverted (D6), because a configuration chosen
before the holdout was seen cannot be rewritten by it without making every other number
unverifiable.

**The blind spot is a ceiling, not a to-do.** Within-spec static offsets are caught
6 of 21. Nine statistics from five families all
land in the same place. Catching them needs different evidence — Tanisha's physical
relationship, tighter measurement, or an accepted higher false-alarm rate — not another
classifier.
