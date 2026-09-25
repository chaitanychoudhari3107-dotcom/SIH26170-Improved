# Acceptance criteria

Written so that "done" is checkable rather than a matter of opinion. Each row
says what is tested, where, and whether it currently passes. Criteria marked
**not checkable here** are stated rather than quietly dropped.

## Contract compliance — all MUST

| # | Criterion | Checked by | Status |
|---|---|---|---|
| C1 | No `*_96h` column reaches any feature matrix | `guards.assert_feature_matrix_clean`, `tests/test_guards.py` | PASS |
| C2 | No `*_168h` value is used as a predictor | same, plus `tests/test_features.py::test_no_derived_feature_reads_a_target` | PASS |
| C3 | No hidden label column is readable | `guards.find_hidden_label_columns` + 8 parametrised tests | PASS |
| C4 | Every validation split is by whole lot | `guards.assert_folds_are_whole_lots`, asserted on every CV pass | PASS |
| C5 | Train / calibration / holdout share no lot and no component | `scripts/01_audit.py` §1.3 | PASS |
| C6 | No static limit is invented for the 7 empty cells | `scripts/08_reason_code_audit.py` §8.5 | PASS |
| C7 | No `module_b_disposition` column is emitted | `guards.assert_output_contract` | PASS |
| C8 | Output matches `ModuleB_Output_Contract.csv` exactly | `contract.check_against_reference` | PASS |
| C9 | The holdout's **contents** are read by exactly one gated script | `scripts/12` gate; every other stage reads `moduleb.holdout_manifest` and may only hash the file; `tests/test_release_gates.py::test_no_pre_freeze_stage_reads_the_holdout_contents` | PASS |
| C10 | A request is answered only when every lot in it is **proved complete** | `serving.assert_delivery_complete`, called unconditionally in `predict_frame`; `tests/test_serving.py` | PASS |
| C11 | `MIN_LOT_COHORT` is a secondary floor, never a completeness proof | `serving.runtime_contract_payload()["min_lot_cohort_role"]`; `scripts/14` R2 check | PASS |
| C12 | No shipped prediction path reaches the model without the proof | `tests/test_serving.py::test_no_shipped_prediction_path_skips_the_proof` | PASS |

## Fail-safe behaviour — all MUST

| # | Criterion | Checked by | Status |
|---|---|---|---|
| F1 | No NaN or inf in any emitted forecast | `guards.assert_predictions_sane` | PASS |
| F2 | No non-positive forecast is emitted | same; the 24 h fallback is logged, never silent | PASS |
| F3 | Every envelope value ≥ its point forecast | `contract.build_output`, `tests/test_pipeline.py` | PASS |
| F4 | Output row count and `component_id` order match the input | `guards.assert_output_contract` | PASS |
| F5 | Prediction is identical across row order, and bit-identical on a rerun of the same cohort | `tests/test_pipeline.py` | PASS |
| F5b | A request too small to support the lot features is refused; a deliberate override is recorded in the report | `tests/test_pipeline.py`, `tests/test_edge_cases.py` | PASS |

*F5 was rewritten 19 Sep 2026 (review finding F1). It previously read "identical across
row order and batch size" and was marked PASS on the strength of a test that split an
already feature-engineered frame and never called `predict_frame`. Cohort composition
does change the timing forecasts, so that criterion is withdrawn and F5b added.*

| F6 | Prediction is bit-identical on a rerun | `scripts/10` §10.7 | PASS |
| F7 | A missing feature column at predict time raises, never zero-fills | `tests/test_features.py` | PASS |
| F8 | A stale frozen artifact is refused | `freeze.load_frozen` digest check | PASS |
| F9 | Every clipping guard reports what it did | `predict.PredictReport` | PASS |
| F10 | A freeze without a genuine team sign-off is refused | `freeze.build_manifest` raises; `tests/test_release_gates.py` | PASS |
| F11 | The sign-off is embedded **before** the artifact is serialised | source order asserted by `scripts/14`; `tests/test_release_gates.py::test_the_manifest_is_complete_before_the_artifact_is_serialised` | PASS |
| F12 | Embedded and sidecar manifests agree, and the manifest verifies against its own digest | `freeze.load_frozen`; four tamper tests | PASS |
| F13 | A `REHEARSAL` artifact is refused for production use | `freeze.load_frozen(require_production=True)`; stage 10 asserts the refusal itself | PASS |
| F14 | Every recorded release decision is re-checked at freeze time | `decisions.check_release_decisions` in `freeze.freeze` and `scripts/11`; negative tests for D1, D10, D11 | PASS |
| F15 | A runtime-contract change is visible without a model change, and vice versa | `serving.runtime_contract_digest`; two directional tests; stale artifacts refused at load | PASS |
| F16 | The delivered holdout is the attested delivery | `holdout_manifest.verify_delivery_hash`, stages 0, 1, 10, 12, 14 | PASS |

