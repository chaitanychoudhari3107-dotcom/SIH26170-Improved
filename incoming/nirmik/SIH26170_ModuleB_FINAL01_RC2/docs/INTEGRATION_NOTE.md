# Module B → integration (for Anushka)

## What you receive

`ModuleB_Final_Holdout_Predictions.csv` — one row per component, joined on
`component_id`, **never by row number**.

**Contract columns**, in this order:

```
component_id
predicted_IDDQ_168h                     module_b_p95_IDDQ_168h
predicted_Input_Leakage_Current_168h    module_b_p95_Input_Leakage_Current_168h
predicted_Active_Supply_Current_168h    module_b_p95_Active_Supply_Current_168h
predicted_Propagation_Delay_168h        module_b_p95_Propagation_Delay_168h
predicted_Output_Rise_Time_168h         module_b_p95_Output_Rise_Time_168h
predicted_Output_Fall_Time_168h         module_b_p95_Output_Fall_Time_168h
module_b_primary_parameter
module_b_reason_codes
```

Plus **24 additive `evidence_*` columns**, four per parameter. Ignore them and
nothing breaks; use them and you can apply your own thresholds instead of
inheriting Module B's.

**There is no `module_b_disposition` column,** and there is no `NOT_SET`
placeholder either. Per decision D1 the disposition belongs to Module A + fusion,
and an always-null column would invite a fusion rule built against a field
Module B has no authority over. Please do not add one downstream and attribute it
to Module B.

## What you must send — the request contract

Module B scores **whole, complete lots**, and it will not take your word for it.

| You supply | What it is |
|---|---|
| `expected_lot_sizes={lot_id: n, ...}` | how many components each lot in the request should carry, from your request metadata or the lot traveller. **This is the normal integration route.** |
| or a delivery attestation | the custodian's manifest entry for a whole file: SHA-256, row count, lot count |

If you supply neither, the call is **refused** — a row count cannot prove that nothing
was dropped on the way. If a declared lot arrives short, the call is refused even when
it carries hundreds of rows.

`allow_partial_lot=True` exists and you should not use it in normal integration. It
proceeds on an incomplete cohort, records which lots were short and by how much, and
sets `report.clean = False`. Output produced that way is **not comparable** to full-lot
output — the timing forecasts move and every evidence column is ranked against a
different population.

**Failure behaviour is fail-closed.** An incomplete or unproved delivery, a missing
predictor column, a `*_96h` or `*_168h` column, a hidden-label column, an unknown
`device_variant`, a null or non-positive measurement, or a non-finite forecast all
**raise**. Module B does not return a partial file, a zero-filled row or a NaN forecast.
If you get a file, every guard passed.

**Version the interface by the runtime digest.** `serving.runtime_contract_digest()`
changes whenever serving behaviour changes — completeness rules, the output contract,
the evidence thresholds, the clipping semantics — even when the fitted model is
byte-identical. Pin it, and treat a change as an interface change.

## Column meanings

| Column | Meaning |
|---|---|
| `predicted_<p>_168h` | point forecast, same unit as the input (µA or ns) |
| `module_b_p95_<p>_168h` | upper envelope. Always ≥ the point forecast. **Evidence, not a screen** — see below |
| `module_b_primary_parameter` | the parameter with the strongest forecast-risk evidence, scale-free. Always one of the six, never blank |
| `module_b_reason_codes` | `\|`-separated `B_`-namespaced codes. **Empty string means no code fired**, which is the common case (85 %) |
| `evidence_<p>_limit` | the static limit, or **NaN where none exists**. NaN means "no source-backed limit", not zero and not a pass |
| `evidence_<p>_pred_frac_of_limit` | forecast ÷ limit; NaN where no limit |
| `evidence_<p>_pred_rel_delta_from_24h` | predicted relative drift from the 24 h reading |
| `evidence_<p>_lot_rel_dev_24h` | how far this component sat from its own lot median at 24 h |

## The one thing that must not be built

**Do not treat "inside the p95 envelope" as a pass.** Measured on held-out
calibration lots at τ = 0.95:

