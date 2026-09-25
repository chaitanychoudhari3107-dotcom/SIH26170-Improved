# Module A → Sanskruti · evaluation

**Model** `ModuleA-FINAL01` · **package** `final01.5.0` · dataset `SIH26170-FINAL-01` ·
state **HOLDOUT_PREDICTION_DELIVERED**
**Model digest** `2b2fa4da5ee36e7c…` · **runtime digest** `d73ea59a16361e23…` ·
**source digest** `e6d86298540fc98b…` (at freeze `820d0201e3162a07…`)
**Sign-off** RECORDED · **holdout run** SPENT · **build mismatch** False

All six packets carry the same `RELEASE_IDENTITY.json`. If two disagree on
**model_config** or **runtime_contract**, one is from a different build and must not be
used. `source_tree` moving on its own is explained in `PROVENANCE_ADDENDUM.json`.

## What to check first

**166 claim checks**, each naming the file it verifies against. Re-run
`scripts/10_verify_claims.py` from the full release and it should still be
166 of 166. A single failure means a document and `results/`
disagree, and the document is wrong.

**The number to scrutinise:** the nested estimate of the shipped configuration,
**45 of 54 anomalies at 9 false alarms** (recall
83.3%, FPR 1.06%) — `04_nested_validation.csv`, the
`shipped` arm. Weights *and* threshold selected inside each of 12 leave-one-lot-out
folds, at the 1% budget the release operates at. The before-state under the same
protocol is 44 of 54 at 7.

No previous Module A candidate reported a number with the selection inside the fold.

## Two corrections you should know were made

Both were caught by the verification machinery rather than by review, and both are in
`docs/DECISION_LOG.md`.

1. **A headline quoted from the wrong budget.** An earlier revision reported 48 of 54 at
   25 false alarms — a 3% run, while the release ships at 1%. Corrected to
   45 of 54 at 9.
2. **A weight-unanimity claim that was budget-dependent.** "All 12 folds chose pure
   `lot_relative`" holds at 3%; at the shipped 1% the folds split 6/6. What *is* robust:
   across all 24 fold-selections, **no fold chose the inherited `overall_extreme`**.

## Reproducibility

Two independent runs from separate clean extractions produce
**47 of 47 analysis outputs byte-identical**
(`verification/19_reproducibility.csv`). The protocol is
`docs/MASTER_PROMPT_FINAL_VERIFICATION.md` and you can re-run it yourself.

Getting there found two defects worth knowing as failure shapes: a results file
recording wall-clock time so no two runs could ever match, and a pipeline that could not
run on a cleared `results/` because it read a gated stage's one-shot output from there.

## What is NOT a performance claim

Everything on the holdout. It shaped RC1, RC2, RC3 and this release's reporting.
`docs/ACCEPTANCE_CRITERIA.md` has a section headed "Not met, and not claimed" — a fresh
lot-grouped test set is F2 in `docs/FUTURE_RELEASE_ITEMS.md` and is the only thing that
would turn any of this into a claim.

## Evidence trail

Predictions were written and hashed by stage 08 **before any label was opened**.
`scripts/09_evaluate_holdout.py` re-hashes them and refuses to score a file that moved.
The hashes are in `prediction/HOLDOUT_PREDICTION_RECEIPT.json`.