## Evidence quality — all MUST

| # | Criterion | Threshold | Measured | Status |
|---|---|---|---|---|
| E1 | No single `B_` code fires on too many components | ≤ 25 % | 10.9 % (`B_WIDE_ENVELOPE`) | PASS |
| E2 | Not too many components carry any code | ≤ 60 % | 14.9 % | PASS |
| E3 | `B_NO_EARLY_SIGNAL` never appears alone | 0 | 0 | PASS |
| E4 | The p95 envelope's marginal coverage is near τ | 0.95 ± 0.05 | 0.933 – 0.974 | PASS |
| E5 | Tail coverage is **measured and reported**, never assumed | must be stated | 0.407 – 0.769, stated in the model card | PASS |
| E6 | The tail population is defined by the truth, not by the forecast | must not move with the model | pinned by `test_tail_is_ranked_by_true_drift_not_by_forecast_residual` | PASS |

*E5 was re-measured 19 Sep 2026 (review finding F3) as a corrective run. The superseded
figure was 0.473 – 0.802, computed with the tail ranked by forecast residual rather than
by observed drift; it is preserved in `results/` and must not be quoted as tail coverage.*


## Model quality — SHOULD

| # | Criterion | Measured | Status |
|---|---|---|---|
| M1 | Beats median-ratio on ≥ 2 parameters, whole-lot CV | 4 of 6 | PASS |
| M2 | No parameter is *worse* than median-ratio on train CV | none | PASS |
| M3 | No configuration in the grid beats the frozen one by > 5 % | max 4.5 % | PASS |
| M4 | Calibration MAE within ~15 % of the CV MAE | −14.5 % to +8.9 % | PASS |
| M5 | `Input_Leakage_Current` calibration ≥ median-ratio | −33 % | **FAIL — open** |

M5 is driven by a single component of 906; see `docs/FINDINGS_FOR_TEAM.md` and guide
§13. It is reported as a failure rather than reframed, and D11 closed on 19 Sep with
the relative-delta cap **off**, so it is carried into freeze as a known limitation
rather than an open decision.

## Revision R1 — 19 Sep 2026

Independent adversarial review. **F5 rewritten**: it previously read "identical across
row order and **batch size**" and was marked PASS on the strength of a test that split
an already feature-engineered frame and never called `predict_frame`. Cohort
composition does change the timing forecasts; the contract is now cohort-level and
enforced in code, and F5b was added. **E5 re-measured** as a corrective run after the
tail metric was found to rank by forecast residual rather than observed drift; E6 was
added to pin the definition. Full adjudication in `docs/ROUND1_ADJUDICATION.md`.

## Revision R2 — 19 Sep 2026

Release engineering. Four freeze blockers closed (**C10–C12**, **F10–F15**), the
holdout-access provenance corrected (**C9**, **F16**, decision D14), and nine withdrawn
claims removed from the executable surfaces as well as the prose. **The fitted model did
not change**, so every measured criterion above (E1–E6, M1–M5) is unchanged and still
comes from the recorded run of 18 Sep 2026. M5 remains a recorded **FAIL** and is
carried into the freeze as a known limitation rather than reframed.

Full disposition, including the S1–S8 secondary audit, in
`docs/ROUND2_FINAL_ADJUDICATION.md`. Gate status in `docs/FINAL_FREEZE_READINESS.md`.

## Not checkable in this environment

- Whether the holdout predictions are accurate. Only Sanskruti can score them,
  after the freeze, and asking earlier would defeat the exercise.
- Whether the declared measurement-noise CVs are true. They are the team's
  assumptions from the design record, labelled as such everywhere they are used.
- Whether the fusion layer uses the evidence columns correctly. That is
  Anushka's integration, and `docs/INTEGRATION_NOTE.md` states the constraints.
- Whether the expected lot sizes a caller declares are true. Module B checks the
  delivery against what it was told; it cannot audit the teller. What it can and does
  refuse is being told nothing.
