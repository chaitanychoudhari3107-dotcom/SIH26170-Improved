# SIH 26170 Operational / Live-Input Layer

This folder implements Anushka's requested ongoing-monitoring concept without changing the frozen benchmark.

## Separation rule
`SIH26170-FINAL-01` remains the training/calibration/holdout benchmark.
New manual or uploaded measurements go into the operational database only.
Operational inputs NEVER:
- alter the frozen CSVs,
- reveal hidden evaluation truth,
- retrain the frozen models automatically.

## Operational storage
Use long-format measurement records:
`component_id, lot_id, device_variant, epoch_h, six measurements, measured_at`.

This is intentionally different from the wide benchmark CSV. The backend reconstructs the wide component trajectory whenever Module A/B needs it.

## Analysis behavior by epoch
- 0h: store; Module A may do baseline/lot-relative checks; Module B waits.
- 24h: Module A updates; Module B predicts 168h using ONLY 0h+24h.
- 96h: Module A updates; Module B must NOT use 96h. Display the existing 24h-based forecast.
- 168h: Module A sees the complete trajectory; compare Module B's earlier forecast with the actual value.

## Dashboard ideas
- total components
- PASS / MONITOR / REJECT
- burn-in progress state
- recently updated components
- components whose final disposition changed
- latest update time
- parameter trajectories
- predicted 168h vs actual 168h when available

## Important distinction
Operational progress:
`AWAITING_24H`, `AWAITING_96H`, `AWAITING_168H`, `COMPLETE`

QA disposition:
`PASS`, `MONITOR`, `REJECT`

Do not merge those concepts.

## Prototype scope
Flask + SQLite is enough for the prototype.
No Kafka, live hardware stream, authentication system or automatic retraining is required for the SIH demo.
