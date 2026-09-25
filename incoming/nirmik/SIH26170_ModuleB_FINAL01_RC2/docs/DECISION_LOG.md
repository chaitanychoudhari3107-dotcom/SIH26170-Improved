# Module B decision log

Newest first. A superseded decision is marked, never deleted.

---

## 2026-09-20 · FINAL-01 · D19 — frozen, and the one-shot spent

**Closed.** Team sign-off was given and recorded as
`Team sign-off 2026-09-20 — confirmed by Nirmik, Module B owner, on behalf of the team`.

Stage 11 froze the model with that sign-off embedded in the manifest before
serialisation; stage 12 then ran the one-shot holdout prediction, once. Outputs:
`models/module_b_final01.joblib`, `models/FREEZE_RECEIPT.json`,
`results/ModuleB_Final_Holdout_Predictions.csv` (1,343 rows / 18 lots) and
`results/HOLDOUT_PREDICTION_RECEIPT.json`.

The fitted model did not change to do this. **From this point the release is closed to
change:** retuning in response to a score would produce a different model that cannot be
evaluated on this holdout, and stage 12 refuses a second run.

Consequence for D14: the spend state is no longer asserted anywhere as a constant. The
pre-freeze provenance record stays fixed — it is history — and whether the one-shot has
been spent is read from disk by `holdout_manifest.one_shot_state()` and recorded in the
release manifest and the prediction receipt. A constant saying `UNSPENT` would have been
false from the moment stage 12 ran.

---

## 2026-09-19 · FINAL-01 · D18 — release decisions are machine-enforced

**Closed.** A decision log is prose, and prose does not stop a freeze.
`moduleb/decisions.py` now carries a predicate per release decision — D1, D10, D11,
D12, D13, D14 — that reads the live code rather than a copy of the decision.
`freeze.freeze` and `scripts/11_freeze.py` run the set as a preflight and refuse to
freeze while any of them is false, so enabling the relative-delta cap (D11) or moving
the fall-time feature set (D10) now stops the release instead of producing a
quietly-different artifact. Negative tests cover both.

Evidence: `moduleb/decisions.py`, `tests/test_release_gates.py`.

## 2026-09-19 · FINAL-01 · D17 — the runtime contract has its own digest

**Closed.** `frozen_config_digest()` covers the fitted model. Everything that changes
what a caller *gets* without changing a fitted parameter — lot completeness, the
partial-lot override, the input and output contracts, the reason-code runtime
thresholds, the static-limit policy, the clipping and fallback semantics — was
invisible to a consumer holding that digest. `serving.runtime_contract_digest()` now
covers exactly that surface, the frozen manifest carries **both**, and stage 12
validates both. A source-tree digest is recorded alongside them for the code the two
do not cover.

Tested: a runtime-only change moves the runtime digest and leaves the model digest
alone; a model-only change does the reverse; a stale artifact is refused at load.

## 2026-09-19 · FINAL-01 · D16 — the sign-off lives inside the frozen artifact

**Closed.** Sign-off used to be written to a sidecar **after** `joblib.dump` had
already run, so the serialised artifact carried a manifest with no approval in it and
the only record of who approved lived in a file anyone could edit afterwards. The
manifest — sign-off included — is now completed **before** serialisation, embedded in
the artifact, and the sidecar is written from the same dict. `freeze.load_frozen`
refuses a missing sign-off, a manifest that fails its own digest, an embedded/sidecar
mismatch, and a rehearsal artifact presented as production.

Module B does not manufacture approval. `build_manifest` raises without one.

## 2026-09-19 · FINAL-01 · D15 — a lot is served only when it is proved complete

**Closed.** `MIN_LOT_COHORT = 30` was a size floor, and a size floor is not a
completeness proof: a lot of 82 delivered with 61 rows present clears it and still
produces a different answer, because the timing models read own-lot medians and every
evidence column ranks a component against the others in the request.

Completeness must now be **proved**, by one of two sources outside the rows
themselves — the caller's declared per-lot sizes (`expected_lot_sizes`, the production
route) or the custodian's whole-file attestation (SHA-256, rows, lots). Without one of
them the request is refused. `MIN_LOT_COHORT` survives as a secondary sanity floor.
`allow_partial_lot=True` remains the only way past, and it records the offending lots,
their observed and expected counts, the serving-contract version and the runtime
digest, and makes the run report non-clean.

Extends D12, which declared the contract cohort-level but enforced it with a floor.
Evidence: `moduleb/serving.py`, `tests/test_serving.py`.

