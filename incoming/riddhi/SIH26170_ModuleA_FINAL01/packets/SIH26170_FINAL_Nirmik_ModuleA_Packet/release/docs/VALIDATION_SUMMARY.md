# Validation summary — ModuleA-FINAL01

Every figure here is checked mechanically by `scripts/10_verify_claims.py` against a
file in `results/`. Eighteen of eighteen checks pass.

---

## 1. Protocol

**Leave-one-lot-out over the 12 calibration lots.** The Better Potential core is
refitted for each held-out lot, so the rank reference never sees the lot it is scoring.
Uncertainty comes from a bootstrap over whole lots.

Repeated k-fold is not used, for a measured reason: with 12 lots,
`StratifiedGroupKFold` returns the same partition for every seed — 4 of 5 seeds gave a
byte-identical assignment when this was checked. Repeats would report a spread of zero
and imply a stability nobody measured.

For the headline estimate, the protocol is **nested**: an inner leave-one-lot-out over
the 11 training lots selects both the component weights and the threshold, so the
held-out lot sees a configuration chosen without it.

## 2. The honest estimate

`results/04_nested_validation.csv`. Four arms, so the cost of each layer of selection
is visible. **Every arm at the 1% budget the release actually ships at** — an arm read
at a different budget from the shipped configuration is not a comparison, which is a
mistake this document made in an earlier revision and which
`scripts/10_verify_claims.py` caught.

| arm | what was selected inside the fold | TP/54 | FP | recall | FPR |
|---|---|---:|---:|---:|---:|
| inherited | nothing — 0.90/0.10 weights and the 0.936978 cutoff | 44 | 7 | 81.5% | 0.82% |
| threshold | the threshold only | 44 | 10 | 81.5% | 1.17% |
| full | weights and threshold, unconstrained | 45 | 10 | 83.3% | 1.17% |
| **shipped** | **the configuration this release ships** | **45** | **9** | **83.3%** | **1.06%** |

**The headline is 45 of 54 at 9 false alarms.** The shipped configuration gains one
anomaly and two false alarms over the before-state at the same budget. That is a small
gain and it is stated as one.

At a 3% budget the same four arms give 44/7, 47/26, 48/25 and 48/25
(`results/04_nested_validation_cap03.csv`). The recall is higher everywhere and so is
the workload; the comparison between arms is what carries over, not the absolute figures.

The `shipped` arm is the only number in the history of this module that estimates the
whole procedure out of sample at the budget it operates at. RC2 grouped only its
residual classifier; RC3 refitted the rank reference per fold but kept the legacy
weights frozen. Both disclosed it; neither removed it.

## 3. What the weight search found, and what it did not

**Across all 24 fold-selections — 12 folds at each of two budgets — not one chose the
inherited `overall_extreme` component.** That is the robust finding, and it is why the
release drops it.

What the folds chose *instead* is budget-dependent, and the earlier revision of this
document overstated it:

| budget | pure `lot_relative` | 0.9 `lot_relative` + 0.1 `temporal` |
|---|---:|---:|
| 3% | 12 of 12 | 0 |
| **1% (shipped)** | **6 of 12** | **6 of 12** |

So "all twelve folds agreed" is true only at the 3% budget. At the budget the release
ships at, the folds split evenly between the two survivors. Both are dominated by
`lot_relative`; neither keeps `overall_extreme`.

The release ships pure `lot_relative` because it is the simpler of the two survivors —
one component rather than two — and because the choice between them is a coin flip on
this evidence. That is a weaker justification than unanimity and it is the accurate one.
It is **not** adopted because it scores better:

| comparison | PR AUC difference | 95% CI | verdict |
|---|---:|:---:|---|
| selected vs inherited weights, calibration | +0.0008 | [−0.0081, +0.0171] | **tie** |

A difference whose interval contains zero is a tie. The tiebreaker applied here is
simplicity: one component instead of two, and nothing else changed.

## 4. The operating point

`results/03_operating_points.csv`, leave-one-lot-out on calibration.

| FPR budget | threshold | TP/54 | FP | recall | precision | flagged |
|---|---:|---:|---:|---:|---:|---:|
| 0.5% | 0.947942 | 43 | 4 | 79.6% | 91.5% | 47 |
| **1% (frozen)** | **0.939541** | **47** | **8** | **87.0%** | **85.5%** | **55** |
| 2% | 0.926150 | 48 | 17 | 88.9% | 73.9% | 65 |
| 3% | 0.918984 | 48 | 24 | 88.9% | 66.7% | 72 |
| 5% | 0.899038 | 48 | 42 | 88.9% | 53.3% | 90 |
| 10% | 0.854067 | 49 | 85 | 90.7% | 36.6% | 134 |

The curve has a knee at 1%. Moving to 3% buys one more anomaly of 54 and costs sixteen
more false alarms; moving to 10% buys two and costs seventy-seven. The 3% figure used
in the RC2 and RC3 work was a development budget, not an operational requirement, and
this release does not inherit it.

