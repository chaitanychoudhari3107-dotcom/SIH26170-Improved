# Master prompt — the confusion matrix, and what it obliges

Standing brief for every result this release reports. It sits under
`docs/MASTER_PROMPT.md` and `docs/MASTER_PROMPT_DEPLOYMENT.md`; where they overlap,
they win.

This exists because every headline number in Module A is a view of four integers, and
quoting one view without the others is the most ordinary way an honest engineer
oversells a model.

---

## The four outcomes

Every component Module A scores lands in exactly one cell. There is no fifth case, and
no component is in two.

|  | **truly abnormal** | **truly healthy** |
|---|---|---|
| **Module A flagged it** (MONITOR) | **TP** — true positive | **FP** — false positive |
| **Module A passed it** (PASS) | **FN** — false negative | **TN** — true negative |

What each one costs **on this problem**, which is the part that decides anything:

- **TP** — an abnormal component was caught. The screen worked.
- **TN** — a healthy component was passed. The screen stayed out of the way. This is
  most of the data and it is not free: every TN is a part nobody had to look at.
- **FP** — a **healthy** component was flagged. Costs a reviewer's time. Nobody is
  harmed; someone is inconvenienced. On the 168 h holdout there are 13 of these.
- **FN** — an **abnormal** component was passed. A real defect goes to the next stage.
  This is the expensive error for ISRO, the one Chaitany asked to minimise, and there
  are 25 of them on the holdout.

`TP + TN + FP + FN = N`, always, and `modulea.metrics.confusion` asserts it rather than
assuming it. If that assertion ever fires, a truth value that is neither 0 nor 1 has
leaked in, or a NaN has reached the prediction vector.

## Every rate is a view of those four

Nothing else is measured. All of these come out of the same four integers:

```
recall / TPR / sensitivity  = TP / (TP + FN)   of the abnormal parts, how many caught
FNR  (the missed-defect rate)= FN / (FN + TP)  = 1 − recall
specificity / TNR           = TN / (TN + FP)   of the healthy parts, how many left alone
FPR (the false-alarm rate)  = FP / (FP + TN)   = 1 − specificity
precision / PPV             = TP / (TP + FP)   of what we flagged, how much was real
NPV                         = TN / (TN + FN)   of what we passed, how much was fine
accuracy                    = (TP + TN) / N
F1                          = 2TP / (2TP + FP + FN)
```

**Accuracy is not reported as a headline anywhere in this release and must not be.**
With 90 anomalies in 1,343 components, a model that flags nothing scores 93.3% accuracy
and catches no defects at all. Every metric with `TN` in the numerator is inflated by
the class imbalance here.

## The obligations

**1 · Report all four cells, or say which you are omitting and why.**
"72.2% recall" is true and nearly useless on its own. "65 caught, 25 missed, 13 healthy
parts flagged, 1,240 left alone" is the same fact and tells a reviewer what their day
looks like. `results/20_confusion_matrices.csv` carries all four for every result the
release quotes, and `scripts/20_confusion_matrix.py` regenerates it.

**2 · Never pair a recall from one operating point with a false-alarm count from
another.** This has gone wrong once already: the headline nested estimate was quoted
from a 3% budget run while the release ships at 1%. A confusion matrix is a single
joint measurement at a single threshold. Splitting it across thresholds produces a
model that does not exist.

**3 · An undefined rate is NaN, never 0.0.** A lot with no anomalies has no recall —
it cannot have failed to catch something that was not there. Printing 0.0 in that cell
reads as a failure that never happened, and `results/14_per_lot.csv` has three such
lots.

**4 · Cross-check the implementation, do not trust it.** `modulea.metrics.confusion` is
hand-rolled and everything depends on it. Swap the FP and FN expressions and the
arithmetic still balances, every rate still lands in [0, 1], and the table still looks
right — while the release claims it misses defects it catches. So:
`tests/test_confusion_matrix.py` compares every cell against
`sklearn.metrics.confusion_matrix` on randomised inputs and pins the orientation with
hand-written single-component cases; `scripts/20_confusion_matrix.py` repeats that
cross-check on the release's own data, every run.

**5 · State the population.** "65 TP" means nothing without "of 90 anomalies among
1,343 components". Every row in `20_confusion_matrices.csv` carries `n`, `positives`
and `negatives` for this reason.

**6 · A tier's matrix is not the model's matrix.** The CONFIRMED tier scores 23 TP,
0 FP, 67 FN, 1,253 TN on the holdout — precision 1.000 and recall 0.256. Reporting its
precision as the model's precision would be a serious misrepresentation. Tiers are
reported as separate rows, labelled.

**7 · Holdout matrices are DIAGNOSTIC.** The holdout shaped RC1, RC2, RC3 and this
release's reporting. Every cell derived from it is a comparison against prior runs, not
evidence of generalisation.

## What the four cells say about this release

From `results/20_confusion_matrices.csv`, the two that matter:

| result | TP | TN | FP | FN | recall | precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|
| calibration, out of fold, shipped config | 47 | 844 | 8 | 7 | 87.0% | 85.5% | 0.94% |
| holdout 168 h, frozen release (diagnostic) | 65 | 1,240 | 13 | 25 | 72.2% | 83.3% | 1.04% |

And the tier the release leans on, across **all 5,400 components** in the dataset:

| datasheet limit rule | TP | TN | **FP** | FN |
|---|---:|---:|---:|---:|
| train + calibration + holdout | 81 | 5,076 | **0** | 243 |

Zero false positives, 5,076 true negatives. And the honest form of that claim, which is
the one used everywhere: **no observed false positive in 5,076 healthy components, 95%
upper bound on the true rate 0.06%.** Not "never". The 243 false negatives in that row
are why the rule certifies rather than detects — on its own it catches a quarter of the
anomalies, and that is stated wherever its precision is.

## Before saying "ready for integration"

- `scripts/20_confusion_matrix.py` runs clean: every matrix balances, every row agrees
  with sklearn.
- `tests/test_confusion_matrix.py` passes — 72 tests, including the transposition guard.
- No document quotes a rate without its cells being reachable in `results/`.
- No document quotes accuracy as a headline.
- Every holdout figure is labelled DIAGNOSTIC.
