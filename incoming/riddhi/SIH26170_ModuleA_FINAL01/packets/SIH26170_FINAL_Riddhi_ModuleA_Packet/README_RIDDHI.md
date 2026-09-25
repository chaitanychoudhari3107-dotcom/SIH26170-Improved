# Module A → Riddhi · Module A history

**Model** `ModuleA-FINAL01` · **package** `final01.5.0` · dataset `SIH26170-FINAL-01` ·
state **HOLDOUT_PREDICTION_DELIVERED**
**Model digest** `2b2fa4da5ee36e7c…` · **runtime digest** `d73ea59a16361e23…` ·
**source digest** `e6d86298540fc98b…` (at freeze `820d0201e3162a07…`)
**Sign-off** RECORDED · **holdout run** SPENT · **build mismatch** False

All six packets carry the same `RELEASE_IDENTITY.json`. If two disagree on
**model_config** or **runtime_contract**, one is from a different build and must not be
used. `source_tree` moving on its own is explained in `PROVENANCE_ADDENDUM.json`.

Your three packages — Better Potential, RC2 Hybrid, RC3 Specialist — are preserved and
still runnable exactly as shipped. Nothing was modified. This is what measuring them
under one protocol showed.

## The core survives; the add-ons do not

**Better Potential's scoring formula is the release.** The rewritten path reproduces it
bit for bit under the inherited weights — `tests/test_equivalence.py` asserts a maximum
absolute difference of 0.0 and refuses to run if that ever stops being true.

What changed is narrower than it looks: the aggregation depths are named parameters
instead of slice literals, the reference scales refuse a degenerate MAD instead of
scoring it as `z = 0`, and the component weights were re-selected under a nested
protocol.

## The structural finding

RC2's and RC3's `core_score` columns are **bit-identical to each other**, and Better
Potential's 73 flags are a **strict subset of both**. All three were one detector plus a
different bolt-on — not three candidates.

Measured at matched review workload on the holdout:

- at 78 flags the plain core score gives 67 TP / 11 FP; **RC3 gives 67 TP / 11 FP**, and
  the two flag sets agree on 66 of 67 anomalies;
- at 125 flags the plain core gives 72 TP / 53 FP; **RC2 gives 71 TP / 54 FP**;
- the plain core score *ranks* better than RC2's combined score — PR AUC 0.8239 against
  0.8000, from RC2's own report.

Under a nested lot-grouped protocol at matched budget, the paired lot bootstrap puts
RC2's band against simply lowering the threshold at 0 to +2 true positives, with a 95%
interval spanning zero at every budget.

## The six defects, and what happened to each

| | defect | fixed by |
|---|---|---|
| C1 | RC2's score not monotone with its own disposition — 54 PASS rows above the weakest REVIEW | one monotone score with a reserved band; the validator refuses a frame where a single threshold fails to reproduce the decision |
| C2 | threshold selected out-of-fold, applied to a model refit on all data | no residual model exists |
| C3 | zero reference MAD scored as `z = 0`, i.e. perfectly normal | declared ladder MAD, IQR, std, then raise. Dormant on this data: 0 of 180 references affected |
| C4 | a zero-weight component named as the reason for a flag | reasons built only from weighted components |
| C5 | attribution unstable — two methods agreed on 81% of the same 73 components | `module_a_attribution_margin` ships alongside |
| C6 | weights and cutoff selected on the full calibration set | both re-selected inside each fold |

## What I got wrong, for the record

I proposed that static outliers were being averaged away by the top-k aggregation
(hypothesis H1). It looked convincing on calibration — PR AUC +0.0196, interval
excluding zero — and **evaporated on the holdout**: static detection is flat at 6–7 of 18
for every k from 1 to 12. Written up as a falsification in `docs/IMPROVEMENTS.md`, because
a hypothesis that survives only on the split lacking the hard cases is how a false claim
gets made.

## What is in here

`docs/DECISION_LOG.md` (D10 records what would reopen the RC2/RC3 question),
`VALIDATION_SUMMARY.md`, `IMPROVEMENTS.md`, `MODEL_CARD.md`, and the comparison results.