Also recorded for completeness: a threshold tuned to **zero** false positives on the
852 calibration normals sits at 0.956835 and catches 38 of 54 (70.4%). That is a
fitted quantity on 852 parts and will not stay at zero on an unseen lot. It is not
where the CONFIRMED tier comes from.

## 5. The tier that has no false positives

`results/02_spec_witness.csv`. The rule: any parameter measured above its own
`Device_Specs` `static_spec_max` at the scored epoch.

| split | components | normals | flagged at 168 h | true positives | **false positives** |
|---|---:|---:|---:|---:|---:|
| TRAIN | 3,151 | 2,971 | 45 | 45 | **0** |
| CALIBRATION | 906 | 852 | 13 | 13 | **0** |
| HOLDOUT | 1,343 | 1,253 | 23 | 23 | **0** |

**81 flags across the whole release, 81 real anomalies, zero normals.** This is not a
fitted threshold — a part above its datasheet maximum is out of specification by
definition — so there is nothing for it to overfit and nothing to drift on an unseen lot.

The honest statement, and the one used everywhere in this release: *no observed false
positive in 5,076 normal components; 95% one-sided upper bound on the true rate,
**0.06%***. Not "never wrong".

What it does not do: it catches about a quarter of anomalies on its own and adds no
detections the statistical score misses on this release. Its value is certification —
marking which flags are certain — not recall.

## 6. Holdout — diagnostic

`results/09_holdout_metrics.csv`. The holdout shaped RC1, RC2 and RC3 design
discussions. It is not an independent test and nothing below is a generalisation claim.

| epoch | TP | FP | FN | recall | precision | FPR | flagged |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 h | 14 | 32 | 76 | 15.6% | 30.4% | 2.55% | 46 |
| 24 h | 19 | 32 | 71 | 21.1% | 37.3% | 2.55% | 51 |
| 96 h | 32 | 31 | 58 | 35.6% | 50.8% | 2.47% | 63 |
| **168 h** | **65** | **13** | **25** | **72.2%** | **83.3%** | **1.04%** | **78** |

Tiers at 168 h (`results/09_holdout_tiers.csv`):

| tier | components | anomalies | normals |
|---|---:|---:|---:|
| CONFIRMED | 23 | 23 | **0** |
| MONITOR | 55 | 42 | 13 |
| PASS | 1,265 | 25 | 1,240 |

Early-epoch recall is low and is *supposed* to be. At 0 h a defect whose onset is later
has not happened yet; those rows are not missed detections, they are components that
were not yet abnormal. Detection of an already-active deviation and warning of a future
one are different questions, and Module A only answers the first.

## 7. The result that went the wrong way

**The weight change did not transfer to the holdout.** On the holdout the frozen
configuration ranks slightly *worse* than the weights it replaced
(`results/09_ranking_comparison.json`):

| | PR AUC | ROC AUC | TP at 78 flags | TP at 100 flags |
|---|---:|---:|---:|---:|
| frozen FINAL-01 (lot_relative 1.0) | 0.8166 | 0.9418 | 65 | 70 |
| inherited (0.90 / 0.10) | 0.8239 | 0.9416 | 67 | 72 |

Two true positives at matched workload, well inside the noise the calibration bootstrap
already described — the two weightings were a statistical tie there and they are a
statistical tie here, with the sign happening to flip.

**This is not grounds to reopen the freeze.** The configuration was selected without
seeing the holdout, by a protocol chosen in advance, and unanimously. Changing it now
because of a holdout result is precisely the failure mode the freeze exists to prevent,
and it would make every number in this document unverifiable. It is recorded here, in
`docs/DECISION_LOG.md` as D6, and in the model card's limitations.

## 8. Behaviour breakdown, 168 h holdout

`results/09_holdout_by_behaviour.csv`.

| behaviour | actual | detected |
|---|---:|---:|
| ACCELERATING_DRIFT | 17 | 17 |
| LATE_STEP | 18 | 17 |
| GRADUAL_DRIFT | 19 | 16 |
| MULTIVARIATE_SHIFT | 18 | 10 |
| STATIC_OUTLIER | 18 | 5 |

The static-outlier row is the wrong unit — see `docs/LIMITATIONS.md` §1.

## 9. What was checked in software

38 tests, `SIH26170_RELEASE=... python -m pytest tests -q`. They establish specific
software behaviours, not model generalisation. Among them:

- a 168 h column set to 1e6 does not change any 24 h score;
- a batch missing part of a lot is refused, and a batch that counts *itself* as
  complete is still refused when external lot sizes disagree;
- the frozen artifact round-trips to a byte-identical prediction frame;
- a frame whose score disagrees with its own disposition — the RC2 defect — is refused;
- a component with zero weight is never named as a reason;
- a constant reference raises rather than being scored as normal;
- the rewritten scoring path reproduces the inherited Better Potential core exactly
  under the inherited weights, so the rewrite fixed defects without quietly changing
  the model.
