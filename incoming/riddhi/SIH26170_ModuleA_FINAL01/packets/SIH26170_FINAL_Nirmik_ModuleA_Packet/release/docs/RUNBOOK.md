# Runbook — ModuleA-FINAL01

```bash
pip install -r requirements.txt
export SIH26170_RELEASE=/path/to/SIH26170_FINAL_RELEASE_01
```

## Ungated stages

```bash
python run_all.py --release $SIH26170_RELEASE
```

Runs 00 through 06 in order and stops on the first failure. Roughly 60 seconds; stage
04 is the slow one at about 30.

| stage | reads | writes | time |
|---|---|---|---|
| `00_selfcheck.py` | hashes, contract, environment, tests | `00_selfcheck.csv` | ~7 s |
| `01_audit.py` | the three splits | `01_audit.json`, `01_scale_ladder.csv` | ~3 s |
| `02_spec_witness.py` | splits + Device_Specs + labels | `02_spec_witness.csv` | ~2 s |
| `03_threshold_curve.py` | train, calibration | `03_threshold_curve.csv`, `03_early_thresholds.json` | ~5 s |
| `04_nested_validation.py` | train, calibration | `04_nested_validation.csv` | ~32 s |
| `05_blindspot_report.py` | all splits + labels | `05_blindspot.csv` | ~5 s |
| `06_dryrun.py` | train, calibration | `06_dryrun.json` | ~5 s |

Stages 02 and 05 open the hidden labels through `scripts/_evaluator.py`. They are
reporting stages: nothing they compute feeds a fitted quantity.

## Gated stages

**Do not run these to see what happens.** Stage 08 is one-shot and has been spent.

```bash
# 07 — freeze. Needs a real recorded sign-off; a placeholder is refused.
python scripts/07_freeze.py --release $SIH26170_RELEASE \
  --signoff "<the team's actual recorded sign-off text>"

# 08 — the one-shot holdout run. Writes and hashes predictions before any label exists.
python scripts/08_predict_holdout.py --release $SIH26170_RELEASE
```

Preconditions for 07: stages 00–06 green, `03_early_thresholds.json` present, input
hashes matching. The preflight re-checks D1, D4 and D5 mechanically and refuses the
freeze if any no longer holds.

## After the fact

```bash
python scripts/09_evaluate_holdout.py --release $SIH26170_RELEASE   # DIAGNOSTIC
python scripts/10_verify_claims.py                                  # after any doc edit
python scripts/11_release_manifest.py
```

Stage 09 re-hashes the prediction files and refuses to score one that changed after
stage 08 wrote it.

**Run stage 10 after editing any document.** Every figure quoted in `docs/` is listed
there against the file it must come from. If you add a claim, add its check in the same
edit — that is what keeps the zero-unsupported-claims rule in the master prompt real.

## Clearing results/

`results/` is regenerable: `rm -rf results/*` then `python run_all.py --release ...`
rebuilds all of it. `prediction/` is **not** — it holds the spent one-shot holdout
outputs, which is why they do not live in `results/`. `run_all.py` refuses to start if
they are missing rather than failing several stages later, and the fix is to restore
them from the release archive, never to re-run stage 08.

## If something fails

- **Hash mismatch at stage 00** — you have a different dataset version. Stop. Do not
  compare any number against this release's.
- **`GuardError: incomplete lots`** — the batch is partial, or the manifest is for a
  different split. Module A cannot score a partial lot; this is not a bug to work around.
- **`DegenerateScaleError`** — a reference feature is constant. The feature carries no
  information and must be excluded explicitly, in a documented change. Do not restore
  the inherited behaviour of scoring it as zero.
- **`FreezeRefused: artifact was frozen under config digest …`** — the code moved after
  the freeze. Either check out the frozen code or re-freeze deliberately; do not edit
  the check.
- **Stage 10 fails** — a document and `results/` disagree. Fix the document, or measure
  the number. Never adjust the check to match the prose.