## 2026-09-19 · FINAL-01 · D14 — corrected holdout-access provenance

**Closed.** The package said the holdout had never been opened. That was not accurate
and the accurate version is this:

- the **predictor-only** holdout file was read before the freeze, for structural and
  schema checks — stage 0 loaded it, stage 1 tabulated its shape, stage 10 read its
  header, stage 14 re-derived its lot count;
- the file carries **no 168 h targets**, and the hidden truth has never been available
  to Module B;
- **no holdout forecast was generated** and **no holdout score was observed**;
- **no model or configuration decision used a holdout outcome**;
- the one-shot predictive evaluation is therefore **UNSPENT**.

Both halves are acted on. The history above is recorded in
`moduleb/holdout_manifest.py` rather than rewritten, and from this release the
pre-freeze stages read the declared structure in that module instead of the file.
Exactly one stage may open the contents — `scripts/12_predict_holdout.py`, after the
freeze — and a test fails if any other stage does. The file may still be **hashed**
anywhere: a SHA-256 is provenance, not content, and it is what proves the delivery is
the one the manifest describes.

Raised in round 2 as P1-G1.

## 2026-09-19 · FINAL-01 · D13 — the tail metric measured the wrong population

**Closed.** Until 18 Sep, `envelope.coverage_report` ranked the "tail" by
`y_true − point` — the forecast **residual** — while every document described it as
the worst-drifting decile. Different populations, and the definition moved whenever
the forecast moved.

Corrected to rank by observed relative drift from 24 h, `(y₁₆₈ − x₂₄)/x₂₄`. Stage 9
re-run as a **corrective run**; the 18 Sep figures are preserved as
`results/09_envelope_coverage_SUPERSEDED_2026-09-18_residual_ranked.csv` and must not
be quoted as tail coverage. Corrected τ = 0.95 tail range **0.407 – 0.769** (was
0.473 – 0.802). Marginal coverage unchanged. A regression test pins the definition.

Raised by independent review as F3. Evidence: `results/09_envelope_coverage.csv`.

## 2026-09-19 · FINAL-01 · D12 — the serving contract is cohort-level

**Closed.** The package claimed a single-component API was equivalent to a full-lot
call. It is not: the three timing models read own-lot medians and the evidence layer
ranks each component against the others in the request. Measured on calibration lot
`B_L23` — every one of 72 components moves when scored alone, median |Δ| 0.55–0.66 %,
max **7.18 %** on `Propagation_Delay`, and `module_b_primary_parameter` collapses to
`IDDQ` for every single-row call.

The test cited as evidence split an already feature-engineered frame and never called
`predict_frame`. It has been replaced by four tests on the real path.

`moduleb.config.MIN_LOT_COHORT = 30` now makes `predict_frame` refuse an insufficient
cohort; `allow_partial_lot=True` overrides it and marks the report not-clean. The
constant sits outside the `FROZEN_V1` block and **the config digest is unchanged** —
no fitted parameter moved and no previously valid forecast changed.

Rejected alternatives: removing the lot features (a model change under D2/D5), and
freezing training reference distributions for the reason codes (changes evidence
semantics, needs a full firing-rate re-audit, unnecessary under a cohort contract).

Raised by independent review as F1.

## 2026-09-19 · FINAL-01 · D11 — the extrapolation cap stays OFF

**Closed. DECISION: LEAVE_OFF.** `FORECAST_REL_DELTA_CAP` remains `None`. The code
path is kept, documented and unit-tested, as a candidate safeguard for a future
release.

Four reasons:

1. The ±0.50 value would be **selected after observing calibration truth**. "Not a
   retune" was too narrow — the coefficients are untouched, but choosing an inference
   transformation from observed calibration outcomes is post-hoc pipeline selection.
   The protocol allowed one pre-declared calibration decision; that was the fall-time
   rule (D10) and it is spent.
2. **The motivating case is not a false positive.** Both the true value (1.047 µA) and
   the forecast exceed CMOS_B's 1.0 µA limit, so `B_FORECAST_EXCEEDS_LIMIT` was
   correct. The defect is the magnitude of the assertion, not its direction.
3. **No independent bound is both available and effective.** A cap justified from the
   training target distribution would sit at p99.9 = 7.81 or max = 13.32 — far above
   the offending +1.95 forecast, so neither would clip it. Only ≈ p99 = 0.247 would,
   which is inside the range the training data says is legitimate and would also begin
   clipping timing forecasts. That has never been measured.
