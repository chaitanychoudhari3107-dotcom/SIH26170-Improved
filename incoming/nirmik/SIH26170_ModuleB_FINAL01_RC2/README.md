# Module B — 168 h forecasting on SIH26170-FINAL-01

**Owner:** Nirmik · **Dataset:** `SIH26170-FINAL-01` ·
**Release candidate:** `ModuleB-FINAL01-RC2` ·
**Status:** `HOLDOUT_PREDICTION_DELIVERED` — **frozen** 20 Sep 2026 on a recorded team
sign-off, and the one-shot holdout run is **spent**. `models/module_b_final01.joblib`
exists; `results/ModuleB_Final_Holdout_Predictions.csv` and its receipt exist.
**Nothing here may be retuned in response to the scores.**

Predict each component's six electrical parameters at 168 h using only what is
measurable at 0 h and 24 h. Module B emits forecasts and forecast-risk evidence.
The final PASS / MONITOR / REJECT belongs to Module A + fusion.

---

## Where things are

```
moduleb/     the package — 16 small modules, none over 230 lines, no module
             imports upward, so any one can be read on its own
scripts/     thin runners, numbered in run order. All the logic is in moduleb/
tests/       the unit suite. Run it before trusting any number; the current
             count is in RELEASE_MANIFEST.json under verification.tests
notebooks/   the same stages as readable notebooks, importing the same package
docs/        COMPLETE_GUIDE.md first — then model card, decision log,
             runbook, integration note, and the ChatGPT review prompt
data/        the four files Module B is allowed to read
results/     everything the scripts produce (generated; safe to delete)
models/      the frozen artifact, once stage 11 has been run
```

The package is split this way on purpose. A single 900-line pipeline file is
hard to open, harder to review line by line, and impossible to unit test in
pieces. Each module here does one thing and is tested for that one thing.

## Quick start

```bash
pip install -r requirements.txt
python scripts/00_selfcheck.py        # environment, file hashes, unit tests
python scripts/01_audit.py            # is anything here a data bug?
python scripts/03_benchmark_frozen_v1.py
```

Full sequence and what each stage decides: **`docs/RUNBOOK.md`**.
Everything in one document, from scratch: **`docs/COMPLETE_GUIDE.md`**.

## The stages

| | script | what it decides | state |
|---|---|---|---|
| 0 | `00_selfcheck.py` | are the code and inputs what we think they are | ✅ |
| 1 | `01_audit.py` | data bug, or a modelling problem to live with | ✅ clean |
| 2 | `02_drift_structure.py` | is the thing being predicted learnable at all | ✅ |
| 3 | `03_benchmark_frozen_v1.py` | the frozen V1 config on FINAL-01, unchanged | ✅ 4 of 6 beat baseline |
| 4 | `04_benchmark_grid.py` | 24 configurations, evidence only | ✅ frozen config stands |
| 5 | `05_calibration_report.py` | held-out score on 12 calibration lots | ✅ |
| 6 | `06_predeclared_falltime_rule.py` | the one pre-declared change | ✅ did not fire |
| 7 | `07_extrapolation_risk.py` | where a forecast is untrustworthy | ✅ evidence for D11, closed 19 Sep |
| 8 | `08_reason_code_audit.py` | are the B_ codes sparse enough to act on | ✅ 14.9 % flagged |
| 9 | `09_envelope_coverage.py` | what the p95 envelope may be called | ✅ evidence, not a screen |
| 10 | `10_dryrun_freeze_predict.py` | rehearse freeze + holdout on a stand-in | ✅ |
| 11 | `11_freeze.py` | **GATED** — freeze the model | ✅ run 20 Sep 2026 on a recorded sign-off |
| 12 | `12_predict_holdout.py` | **GATED** — the one-shot holdout run | ✅ **spent** 20 Sep 2026 — 1,343 rows, 18 lots |
| 14 | `14_verify_claims.py` | do the docs **and the code** match the numbers | ✅ |
| 15 | `15_release_manifest.py` | write `RELEASE_MANIFEST.json` | ✅ |

## The result in six lines

- FINAL-01 is clean: 5,400 rows, 72 lots, zero nulls, zero duplicate ids, zero
  non-positive values, zero 96 h columns, three splits with no shared lot.
- The frozen Candidate-V1 configuration, rerun untouched, now beats the
  median-ratio baseline on **four of six** parameters (V1: two). Gains of
  6.8–9.0 % MAE on 30–34 of 42 held-out lots, p ≤ 0.0015.
- IDDQ and Active_Supply_Current remain **ties**. A single constant per variant
  is as good as the model there, and that is the honest thing to report.
- The 24-configuration grid does not beat the frozen config by more than 4.5 %
  on any parameter — below the team's 5 % tie threshold. No change is warranted.
- The pre-declared `Output_Fall_Time` rule **did not fire** (−1.5 % gain, 2 of 12
  lots). It is now spent.
- **D11 closed 19 Sep — cap stays OFF.** A single component of 906 gets a +195 %
  drift forecast and carries 27.7 % of `Input_Leakage_Current`'s calibration error.
  A ±0.50 cap would fix it, but the value would be post-hoc on calibration, the case
  is a true positive with an exaggerated magnitude, and no independent bound is both
  available and effective. Carried into freeze as a known limitation.
- **Round-1 review applied (19 Sep).** The serving contract is now **cohort-level**
  (whole lots, not single components), and tail coverage is re-measured against true
  drift rather than forecast residual. See `docs/ROUND1_ADJUDICATION.md`.
- **Round-2 release engineering applied (19 Sep).** A lot is served only when it is
  **proved complete**; team sign-off is **embedded in the frozen artifact** before it is
  serialised; every release decision is **machine-checked** by the freeze preflight; the
  **runtime contract has its own digest** alongside the fitted-model one; and the
  holdout-access history is **corrected and recorded** (D14) rather than claimed away.
  The fitted model did not change — the config digest still begins `8d0621941f86fbb8`.
  See `docs/ROUND2_FINAL_ADJUDICATION.md` and `docs/FINAL_FREEZE_READINESS.md`.

## Rules the code enforces, not the reader

- No `*_96h` or `*_168h` column ever enters a feature matrix. Checked on the
  file *and* on the matrix handed to each estimator.
- No generator ground truth, defect label, severity or onset is read at any point.
- Every split is by whole lot. A row-level split raises.
- No static limit is invented. The seven empty `Device_Specs` cells stay empty
  and the limit-based reason codes never fire there.
- No `module_b_disposition` column, not even `NOT_SET`.
- A request is answered only when every lot in it is **proved complete** — from declared
  per-lot sizes or the custodian's file attestation. A row count is not a proof, and
  `MIN_LOT_COHORT` is only a secondary sanity floor.
- A freeze without a genuine team sign-off is refused, and the sign-off is embedded in
  the artifact before it is written.
- Every recorded release decision (D1, D10, D11, D12, D13, D14) is re-checked
  mechanically at freeze time; one that no longer holds stops the freeze.
- The holdout's **contents** are opened by exactly one gated script, once. Every other
  stage reads the declared structure in `moduleb/holdout_manifest.py` and may only hash
  the file.
