# Limitations — ModuleA-FINAL01

Written so that a reviewer finds nothing here they were not told.

## 1. The blind spot, named precisely

Not "static outliers". **Static offsets that stay inside specification.**

`results/05_blindspot.csv`:

| population | actual | detected |
|---|---:|---:|
| static, fails spec (both splits) | 7 | 7 |
| static, within spec (both splits) | 21 | 6 |
| all other behaviours (both splits) | 116 | 99 |

Detection tracks the ground truth's `static_fail_target` flag almost perfectly. The
published "8 of 10 on calibration, 4 of 18 on holdout" is the same detector at the same
threshold looking at two differently composed populations: calibration holds 6 of its
10 static outliers as spec failures, the holdout holds 1 of 18.

**This is a ceiling, not a deficiency of this candidate.** Nine statistics from five
families — top-k means at k ∈ {1,2,4,8}, the raw per-parameter extreme, two persistence
statistics, a late-epoch statistic, and robust within-lot Mahalanobis — all detect 4 to
7 of the 18 holdout static outliers at a matched 3% budget. The reason is visible in
Chaitany's own ground-truth audit: a SUBTLE anomaly's primary |z| is about 2.28, while
a healthy component's *maximum* across 24 parameter-epoch values routinely exceeds that
simply by being a maximum over 24 draws. The signal is real and it sits below the noise
floor of comparing a component to its lot.

Catching these needs a different kind of evidence — a physically motivated parameter
relationship, tighter measurement, or a deliberately accepted higher false-alarm rate.
It does not need another classifier.

## 2. The calibration split cannot see the blind spot

Four within-spec static offsets in calibration against seventeen in the holdout. Nothing
selected on calibration can be tuned for that failure mode, and no validation protocol
fixes a population that is not there. **This belongs in a note to whoever owns the
generator**, not in another modelling round.

## 3. The frozen weights did slightly worse on the holdout

PR AUC 0.8166 against the inherited weights' 0.8239; 1–2 fewer true positives at
matched workload. Inside the noise the calibration bootstrap already described, and
deliberately not acted on — see `docs/DECISION_LOG.md` D6. The freeze exists so that a
holdout result cannot rewrite a configuration chosen before it was seen.

## 4. Inherited conditioning that this release reduced but did not remove

The feature block, the rank transform and the top-k aggregation depths are inherited
from Better Potential's development, which used the full calibration set. This release
re-selects the **weights and the threshold** inside each fold, which is where the
selection pressure was; it does not re-derive the feature design. A genuinely pristine
estimate would require redesigning features under the nested protocol too.

## 5. The holdout is not an independent test

It has shaped RC1, RC2 and RC3 design discussions and now this release's reporting.
Every holdout number here is a comparison against prior runs. **A fresh lot-grouped
test set after design freeze is still required** before any performance claim leaves
the team.

## 6. Small denominators

54 calibration anomalies and 90 holdout anomalies. Differences of one or two components
are not distinguishable, which is why every comparison in this release carries a
bootstrap interval and why two of them are reported as ties.

## 7. Early epochs answer a narrower question

At 0 h and 24 h Module A reports observed deviation only. A component whose defect
begins at 168 h is not abnormal at 0 h, and is correctly dispositioned PASS. The low
early recall (15.6% at 0 h) is therefore not a miss rate in the usual sense, and should
never be quoted as one. Warning about future drift is Module B's question.

## 8. Synthetic data

`SIH26170-FINAL-01` is generated. The ceiling in §1 is a ceiling on *this generator's*
data. Nothing here supports a claim about real silicon, and the same generator producing
the same result is not evidence of real-world validity.

## 9. What has not been checked

- Behaviour on a variant outside CMOS_A/B/C — refused by design, never exercised.
- Behaviour under measurement units other than the release's.
- Any fusion rule. Module A's interaction with Module B's forecasts is not modelled
  here, and no learned B-confirmation policy exists.
- Runtime performance at production batch sizes.