4. A hard cap can suppress a future legitimate extreme forecast, and nothing in the
   evidence distinguishes the two cases.

**What would reopen it:** a cap fixed independently of the observed calibration outcome
— a source-backed engineering or physical bound, or a genuinely pre-specified train-only
rule — plus a calibration check that it controls the intended failure mode without
creating materially worse misses.

The finding itself stands: acceptance criterion M5 fails and is carried into freeze as
a known limitation. Evidence: `results/07_cap_sweep.csv`, `results/07_target_tails.csv`,
guide §13. Raised by independent review as F4.

## 2026-09-18 · FINAL-01 · D10 — the pre-declared fall-time rule did not fire

Executed on the 12 calibration lots. The `own` feature set was **1.5 % worse**
than `own+lot+cross` and won **2 of 12** lots. Both conditions failed.
`Output_Fall_Time` keeps `own+lot+cross`. The rule is spent and cannot be re-run.

Recorded re-reading: "≥ 4 of 6 lots" was written for Candidate V1's six-lot
calibration file. FINAL-01 ships twelve, so it was applied as the proportion it
expressed — more than half, ≥ 7 of 12. It fails under either reading.

Evidence: `results/06_predeclared_falltime_decision.csv`.

## 2026-09-18 · FINAL-01 · D9 — the frozen configuration stands

The Candidate-V1 configuration, rerun unchanged on FINAL-01, beats the
median-ratio baseline on four of six parameters (V1: two). The 24-configuration
grid finds nothing better by more than 4.5 % on any parameter, which is inside
the 5 % tie threshold.

No configuration change. Evidence: `results/03_paired_lot_test.csv`,
`results/04_best_vs_frozen.csv`.

## 2026-09-18 · FINAL-01 · D8 — FINAL-01 is accepted with no escalation

Every structural check passes. Generator changes 1, 3, 4 and 5 are visible in the
data; change 2 did not land on the SNR measure it was written against, which is
recorded for the record and is **not** a request to regenerate.

Evidence: `results/01_*.csv`, `results/02_*.csv`.

---

## 2026-09-15 · Candidate V1 · D5 — standing instruction *(carried into FINAL-01)*

No retraining, no tuning, no configuration changes until the new dataset is
benchmarked with the same code. Candidate V1 is the before-state.
**Honoured:** the `FROZEN_V1` block in `moduleb/config.py` is byte-equivalent to
the V1 freeze.

## 2026-09-15 · Candidate V1 · D4 — FDI-5 retracted

The claim that the CMOS_C 3.5 ns propagation-delay baseline was a misread
datasheet maximum was **wrong**. TI's SN74LVC00A gives tpd MIN 1 / TYP 3.5 /
MAX 4.1 ns at 3.3 V ± 0.3 V and 25 °C. 3.5 ns is a genuine typical, and the
5.5 → 4.1 ns limit change was a correction (5.5 ns is the 125 °C max). Mock v1
review item C4 is withdrawn on the same grounds.

## 2026-09-15 · Candidate V1 · D3 — five V2 generator changes accepted

Stronger lot ageing · recalibrated `Input_Leakage_Current` early SNR · more
independent lots · better clean-lot coverage · enough static-fail cases.
Stated principle: the generator is not changed to improve Module B's MAE.
Checked against the delivered data in `docs/FINDINGS_FOR_TEAM.md` §2.

## 2026-09-15 · Candidate V1 · D2 — architecture frozen for a fair comparison

The two feature groups, Huber on the relative delta from 24 h (ε = 1.35,
α = 1e−3), the pooled-with-variant-one-hot structure, the whole-lot GroupKFold
protocol, and the conformalised envelope at τ = 0.95 may not change before the
new dataset is benchmarked. **Honoured.**

## 2026-09-15 · Candidate V1 · D1 — Module B does not own the disposition

Final PASS / MONITOR / REJECT belongs to Module A + fusion. Module B emits six
point forecasts, six p95 envelopes, `module_b_primary_parameter` and `B_`
evidence codes. `module_b_disposition` is withdrawn entirely — not emitted as
`NOT_SET`, so no fusion rule can be built against it.

Carried instruction: **do not invent missing static limits.** The seven
variant × parameter cells with no `static_spec_max` stay empty and the
limit-based codes never fire there. **Honoured and tested**
(`scripts/08_reason_code_audit.py` §8.5, `tests/test_reason_codes.py`).
