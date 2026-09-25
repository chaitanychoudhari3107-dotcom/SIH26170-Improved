# FINAL v1 — Review Resolution Summary

## Nirmik / Module B
Accepted changes:
- More independent lots.
- Stronger lot-specific ageing structure.
- Recalibrate Input_Leakage_Current early signal/noise.
- Module B does not own final PASS/MONITOR/REJECT; it emits forecasts/evidence.

Not changed:
- CMOS_C propagation-delay anchor remains 3.5 ns typical / 4.1 ns max.
- No fake static limits were added.
- The dataset was not tuned to improve a model score.

## Riddhi / Module A
Accepted changes:
- Calibration anomaly allocation is balanced across variants and spread across multiple lots.
- Behavior/severity coverage is constrained across variants.
- Clean-lot coverage exists in every variant and split.
- Static-pass/static-fail benchmark coverage is more balanced.

Reviewed but intentionally not changed:
- Raw epoch level correlation remains high because the same physical component keeps its manufacturing baseline across time.
- Timing parameters remain moderately correlated within each variant; the pooled ~0.99 correlation was largely caused by mixing HC/AHC/LVC baselines.
- Legitimate lot baseline variation was not flattened.
- Holdout extreme values remain when they correspond to intentional severe hidden anomalies.

## Anushka / Integration
- `Active_Supply_Current` is the final parameter name.
- `component_id` is only a join key, not chronological order.
- Module A and B must run on the same final dataset version.
- Safe integration package excludes hidden truth/targets/config.
