# SIH 26170 FINAL RELEASE APPROVAL

Dataset ID: `SIH26170-FINAL-01`
Status: **FINAL / FROZEN BENCHMARK**
Rows: 5,400
Lots: 72
Variants: CMOS_A / CMOS_B / CMOS_C
Schema: one component per row, 28 raw columns
Parameters: IDDQ, Input_Leakage_Current, Active_Supply_Current, Propagation_Delay, Output_Rise_Time, Output_Fall_Time
Epochs: 0h, 24h, 96h, 168h

## Nirmik feedback resolved
- more independent lots: 72 total
- stronger lot-specific ageing: healthy late-drift ICC median ~0.177
- Input Leakage early signal/noise fixed: SNR > 1 and positive early→late correlation in all variants
- Module B uses 0h/24h only
- Module B emits forecasts/evidence; fusion owns final PASS/MONITOR/REJECT

## Riddhi feedback resolved
- calibration anomalies balanced across variants: 19 / 18 / 17
- anomalies distributed over multiple calibration lots per variant
- clean lots exist in train/calibration/holdout for every variant
- defect behavior/severity allocation is controlled but not mechanically identical
- timing correlation is checked within variant and remains moderate, not copied
- same-component epoch continuity is intentionally high; drift relationships are not forced to 0.99
- static-pass/static-fail anomaly coverage is 75% / 25%

## Anushka feedback resolved
- final safe integration contract and schema are included
- Active_Supply_Current is the final parameter name
- all modules use the same dataset ID/version
- an operational live-input layer is included separately:
  measurement entry/upload -> validation -> DB -> Module A/B -> fusion -> dashboard/history
- operational data does not alter the frozen benchmark

## Freeze rule
No V2/V3 regeneration should be done merely to improve recall, MAE or demo appearance.
Regenerate only if an actual correctness bug is discovered: leakage, broken schema, impossible values, wrong split, or faulty generator logic.