| Parameter | marginal coverage | tail coverage (worst-drifting decile) |
|---|---|---|
| IDDQ | 0.967 | 0.681 |
| Input_Leakage_Current | 0.974 | 0.769 |
| Active_Supply_Current | 0.955 | 0.593 |
| Propagation_Delay | 0.958 | 0.604 |
| Output_Rise_Time | 0.933 | **0.407** |
| Output_Fall_Time | 0.942 | 0.451 |

*Corrected 19 Sep 2026: the tail is the decile with the largest observed relative
drift, not the largest forecast residual. Marginal coverage is unchanged.*

The envelope is calibrated across the *population*, not on the tail. A screen
built on it would miss roughly half the worst drifters on `Output_Rise_Time`.
The outlier judgement belongs to Module A; Module B's envelope is one more input
to your fusion, weighted accordingly.

## Calling Module B from the backend

```python
import pandas as pd
from moduleb import freeze, predict

ART = freeze.load_frozen("models/module_b_final01.joblib")   # load once at startup

def forecast(rows: pd.DataFrame) -> pd.DataFrame:
    """rows: one row per component with component_id, lot_id, device_family,
    device_variant and the six parameters at 0h and 24h. Returns the contract
    frame, same row order."""
    out, report = predict.predict_frame(ART, rows, name="api")
    if not report.clean:
        for line in report.lines():
            log.warning(line)          # a clip happened — do not swallow it
    return out
```

`load_frozen` raises if the artifact was produced by a different
`moduleb/config.py` than the one running. That is deliberate: a stale artifact
scored as if it were the frozen model is worse than a startup failure.

### Required input columns, and the request unit

`component_id`, `lot_id`, `device_family`, `device_variant`, and
`<parameter>_0h` / `<parameter>_24h` for all six parameters. That is 16 columns.
Any `96h` or `168h` column present in the frame makes the call **raise**, not
warn.

**The request unit is a whole lot**, not a component — see "What you can rely on"
below. A lot carrying fewer than `moduleb.config.MIN_LOT_COHORT` (30) rows is
refused with a `DataQualityError` that names it.

### Error handling

| Exception | Cause | What the API should do |
|---|---|---|
| `guards.LeakageError` | forbidden column, or a stale artifact | 500 — this is a wiring bug, not bad user input |
| `guards.DataQualityError` | null, duplicate id, non-positive value, unknown variant | 400 — reject the batch and say which check failed |
| `report.clean == False` | a forecast was clipped | still 200, but log it; a non-positive forecast is not normal |

### What you can rely on, and the one thing you cannot

- **Row order does not matter,** and the output preserves the input's order. A rerun
  on the same cohort is bit-identical.
- **Cohort composition DOES matter — send whole lots.** *(Corrected 19 Sep 2026; this
  section previously claimed the opposite, and the test cited for it never called
  `predict_frame`.)* The three timing models read own-lot medians, and the evidence
  layer ranks each component against the others in the request. Measured on calibration
  lot `B_L23`, scoring a component alone instead of with its lot moves the timing
  forecasts by up to **7.18 %** and collapses `module_b_primary_parameter` to `IDDQ` for
  every single-row call. The three current/leakage forecasts are identical, having no
  lot terms.

  `predict_frame` therefore **refuses** any request in which a lot carries fewer than
  `moduleb.config.MIN_LOT_COHORT` (30) rows, naming the offending lots.
  `allow_partial_lot=True` proceeds and sets `report.partial_lot_override`, which makes
  `report.clean` false; the timing forecasts and every evidence column are then computed
  against that partial cohort and are **not comparable** to full-lot output.

## Operational data must not retrain anything

Live measurements entering the operational demo must not modify or retrain the
frozen benchmark model. The artifact is immutable by design — its manifest
carries the SHA-256 of every file it was fitted on.

## Questions

Schema or contract: Nirmik. Dataset or version: Chaitany. Hidden-target
evaluation: Sanskruti, and only after the freeze.
