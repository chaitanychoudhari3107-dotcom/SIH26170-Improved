# Model card — ModuleA-FINAL01

**Release candidate** `ModuleA-FINAL01-RC1` · **Dataset** `SIH26170-FINAL-01` ·
**Frozen** 22 Sep 2026 · **Config digest** see `RELEASE_MANIFEST.json`

## What it does

Given a component's burn-in measurements, Module A reports whether it **already looks
abnormal** relative to (a) its variant's normal references, fitted on the train split,
and (b) the other components in its own lot.

It emits five contract fields — `component_id`, `module_a_score`,
`module_a_disposition`, `module_a_primary_parameter`, `module_a_reason_codes` — plus
additive diagnostic columns that fusion may ignore.

## What it does not do

- **It does not forecast.** Nothing here predicts a future measurement. That is Module B.
- **It does not decide.** It emits PASS or MONITOR only; the final
  PASS / MONITOR / REJECT belongs to fusion. The contract validator refuses a frame
  containing REJECT.
- **It does not identify root cause.** `module_a_primary_parameter` is the parameter
  with the strongest observed deviation. Two reasonable attribution methods on the same
  73 components agreed only 81% of the time, so the field ships with
  `module_a_attribution_margin` — the gap to the runner-up. A margin near zero is a
  coin toss between two parameters and should be shown to a reviewer as such.
- **It does not warn about defects that have not started.** At 0 h a component whose
  onset is at 168 h is not abnormal yet, and Module A says PASS. That is a correct
  answer to the question it was asked.

## How the score works

`module_a_score` is a single number in [0, 1] with a reserved band:

```
[0.00, 0.90)   statistical evidence      0.90 x weighted rank score
[0.90, 1.00]   out of specification      0.90 + 0.10 x how far past the datasheet limit
```

One threshold on it reproduces the disposition exactly. The published floor is in
`results/HOLDOUT_PREDICTION_RECEIPT.json` under `monitor_floor`. **Fusion should
threshold this column directly**; it does not need to reimplement anything.

The statistical part is the Better Potential formula: 60 features per component
(6 parameters × 4 raw epochs + 6 derived temporal), robust-z against the variant
reference and against the component's own lot, aggregated by top-k means into five
components, rank-transformed against calibration, then weighted.

**Weights: `lot_relative` 1.0, everything else 0.0.** Across 24 fold-selections
(12 leave-one-lot-out folds at each of two budgets) **no fold chose the inherited
`overall_extreme` component**, which is why it is dropped. At the shipped 1% budget the
folds split 6/6 between pure `lot_relative` and 0.9 `lot_relative` + 0.1 `temporal`;
the release ships the simpler of the two. Adopted for simplicity, not performance — the
difference against the inherited 0.90/0.10 weighting is a statistical tie both ways.
See `docs/VALIDATION_SUMMARY.md` §3 and §7.

**Operating threshold 0.9395405079**, the loosest cut whose out-of-fold calibration
false-alarm rate stays within 1%. Chosen at the curve's knee. This is a team-owned
number: changing it is a config edit, not a retrain, and the score stays comparable.

## Tiers

| tier | fires when | on this release |
|---|---|---|
| `CONFIRMED` | a measured value exceeds its datasheet `static_spec_max` | 81 flags, 81 anomalies, **0 normals** across all 5,400 components |
| `MONITOR` | statistical score at or above the operating threshold | 55 of the 78 holdout flags |
| `PASS` | neither | — |

The CONFIRMED tier is not a fitted threshold, which is why it is described separately.
Even so the claim is bounded: **no observed false positive in 5,076 normal components;
95% upper bound on the true rate 0.06%.** Not "never wrong".

Seven of eighteen variant × parameter cells have no datasheet limit
(`Active_Supply_Current` for all three variants, `Output_Rise_Time` and
`Output_Fall_Time` for CMOS_B and CMOS_C). They stay empty. No limit is interpolated,
borrowed from another variant, or derived from the data, so the CONFIRMED tier simply
cannot fire on those parameters.

## Performance

Honest nested estimate of the shipped configuration, weights and threshold both
selected inside the fold, at the 1% budget the release operates at:
**45 of 54 anomalies at 9 false alarms** (recall 83.3%, FPR 1.06%). The before-state —
inherited weights and cutoff — gives 44 of 54 at 7 false alarms under the same protocol.

Diagnostic holdout at 168 h: **65 TP, 13 FP, 25 FN** of 1,343 components, 78 flagged.
The holdout informed earlier redesign and is not an independent test.

Full tables, including the result that went the wrong way, in
`docs/VALIDATION_SUMMARY.md`.

## Training data

| split | rows | lots | role |
|---|---:|---:|---|
| train | 3,151 | 42 | variant reference medians and scales |
| calibration | 906 | 12 | rank references, weights, thresholds |
| holdout | 1,343 | 18 | scored once after freeze; diagnostic only |

**The train split is not anomaly-free.** The inherited handoff calls it a
"Normal-reference split"; the hidden ground truth records 180 anomalies among its 3,151
components, about 5.7%. The reference is fitted without labels and uses median and MAD,
which have a 50% breakdown point, so a contamination of this size does not move it
materially. The point is that it is disclosed and bounded, not that it is absent.

## Data quality behaviour

- A feature whose reference MAD is zero falls down a declared ladder — MAD, then
  IQR/1.349, then standard deviation — and **raises** if every rung is degenerate. It
  is never scored as `z = 0`, which would read as "perfectly normal". On this release
  no fallback was needed: all 180 variant-feature references used MAD
  (`results/01_scale_ladder.csv`).
- Same-lot statistics are computed only on a lot proved complete against external lot
  metadata. A count taken from the arriving batch is not a proof.
- Unknown variants, duplicate ids, non-positive measurements, mixed-variant lots and
  lots under 30 components are all refused rather than coerced.

## Intended use and misuse

**Intended:** one input to fusion, on complete lots of a known variant from
`SIH26170-FINAL-01`'s generator, as a screening aid that a human reviews.

**Not intended:** as a final disposition; as a root-cause identifier; on partial lots;
on an unknown variant; on real silicon. This is synthetic data and nothing here
supports a production claim.

## Known limitations

See `docs/LIMITATIONS.md` in full. The three that matter most:

1. **Static offsets that stay inside specification are largely invisible** — 6 of 21
   across both splits, against 7 of 7 for those that fail spec. Nine statistics from
   five families all land in the same place, so this is a ceiling of within-lot
   statistics rather than a deficiency of this candidate.
2. **The calibration split cannot be used to tune for that**, because it holds four
   such cases against the holdout's seventeen.
3. **The frozen weights ranked slightly worse on the holdout** than the ones they
   replaced — within noise, predicted by the calibration tie, and deliberately not
   acted on.
