# Module A → Tanisha · domain and standards

**Model** `ModuleA-FINAL01` · **package** `final01.5.0` · dataset `SIH26170-FINAL-01` ·
state **HOLDOUT_PREDICTION_DELIVERED**
**Model digest** `2b2fa4da5ee36e7c…` · **runtime digest** `d73ea59a16361e23…` ·
**source digest** `e6d86298540fc98b…` (at freeze `820d0201e3162a07…`)
**Sign-off** RECORDED · **holdout run** SPENT · **build mismatch** False

All six packets carry the same `RELEASE_IDENTITY.json`. If two disagree on
**model_config** or **runtime_contract**, one is from a different build and must not be
used. `source_tree` moving on its own is explained in `PROVENANCE_ADDENDUM.json`.

Two asks, both needing domain judgement rather than more searching.

## 1 · Please sanity-check the datasheet limits

`Device_Specs.csv`'s `static_spec_max` is carrying real weight in this release. It is
the basis of the **CONFIRMED** tier: across all 5,400 components the rule fired
81 times and **every one was a real anomaly** — 0 false
positives in 5,076 normals, 95% upper bound 0.06%.

Eleven of eighteen variant x parameter cells have a limit. **The seven empty ones stay
empty** — no interpolation, no borrowing from a neighbouring variant, no derivation from
the data — and the rule simply never fires on those parameters:

- `Active_Supply_Current` — no limit for any variant
- `Output_Rise_Time`, `Output_Fall_Time` — no limit for CMOS_B or CMOS_C

If any of the eleven populated values is wrong, a real defect gets certified on a wrong
basis, or a real one is missed. That is worth twenty minutes of your time.

## 2 · Is there a physically justified relationship between parameters?

This is the open technical question and I cannot answer it without you.

The components Module A misses are individually **within spec** and individually
unremarkable against their own lot — 6 of 21
within-spec static offsets are caught. Nine statistics from five families all land in
the same place, so the evidence is genuinely below the noise floor of comparing a
component to its lot.

What has **not** been tried is whether those parts violate a *relationship* that physics
fixes, rather than a marginal distribution: IDDQ against `Active_Supply_Current`, or rise
time against fall time. An unconstrained multivariate distance was tried (robust
within-lot Mahalanobis) and did not help.

The reason this needs you: a ratio nobody can justify is just another fitted threshold,
and this release has been careful not to add any. A relationship you can point to a
physical reason for would be a genuinely independent witness — the second one after the
datasheet limits.

## What is in here

`domain/` holds `Device_Specs.csv`, `02_spec_witness.csv`, `02_spec_coverage.csv`,
`05_blindspot.csv` and `14_per_severity.csv`; `docs/LIMITATIONS.md` has the reasoning.
