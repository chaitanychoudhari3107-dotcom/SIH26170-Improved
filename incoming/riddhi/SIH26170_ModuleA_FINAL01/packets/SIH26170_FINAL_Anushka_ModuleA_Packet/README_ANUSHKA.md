# Module A → Anushka · integration

**Model** `ModuleA-FINAL01` · **package** `final01.5.0` · dataset `SIH26170-FINAL-01` ·
state **HOLDOUT_PREDICTION_DELIVERED**
**Model digest** `2b2fa4da5ee36e7c…` · **runtime digest** `d73ea59a16361e23…` ·
**source digest** `e6d86298540fc98b…` (at freeze `820d0201e3162a07…`)
**Sign-off** RECORDED · **holdout run** SPENT · **build mismatch** False

All six packets carry the same `RELEASE_IDENTITY.json`. If two disagree on
**model_config** or **runtime_contract**, one is from a different build and must not be
used. `source_tree` moving on its own is explained in `PROVENANCE_ADDENDUM.json`.

## What you need to do

Threshold `module_a_score` at **0.8455864571** — `monitor_floor` in
`contract/runtime_contract.json`. That reproduces `module_a_disposition` exactly, for
every row. Nothing else needs reimplementing.

## What is in here

| Path | What it is |
|---|---|
| `contract/ModuleA_Output_Contract.csv` | the exact output header |
| `contract/runtime_contract.json` | serving rules, the published floor, score bands, what is refused |
| `contract/Schema_Data_Dictionary.csv` | the meaning of every column |
| `contract/Device_Specs.csv` | units, reference values, the eleven available static limits |
| `example/input_one_complete_lot.csv` | a worked serving call — what goes in |
| `example/output_one_complete_lot.csv` | …and exactly what comes back |
| `example/fusion_joined_example_60_rows.csv` | Module A joined to Module B — the frame you start from |
| `example/fusion_join_checks.csv` | the 9 join checks, all passing |
| **`prediction/ModuleA_Final_Holdout_168h.csv`** | **the frozen output fusion consumes — 1,343 rows** |
| `prediction/ModuleA_Final_Holdout_0h/24h/96h.csv` | the same components at earlier epochs |
| `prediction/HOLDOUT_PREDICTION_RECEIPT.json` | input hash, output hashes, digests, sign-off |
| `docs/INTEGRATION_NOTE.md` | the full interface note |

## Four things that will bite if they are missed

**1 · The score is not a probability.** It is monotone in the anomaly rate — every band
up, the observed rate rises — but the largest gap between a band's midpoint and its
observed rate is 0.75. A score of 0.7 does not mean 70%. Do not
display it to a user as a percentage.

**2 · Requests carry whole, complete lots.** Module A compares a component to the others
in its lot, so a partial lot gives a wrong reference — wrong, not approximate.
Completeness is proved against external lot sizes; a row count is not a proof. A short
lot is refused. **A batch missing a whole lot is scored, not refused** — screening one
lot is legitimate — so Module A returns one row per component you *send*, and checking
you got the coverage you expected is yours.

**3 · Module A emits no REJECT.** PASS and MONITOR only. The final disposition is yours.

**4 · A unit error is invisible to the statistical score.** A lot-relative robust z is
scale-free by construction, so if every reading arrives 1000x too large the statistical
tier barely moves. Only the datasheet witness notices, and only upward. Unit validation
belongs upstream of Module A.

## The tier you can lean on

`module_a_evidence_tier == "CONFIRMED"` means the part exceeds its own datasheet
`static_spec_max`. Across all 5,400 components this fired 81 times and
**every one was a real anomaly** — 0 false positives in
5,076 normal components. Not a fitted threshold, so nothing to overfit.

Still bounded, not absolute: the 95% upper bound on the true rate is
**0.06%**. Please do not write "never" in the dashboard.

`MONITOR` is statistical evidence and is not zero-false-positive.

## The join, already done

1,343 rows against `ModuleB-FINAL01-RC2`'s frozen packet,
9 checks, all passing: no duplicate ids either side, full coverage
both ways, no column collision beyond `component_id`, Module A emits no REJECT and
Module B emits no disposition.

**`b_evidence_status` is a view, not a rule.** Where Module B's reason codes name the
same parameter Module A flagged, 19 components are corroborated and on
the holdout every one is a real anomaly. That association is real and **cannot be a
decision rule yet** — the only data where both modules and the labels exist is the
holdout, so a policy fitted there would be fitted on the labels it would be judged
against. Making it usable needs calibration-split Module B forecasts; it is F1 in
`docs/FUTURE_RELEASE_ITEMS.md` and the highest-value cross-module item open.

The two modules name the same primary parameter on only a small minority of components.
Expected: A names where a deviation is already *observed*, B where drift is *forecast*.
Agreement is corroboration; disagreement is two pieces of evidence, not a contradiction.

## What Module A does not do

It does not forecast, decide, or identify root cause.
`module_a_primary_parameter` ships with `module_a_attribution_margin` — the gap to the
runner-up. A margin near zero is a coin toss. Both are blank on PASS rows, deliberately.

Please read `docs/LIMITATIONS.md` section 1 before writing UI copy about static outliers.
