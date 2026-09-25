# Integration note — Module A to fusion

For Anushka. Short version: **threshold `module_a_score` at the published floor** and
you have reproduced Module A's decision exactly. Nothing else needs reimplementing.

## The contract

`results/ModuleA_Final_Holdout_168h.csv` leads with the five fields
`Integration_Contract_Safe.json` fixes, in order:

```
component_id, module_a_score, module_a_disposition,
module_a_primary_parameter, module_a_reason_codes
```

Everything after those five is additive diagnostic and may be ignored. Join on
`component_id`, never on row order.

## The score

One number in [0, 1] with a reserved band:

| range | meaning |
|---|---|
| `[0.00, 0.90)` | statistical evidence, scaled rank score |
| `[0.90, 1.00]` | **out of specification** — a measured value exceeds its datasheet maximum |

The published floor is `monitor_floor` in
`results/HOLDOUT_PREDICTION_RECEIPT.json`. `module_a_score >= monitor_floor` is
equivalent to `module_a_disposition == "MONITOR"`, exactly, for every row. The release
refuses to emit a frame where that is not true.

This matters because RC2's score did **not** have this property: 54 of its PASS rows
scored above the weakest REVIEW row. If any fusion prototype was built against an RC2
file, that assumption needs rechecking.

## Confidence

`module_a_evidence_tier` is `CONFIRMED`, `MONITOR` or `PASS`.

`CONFIRMED` means the part is out of specification against its datasheet. Across all
5,400 components in this release, 81 components were CONFIRMED and all 81 are real
anomalies — no observed false positive in 5,076 normals, 95% upper bound 0.06%. Fusion
can weight this tier more strongly than `MONITOR` and can reasonably treat it as
decisive.

`MONITOR` is statistical evidence. It is not calibrated as a probability: a score of
0.5 does not mean 50% likely. Use the tier and the floor, not the number's face value.

## Attribution

`module_a_primary_parameter` is the parameter with the strongest observed deviation —
**evidence, not proven root cause**. Ship it to a human reviewer, not into an automated
rule. `module_a_attribution_margin` gives the gap to the runner-up; a margin near zero
means the top two parameters are indistinguishable. Both fields are blank on PASS rows,
deliberately: below the operating threshold the attribution is noise being ranked.

## Reason codes

Pipe-separated. `A_STATIC_LIMIT_EXCEEDED:<parameter>` names the parameter that breached
its limit. `A_LOT_RELATIVE_DEVIATION` and `A_OVERALL_EXTREME` are statistical. `A_OK`
means nothing above the threshold. A component carrying zero weight in the frozen
configuration is never named — so on this release you will only ever see
`A_LOT_RELATIVE_DEVIATION` among the statistical codes.

## Epochs

`scored_epoch_h` and `analysis_status` say what was available. At 0, 24 and 96 h the
output reports **observed deviation only**; a defect that has not begun is correctly
PASS, and the low early recall is not a miss rate. Do not build a fusion rule that
treats a 0 h PASS as evidence of health.

## Module B

Module A makes no use of Module B's forecasts and takes no position on them. If fusion
wants B to corroborate A, note the constraints the Module B team recorded: the p95
envelope is evidence and never a screen, inside-envelope is not a pass, and missing or
no-risk B evidence must never cancel an observed A anomaly. Any learned confirmation
policy needs calibration predictions made without target leakage — it cannot be learned
from the holdout forecasts and their labels.

## Serving requirements

- **Whole, complete lots.** Module A compares a component to its lot; a partial lot
  gives a wrong reference. Completeness is proved against external lot metadata, and a
  batch that cannot prove it is refused rather than scored.
- Known variants only (CMOS_A, CMOS_B, CMOS_C). An unknown variant raises.
- Finite, positive measurements. Nulls, zeros and negatives raise.
- Lots of at least 30 components.

Every one of these raises rather than degrading quietly, so a serving failure is
visible rather than silent.
