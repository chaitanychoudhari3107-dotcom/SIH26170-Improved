# Data bug, or a modelling problem?

The distinction matters because one of these is Chaitany's to fix and the other
is Module B's to live with, and because "the score is low, please regenerate the
dataset" is how a benchmark stops meaning anything.

FINAL-01 is frozen. It is regenerated only for a real correctness bug.

## Escalate to Chaitany

| Symptom | Why it is a bug |
|---|---|
| a `*_96h` column in a Module B file | Module B is contractually 0 h + 24 h only |
| any hidden label, defect mode, severity, onset or ground-truth column | those are evaluator-only |
| the holdout file carries `168h` values | the blind evaluation is no longer blind |
| a lot appears in two protected splits | a held-out score becomes partly in-sample |
| duplicate `component_id` | the fusion join silently multiplies rows |
| zero or negative measurements | all six parameters are magnitudes |
| a missing target column in train or calibration | the stage cannot fit |
| schema or dataset-id mismatch with FINAL-01 | results across versions are not comparable |

All eight raise automatically. `moduleb/guards.py` is where they live, and
`tests/test_guards.py` proves each one fires.

## Keep modelling

| Symptom | Why it is not a bug |
|---|---|
| MAE higher than hoped | the problem is as hard as it is |
| one parameter barely predictable | its late drift is not visible at 24 h — report it |
| a simple baseline beats the model | then ship the baseline's honesty, not a complex model |
| the model fails on some lots | lots differ; that is what `WorstLotMAE` is for |
| prediction intervals are wide | the uncertainty is real |
| holdout worse than calibration | expected; twelve lots is a small sample |
| a flag fires rarely | sparse is the design goal, not a defect |

## The one that looks like both

A forecast far outside anything the training data supports — the +195 % drift in
`docs/FINDINGS_FOR_TEAM.md` — is **not** a data bug. The training file genuinely
contains relative deltas up to 13.3×, so the model is extrapolating from real
data, not corrupt data. It is a modelling decision about what Module B is willing
to assert, and it belongs in `moduleb/config.py`, not in a message to Chaitany.
