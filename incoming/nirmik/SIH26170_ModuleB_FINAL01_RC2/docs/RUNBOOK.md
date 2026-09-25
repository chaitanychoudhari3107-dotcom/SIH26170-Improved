# Module B runbook

Run the stages in order. Each one writes to `results/` and prints its own
pass/fail. Nothing later depends on a stage you skipped except where stated.

## Before anything

```bash
pip install -r requirements.txt
python -m pytest tests/ -q          # the full suite, ~100 s
```

If a test fails, stop. Every number the pipeline produces depends on the guards
those tests exercise.

## Stage by stage

| Stage | Command | Runtime | Reads | Writes |
|---|---|---|---|---|
| 0 | `python scripts/00_selfcheck.py` | ~40 s | all inputs (headers only) | `00_input_hashes.csv` |
| 1 | `python scripts/01_audit.py` | <1 s | train, calibration, holdout *shape* | `01_*.csv` |
| 2 | `python scripts/02_drift_structure.py` | <1 s | train | `02_*.csv` |
| 3 | `python scripts/03_benchmark_frozen_v1.py` | ~3 s | train | `03_*.csv` |
| 4 | `python scripts/04_benchmark_grid.py` | ~6.5 min | train | `04_*.csv` |
| 4 | `python scripts/04_benchmark_grid.py --quick` | ~25 s | train | `04_*.csv` |
| 5 | `python scripts/05_calibration_report.py` | ~3 s | train, calibration | `05_*.csv` |
| 6 | `python scripts/06_predeclared_falltime_rule.py` | <1 s | train, calibration | `06_*.csv` |
| 7 | `python scripts/07_extrapolation_risk.py` | ~3 s | train, calibration | `07_*.csv` |
| 8 | `python scripts/08_reason_code_audit.py` | ~15 s | train, calibration | `08_*.csv` |
| 9 | `python scripts/09_envelope_coverage.py` | ~40 s | train, calibration | `09_*.csv` |
| 10 | `python scripts/10_dryrun_freeze_predict.py` | ~15 s | train, calibration | `results/dryrun/` |
| 11 | `python scripts/11_freeze.py --team-signoff "..."` | ~15 s | train, calibration | `models/` |
| 12 | `python scripts/12_predict_holdout.py --frozen` | ~5 s | **holdout** | `ModuleB_Final_Holdout_Predictions.csv`, `HOLDOUT_PREDICTION_RECEIPT.json` |
| 14 | `python scripts/14_verify_claims.py` | <1 s | docs, scripts, notebooks, `results/` | — |
| 15 | `python scripts/15_release_manifest.py` | ~2 min | tests + stage 14 | `RELEASE_MANIFEST.json` |

**Stage 12 is the only stage that reads the holdout's contents**, and it is the
one-shot. Every other stage takes the holdout's row count, lot count and header from
`moduleb/holdout_manifest.py` — the declared structure, recorded under decision D14 —
and may only **hash** the file to confirm it is the attested delivery. A test fails if
any other stage opens it.

Stage 15 must be run before stage 11: the freeze refuses without `RELEASE_MANIFEST.json`
and carries its digest into the freeze receipt.

## The two gates

**Stage 11 refuses to run** when the unit tests fail, when the pre-declared
fall-time rule has not been executed, when `moduleb/config.py` disagrees with
that executed decision, or when a frozen artifact already exists (without
`--force --reason`). `--team-signoff` is required and is written into the
manifest, so the approval travels with the model.

**Stage 12 refuses to run** when there is no frozen artifact, when the config
digest no longer matches the artifact's, when the holdout carries `168h`
columns, or when the output file already exists.

## What to do before running stage 11

1. Stages 0, 3, 5, 6, 8, 9, 10 all pass.
2. ~~The team has decided `FORECAST_REL_DELTA_CAP`.~~ **Done 19 Sep — D11 =
   LEAVE_OFF.** Nothing further is open.
3. The round-1 review adjudication in `docs/ROUND1_ADJUDICATION.md` has been read,
   and round 2 has either run or been waived.
4. `moduleb/config.py` reflects the decision, and
   `python -c "from moduleb.config import frozen_config_digest as d; print(d())"`
   is noted down.

## If something fails

| Symptom | Meaning | Action |
|---|---|---|
| `LeakageError: 96h information is forbidden` | a forbidden column is in the input file | stop, tell Chaitany |
| `LeakageError: hidden generator-truth columns` | an evaluator-only file was distributed | stop, tell Chaitany |
| `LeakageError: this stage must not receive 168h targets` | the holdout shipped with answers | stop, tell Chaitany |
| `LeakageError: lots appear in both ...` | the split manifest is wrong | stop, tell Chaitany |
| `DataQualityError: duplicate component_id` | the join key is not unique | stop, tell Chaitany |
| `DataQualityError: non-positive measurements` | file corruption | stop, tell Chaitany |
| `LeakageError: the frozen artifact was produced by a different moduleb.config` | code changed after the freeze | check out the matching code, or re-freeze **before** the holdout |
| `WARNING: n non-positive forecasts replaced` | the model produced an impossible value | investigate before sending; it is not normal |
| `WARNING: n forecasts hit the relative-delta cap` | the model was extrapolating | expected only if the cap is on |

MAE higher than hoped, one difficult parameter, a baseline beating the model,
wide intervals, or a worse holdout than calibration are **none of them bugs**.
See `docs/DATA_BUG_VS_MODEL_PROBLEM.md`.

## Reproducing a number

Every table in `results/` comes from exactly one script, and every script prints
the config digest it ran under. To reproduce: check the digest matches, rerun the
script. There is no hidden state and no randomness outside `GLOBAL_SEED`.
