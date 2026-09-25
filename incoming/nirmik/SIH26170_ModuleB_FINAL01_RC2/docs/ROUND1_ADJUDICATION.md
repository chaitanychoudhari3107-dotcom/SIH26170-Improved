# Round-1 adjudication — independent adversarial review

**Date:** 19 Sep 2026 · **Module:** B · **Dataset:** `SIH26170-FINAL-01`
**Config digest before and after:** `8d0621941f86fbb8…` — **unchanged**
**Holdout:** not opened, not predicted, not scored. **Dataset:** not regenerated.

Seven findings and two claim corrections were raised. **Nine adjudicated: eight
ACCEPT, one ACCEPT-as-wording. Nothing rejected**, because every point was either
verifiable at source or a claim the evidence did not support. Two were BLOCKERs and
both are closed.

---

## ROUND-1 ADJUDICATION

### F1 — the batch-size invariance claim was false, and its test did not test it

- **STATUS: ACCEPT** (BLOCKER)
- **EVIDENCE:** Verified at source and then measured, not taken on trust.
  `predict.predict_frame` calls `add_features(raw, ...)`, which recomputes own-lot
  medians from the rows in the request. The old test split `synth_feat` — already
  feature-engineered — so the medians were fixed before the split and could not move.
  Measured on calibration lot `B_L23` (72 components), scoring each component alone
  versus with its lot:

  | Parameter | feature set | max \|Δ\| | median \|Δ\| | components changed |
  |---|---|---|---|---|
  | IDDQ | `own` | 0.00000 % | 0.00000 % | 0 / 72 |
  | Input_Leakage_Current | `own` | 0.00000 % | 0.00000 % | 0 / 72 |
  | Active_Supply_Current | `own` | 0.00000 % | 0.00000 % | 0 / 72 |
  | Propagation_Delay | `own+lot+cross` | **7.180 %** | 0.551 % | **72 / 72** |
  | Output_Rise_Time | `own+lot+cross` | 3.857 % | 0.633 % | **72 / 72** |
  | Output_Fall_Time | `own+lot+cross` | 3.279 % | 0.656 % | **72 / 72** |

  7.18 % is most of the 8.95 % advantage the model has over median-ratio on
  propagation delay. The evidence layer is worse: on a one-row request every robust z
  is zero, so `module_b_primary_parameter` returned **`IDDQ` for every component
  tested**, against a spread of five different parameters under the full-lot call, and
  the reason codes vanished.
- **CONTRACT CHECK:** No rule touched. Removing the lot features would have been a
  model change under D2/D5 and was rejected on that ground.
- **CHANGE REQUIRED:** Declare and enforce a **cohort-level serving contract**.
  `MIN_LOT_COHORT = 30`; `predict_frame` refuses a request in which any lot carries
  fewer rows, naming them. `allow_partial_lot=True` proceeds, sets
  `report.partial_lot_override`, and makes `report.clean` false. The old test is
  renamed to what it actually proves and four new tests exercise the real path.
- **WHY:** The wrong answer was well-formed and silent. Burn-in is performed in lots,
  the lot is what makes lot-relative context meaningful, and the frozen pipeline has
  always scored whole cohorts — the holdout is eighteen complete lots in one call.
  Only the *promise about the API* was wrong, so the contract is corrected rather
  than the model.
- **FILES AFFECTED:** `moduleb/config.py`, `moduleb/guards.py`, `moduleb/predict.py`,
  `tests/test_pipeline.py`, `tests/test_edge_cases.py`, `tests/conftest.py`,
  `docs/COMPLETE_GUIDE.md` §6.5/§7.3/§7.4/§16.2/§17/§18/§19/§20,
  `docs/INTEGRATION_NOTE.md`, `docs/ACCEPTANCE_CRITERIA.md`, `docs/MODEL_CARD.md`,
  `docs/FINDINGS_FOR_TEAM.md`, `docs/DECISION_LOG.md` (D12), `README.md`.
- **RESULT/DIGEST IMPACT:** **None.** Every recorded result was computed on full
  cohorts, so nothing is recomputed. `MIN_LOT_COHORT` sits outside the `FROZEN_V1`
  block and the digest is unchanged: no fitted parameter moved and no previously
  valid forecast changed. The guard converts a silently wrong output into an error.
- **CHECK PERFORMED:** the measurement above; `test_raw_request_composition_changes_timing_forecasts`,
  `test_single_row_request_is_refused_by_default`,
  `test_partial_lot_override_is_recorded`, `test_evidence_layer_is_a_cohort_statistic`;
  stage 10 rerun clean (906 rows across 12 lots).

**Rejected remediations, with reasons.** *Freezing training reference distributions
for the reason codes* would make single-component evidence stable, but it changes
evidence semantics, requires a full firing-rate re-audit and alters the digest — and
it is unnecessary once the contract is cohort-level. *Removing the timing lot
features* is a model change forbidden by D2/D5 and unjustified by the grid.

---

### F2 — the conformal guarantee was stated more strongly than the construction supports

- **STATUS: ACCEPT** (wording; MAJOR)
- **EVIDENCE:** `fit_envelope` withholds six whole lots, then forms the conformal
  correction from **component-level** conformity scores inside them. Split-conformal
  finite-sample coverage needs exchangeable calibration and test units. This project
  forbids row-level significance testing precisely because within-lot components are
  dependent, so it cannot simultaneously treat within-lot component scores as
  exchangeable calibration units. Whole-lot holdback removes leakage; it does not
  supply exchangeability.
- **CONTRACT CHECK:** None.
- **CHANGE REQUIRED:** Remove "finite-sample valid rather than asymptotic". Keep and
  sharpen the two statements that are true: six complete training lots are withheld
  from envelope fitting, and marginal coverage was **measured** on twelve unseen
  calibration lots. State plainly that no cluster-conformal derivation has been
  produced for the implemented score construction.
- **WHY:** The empirical claim is the one the evidence supports, it is sufficient for
  how the envelope is used, and it is cheaper to defend than a theorem nobody derived.
- **FILES AFFECTED:** `docs/COMPLETE_GUIDE.md` §15.1, `docs/MODEL_CARD.md`.
- **RESULT/DIGEST IMPACT:** None — wording only. The envelope was **not** rebuilt: a
  lot-level conformity scheme with six conformal lots would be very coarse and there
  is no measured reason to believe it better.
- **CHECK PERFORMED:** claim checker asserts "finite-sample valid" is never asserted
  anywhere; model card carries the exchangeability paragraph.

---

### F3 — "tail coverage" was computed from the forecast residual, not observed drift

- **STATUS: ACCEPT** (BLOCKER in effect; every document quoted it)
- **EVIDENCE:** `coverage_report` computed `drift_rank = y_true - point` and selected
  the top decile of that, while the guide, model card, integration note, validation
  summary and glossary all called it the worst-drifting decile. A residual is not a
  drift: a component can be badly under-predicted while barely drifting, and a heavy
  drifter the model saw coming never enters the residual tail. Worse, the tail
  definition depended on the forecast, so changing the model silently changed which
  components were called the worst drifters.
- **CONTRACT CHECK:** The correction uses permitted train/calibration data only.
- **CHANGE REQUIRED:** `coverage_report` now takes `x24` as a **required** argument
  and ranks by observed relative drift `(y₁₆₈ − x₂₄)/x₂₄`. It also returns
  `tail_cut_rel_drift` and `tail_rank_basis` so the result carries its own definition.
  Stage 9 re-run as a **corrective run**.
- **WHY:** The metric must measure the quantity its name claims, and the tail must be
  a property of the truth rather than of the model.
- **FILES AFFECTED:** `moduleb/envelope.py`, `scripts/09_envelope_coverage.py`,
  `results/09_envelope_coverage.csv`, `docs/COMPLETE_GUIDE.md` §15 + glossary +
  appendices, `docs/MODEL_CARD.md`, `docs/INTEGRATION_NOTE.md`,
  `docs/ACCEPTANCE_CRITERIA.md` (E5, new E6), `docs/VALIDATION_SUMMARY.md`,
  `docs/FINDINGS_FOR_TEAM.md`, `README.md`.
- **RESULT/DIGEST IMPACT:** Tail coverage changes; **marginal coverage does not**, as
  expected. τ = 0.95:

  | Parameter | superseded (residual-ranked) | **corrected (true drift)** | Δ |
  |---|---|---|---|
  | IDDQ | 0.8022 | **0.6813** | −0.121 |
  | Input_Leakage_Current | 0.7363 | **0.7692** | +0.033 |
  | Active_Supply_Current | 0.6044 | **0.5934** | −0.011 |
  | Propagation_Delay | 0.6154 | **0.6044** | −0.011 |
  | Output_Rise_Time | 0.4725 | **0.4066** | −0.066 |
  | Output_Fall_Time | 0.5495 | **0.4505** | −0.099 |

  Corrected range **0.407 – 0.769** against 0.473 – 0.802. **The envelope's
  limitation is larger than previously reported**, so the qualitative conclusion —
  evidence, not a screen — is strengthened, not rescued. Digest unchanged; no model
  parameter is involved. The 18 Sep numbers are preserved as
  `results/09_envelope_coverage_SUPERSEDED_2026-09-18_residual_ranked.csv` and are
  never presented as though the 18 Sep run produced the corrected value.
- **CHECK PERFORMED:** `test_tail_is_ranked_by_true_drift_not_by_forecast_residual`
  scrambles the point forecast and asserts the tail membership, cut and coverage do
  not move; `test_coverage_report_requires_x24` prevents a silent fallback.

---

### F4 — the ±0.50 cap is post-hoc selection on calibration

- **STATUS: ACCEPT** (MAJOR) — and D11 closes **LEAVE_OFF**
- **EVIDENCE:** The three candidate values were evaluated against calibration truth
  and ±0.50 is attractive because it most improves the one extreme calibration
  forecast. "Not a retune" was too narrow: the coefficients are untouched, but
  choosing an inference transformation from observed calibration outcomes is post-hoc
  pipeline selection, and the protocol allowed exactly one pre-declared calibration
  decision — the fall-time rule (D10), now spent. The motivating component is also
  **not a false positive**: true value 1.047 µA and forecast both exceed CMOS_B's
  1.0 µA limit, so `B_FORECAST_EXCEEDS_LIMIT` was correct.

  **An argument the review did not make, checked here:** no independently-justified
  cap is also effective. A bound taken from the training target distribution sits at
  p99.9 = **7.81** or max = **13.32** for `Input_Leakage_Current` — both far above the
  offending **+1.95** forecast, so neither would clip it. The only train-derived bound
  tight enough is ≈ p99 = **0.247**, which is inside the range the training data says
  is legitimate and which would also begin clipping timing forecasts (train-OOF maxima
  0.137 – 0.190 against per-parameter p99 of 0.099 – 0.184). That has never been
  measured, and measuring it now — after seeing calibration — is the same post-hoc
  selection this finding rejects.
- **CONTRACT CHECK:** Leaving it off keeps the package reproducing the frozen
  Candidate V1 model exactly, honouring D5.
- **CHANGE REQUIRED:** Close D11 as LEAVE_OFF. Keep the code path, disabled and
  documented. Reword "not a retune" to a post-model guard candidate whose enabling is
  a model/pipeline behaviour change. Remove any implication that ±0.50 is an
  established accuracy optimum or a false-positive fix.
- **WHY:** The project is at the stage of closing honestly, not of squeezing one more
  calibration improvement out of one component.
- **FILES AFFECTED:** `docs/COMPLETE_GUIDE.md` §13.5–13.7, `docs/DECISION_LOG.md`,
  `docs/FINDINGS_FOR_TEAM.md`, `docs/MODEL_CARD.md`, `docs/RUNBOOK.md`,
  `docs/MASTER_PROMPT.md`, `docs/ACCEPTANCE_CRITERIA.md`, `README.md`.
- **RESULT/DIGEST IMPACT:** None. `FORECAST_REL_DELTA_CAP` stays `None`; digest
  unchanged. Acceptance criterion **M5 still FAILS** and is carried into freeze as a
  known limitation rather than papered over.
- **CHECK PERFORMED:** the train-bound computation above; claim checker asserts the
  cap is `None` and that no document still calls D11 open.

---

### F5 — "one forecast in 5,400" used a denominator that includes the unpredicted holdout

- **STATUS: ACCEPT** (MAJOR)
- **EVIDENCE:** `results/07_cap_sweep.csv` contains `train_oof` (n = 3,151) and
  `calibration` (n = 906) only. 3,151 + 906 = **4,057** forecasts exist. The 1,343
  holdout rows have never been predicted, so no statement about them is observable.
- **CONTRACT CHECK:** The old phrasing did not *use* holdout information, but it
  implied a measurement over rows that were never scored — which is exactly the kind
  of claim the blind-holdout rule exists to prevent.
- **CHANGE REQUIRED:** Split denominators. At ±0.50: **1 of 906 calibration rows** and
  **2 of 3,151 train-OOF rows**, all `Input_Leakage_Current`, zero elsewhere. State
  explicitly that no claim is made about the holdout.
- **WHY:** A denominator is a claim about what was measured.
- **FILES AFFECTED:** `docs/COMPLETE_GUIDE.md` §13.5, `docs/FINDINGS_FOR_TEAM.md`,
  `scripts/14_verify_claims.py`, `README.md`.
- **RESULT/DIGEST IMPACT:** None — documentation only, no rerun.
- **CHECK PERFORMED:** the claim checker now **fails** on the phrases "one forecast in
  5,400" and "rows touched (of 5,400)" anywhere outside a correction note, and
  requires the split denominators to be present.

---

### F6 — Pearson r is not a ceiling on same-parameter predictability

- **STATUS: ACCEPT** (MINOR)
- **EVIDENCE:** `r²` bounds what a **linear** association explains. It places no
  bound on nonlinear transforms or on an interaction between the 0 h and 24 h readings,
  both of which are permitted same-parameter functions.
- **CONTRACT CHECK:** None.
- **CHANGE REQUIRED:** §9.2.1 now reads "a diagnostic of the simple linear early→late
  relationship; low values indicate weak linear signal but do not rule out nonlinear
  predictability".
- **WHY:** It was a stronger statement than the statistic supports, and it would not
  survive a judge who knows what a correlation is.
- **FILES AFFECTED:** `docs/COMPLETE_GUIDE.md` §9.2.1.
- **RESULT/DIGEST IMPACT:** None.
- **CHECK PERFORMED:** claim checker asserts "ceiling on what a same-parameter…" is
  never asserted.

---

### F7 — the calibration-vs-CV comparison does not prove the protocol sound

- **STATUS: ACCEPT** (MINOR) — and the better diagnostic was computed
- **EVIDENCE:** §11.2 compared **absolute** Module B MAE, which is confounded by
  whether these twelve lots are intrinsically easier, and cannot see whether the
  **baseline-relative** effect transferred. `Input_Leakage_Current` is the
  counter-example: absolute MAE improves 9.2 % while the comparison against
  median-ratio reverses.
- **CONTRACT CHECK:** The added diagnostic uses permitted train and calibration data
  only; no model refit, no holdout.
- **CHANGE REQUIRED:** Downgrade the claim, and add the diagnostic that actually tests
  it — the median per-lot advantage over median-ratio, computed identically on the 42
  CV lots and the 12 calibration lots:

  | Parameter | CV | Calibration | shift |
  |---|---|---|---|
  | IDDQ | +1.27 % | +0.69 % | −0.58 pp |
  | Input_Leakage_Current | +7.02 % | +2.64 % | **−4.39 pp** |
  | Active_Supply_Current | +1.87 % | +4.04 % | +2.17 pp |
  | Propagation_Delay | +7.90 % | +10.10 % | +2.19 pp |
  | Output_Rise_Time | +9.23 % | +7.46 % | −1.76 pp |
  | Output_Fall_Time | +6.34 % | +8.92 % | +2.58 pp |

  Five of six transfer within ±2.6 percentage points. Input leakage shifts furthest —
  and even there the *typical lot* keeps a +2.64 % advantage while the *mean* reverses
  to −33 %. The gap between those two sentences is one component.
- **WHY:** It converts a claim that was merely reassuring into one that is measured.
- **FILES AFFECTED:** `scripts/05_calibration_report.py` (new §5.5),
  `results/05_relative_effect_transfer.csv`, `docs/COMPLETE_GUIDE.md` §11.2,
  `docs/VALIDATION_SUMMARY.md`.
- **RESULT/DIGEST IMPACT:** New results file; no existing number changes; digest
  unchanged.
- **CHECK PERFORMED:** stage 5 rerun; claim checker asserts the file exists and that
  "validation protocol is sound" is never asserted.

---

### A1 — "sparse enough to be actionable" overstates what the audit measures

- **STATUS: ACCEPT**
- **EVIDENCE:** The audit measures firing rates against pre-declared gates. Module B
  has no correctness label for its reason codes and, as §14.1 says, by design never
  will. Sparsity bounds alert flooding; it says nothing about precision.
- **CONTRACT CHECK:** None.
- **CHANGE REQUIRED:** §14.7 now reads "Every code passes the pre-declared sparsity
  gate. Sparsity limits alert flooding. It does not establish precision, usefulness or
  downstream actionability."
- **FILES AFFECTED:** `docs/COMPLETE_GUIDE.md` §14.7.
- **RESULT/DIGEST IMPACT:** None.
- **CHECK PERFORMED:** claim checker asserts the old phrase is never asserted.

---

### A2 — the tail numbers are superseded until F3 is recomputed

- **STATUS: ACCEPT** — discharged by the F3 corrective run
- **EVIDENCE:** Every quoted tail figure and the "`Output_Rise_Time` fails first"
  ranking derived from the residual-ranked metric.
- **CHANGE REQUIRED:** Recompute and replace everywhere; keep the superseded file.
- **RESULT/DIGEST IMPACT:** The qualitative conclusion survives and the ranking
  happens to survive — `Output_Rise_Time` is still worst — but it is now **0.407**,
  not 0.473, and it is quoted as a recomputed number rather than preserved because it
  was convenient.
- **CHECK PERFORMED:** claim checker fails if `0.473` appears outside a correction
  note in any document.

---

## D11 — RELATIVE-DELTA CAP

- **DECISION: LEAVE_OFF**
- **VALUE:** `FORECAST_REL_DELTA_CAP = None`. Code path kept, disabled, tested.
- **WHY:** (1) the value would be selected after observing calibration truth, and the
  single pre-declared calibration decision is spent; (2) the motivating case is a true
  positive with an exaggerated magnitude, not a false alarm — both truth and forecast
  exceed the 1.0 µA limit; (3) **no independently-justified cap is also effective** —
  a train-derived bound sits at 7.81 or 13.32, far above the +1.95 forecast, while the
  only tight enough one (≈ 0.247) is inside the legitimate training range and would
  begin clipping timing forecasts; (4) a hard cap can suppress a future legitimate
  extreme forecast and nothing distinguishes the two cases.
- **EVIDENCE USED:** `results/07_cap_sweep.csv`, `results/07_target_tails.csv`,
  `results/07_predicted_rel_delta.csv`, `results/07_error_concentration.csv`.
- **DECISION_LOG ENTRY:** written — *2026-09-19 · FINAL-01 · D11 — the extrapolation
  cap stays OFF*, with the four reasons and the conditions that would reopen it.
- **Consequence carried forward:** acceptance criterion **M5 fails** and is carried
  into freeze as a stated limitation.

---

## CHANGES MADE

**Code**
- `moduleb/envelope.py` — `coverage_report` takes a required `x24` and ranks the tail
  by observed relative drift; returns `tail_cut_rel_drift` and `tail_rank_basis`.
- `moduleb/config.py` — `MIN_LOT_COHORT = 30`, outside `FROZEN_V1`, documented.
- `moduleb/guards.py` — `assert_cohort_sufficient`.
- `moduleb/predict.py` — cohort guard wired in; `allow_partial_lot`; report carries
  `n_lots` and `partial_lot_override`, and the override makes `clean` false.

**Tests** — 59 → **65**
- replaced `test_prediction_is_batch_size_invariant` with
  `test_estimator_is_insensitive_to_chunking_a_built_design_matrix`, named for what it
  proves;
- added `test_raw_request_composition_changes_timing_forecasts`,
  `test_single_row_request_is_refused_by_default`,
  `test_partial_lot_override_is_recorded`, `test_evidence_layer_is_a_cohort_statistic`;
- added `test_tail_is_ranked_by_true_drift_not_by_forecast_residual`,
  `test_coverage_report_requires_x24`;
- rewrote `test_single_component_predicts` as
  `test_single_component_is_refused_then_works_under_override`;
- `conftest.py` lot size 20 → 35, because 20 is smaller than any real FINAL-01 lot and
  the fixture was quietly exercising a shape production now refuses.

**Scripts**
- `scripts/09_envelope_coverage.py` — corrective-run header and the new call.
- `scripts/05_calibration_report.py` — new §5.5, the relative-effect transfer diagnostic.
- `scripts/14_verify_claims.py` — 53 → **148** checks, including negative checks that
  fail if a withdrawn phrase is asserted anywhere outside a correction note.

**Results**
- `results/09_envelope_coverage.csv` — corrective run.
- `results/09_envelope_coverage_SUPERSEDED_2026-09-18_residual_ranked.csv` — preserved.
- `results/05_relative_effect_transfer.csv` — new.

**Documentation** — `COMPLETE_GUIDE.md`, `MODEL_CARD.md`, `INTEGRATION_NOTE.md`,
`ACCEPTANCE_CRITERIA.md`, `DECISION_LOG.md` (D11, D12, D13), `FINDINGS_FOR_TEAM.md`,
`RUNBOOK.md`, `MASTER_PROMPT.md`, `VALIDATION_SUMMARY.md` (regenerated from
`results/`), `README.md`, and this file.

---

## SAFE RECOMPUTATIONS

| Stage | Why | Holdout involved |
|---|---|---|
| 5 — calibration report | new relative-effect diagnostic | no |
| 9 — envelope coverage | **corrective run**, F3 | no |
| 10 — freeze/predict rehearsal | confirm the cohort guard does not break the real path (906 rows across 12 lots, clean) | no — stand-in only |
| 13 — validation summary | regenerated from `results/` | no |
| 14 — claim checker | 148 / 148 pass | no |
| full test suite | 65 / 65 pass | no |

**Stages 0–4 and 6–8 were not re-run**, because nothing they depend on changed:
`features.py`, `featureset.py`, `models.py`, `cv.py`, `metrics.py` and `baselines.py`
are untouched and the config digest is unchanged.

**`03_HOLDOUT_AFTER_FREEZE/ModuleB_Holdout.csv` was not opened, not predicted, not
scored. No hidden targets were requested. The dataset was not regenerated. No frozen
artifact exists.**

---

## CLAIMS CHANGED

| Old claim | New defensible claim |
|---|---|
| "Batch size does not matter. One component or 1,343 gives identical forecasts." | Cohort composition changes the timing forecasts by up to 7.18 % and degenerates the evidence layer. **Send whole lots**; requests under `MIN_LOT_COHORT` are refused. |
| F5: "Prediction is identical across row order and **batch size** — PASS" | F5: identical across row order and bit-identical on a rerun of the same cohort. **F5b** added for the refusal and the recorded override. |
| "the `(n+1)` … makes the guarantee finite-sample valid rather than asymptotic" | Six complete training lots are withheld and marginal coverage was **measured** on twelve unseen calibration lots. No cluster-conformal derivation has been produced for the implemented score construction. |
| Tail coverage **0.473 – 0.802**, ranked by forecast residual | Tail coverage **0.407 – 0.769**, ranked by observed relative drift from 24 h. Worst still `Output_Rise_Time`, now **0.407**. |
| "±0.50 touches exactly one forecast in 5,400" | 1 of 906 calibration rows and 2 of 3,151 train-OOF rows. No claim is made about the 1,343 holdout rows. |
| The cap "is not a retune" | It is a post-model guard candidate; enabling it is a model/pipeline behaviour change. D11 closed LEAVE_OFF. |
| `r` is "the ceiling on what a same-parameter early feature can do" | A diagnostic of the simple **linear** early→late relationship; low values do not rule out nonlinear predictability. |
| "the strongest single piece of evidence that the validation protocol is sound" | Reassuring against a large global optimism effect, but not proof that every baseline-relative effect transferred — with the per-lot advantage transfer table now supplying the direct test. |
| "Every code is sparse enough to be actionable" | Every code passes the pre-declared sparsity gate. Sparsity limits alert flooding; it does not establish precision or actionability. |
| D11 open, "must close before freeze" | D11 **closed 19 Sep — LEAVE_OFF**, with the conditions that would reopen it. |

---

## ITEMS REJECTED

**No finding was rejected.** Three *remediations* proposed within accepted findings
were declined, each on a stated ground:

| Proposed | Declined because |
|---|---|
| Freeze training reference distributions for the reason codes (F1's "preferred if the backend must request one component at a time") | It changes evidence semantics, requires a full firing-rate re-audit and alters the config digest. The cohort contract makes it unnecessary, and the backend does not in fact need single-component calls — burn-in is performed in lots. |
| Remove the timing lot features to make a single-row API easy (F1 explicitly warns against this) | A model change under D2/D5, and the 24-configuration grid says no configuration change clears the 5 % tie threshold. |
| Rebuild the envelope with a lot-level conformity scheme (F2's alternative) | With only six conformal lots the calibration would be very coarse, and the review itself says not to claim an improvement until measured. The empirical claim is sufficient for how the envelope is used. |

---

## ITEMS STILL NEEDING DATA

| Question | Smallest permitted check | Why it is not being run now |
|---|---|---|
| Would a **per-parameter train-p99 cap** control the extrapolation without harming the timing parameters? | Re-score all six parameters on train OOF and calibration with per-parameter caps fixed from the training target distribution alone. Permitted data only. | Running it now, after calibration truth has been seen, is the same post-hoc selection D11 rejected. It is the right experiment for a future release, pre-declared before its calibration is opened. |
| Does a cluster-conformal construction give a better envelope? | Rebuild with lot-level conformity scores; measure marginal and tail coverage on the same twelve lots. | Six conformal lots is too coarse to expect a gain, and it would be a pre-freeze change to a component D2 froze. |
| Is `Input_Leakage_Current`'s reversal one component or a population property? | Already answered as far as permitted data allows: 27.7 % of the parameter's calibration error is one row, and removing it leaves a 1.075× tie. Anything further needs the holdout. | The holdout is a one-shot and stays blind. |

---

## FREEZE READINESS

- **STATUS: READY** — no technical blocker remains.
- **BLOCKERS:** none in the package. Two process items, both human:
  1. **Team sign-off** for `scripts/11_freeze.py --team-signoff`, which is required by
     the gate and is not something the code can supply.
  2. **Round 2 of the independent review**, which was planned. Both round-1 BLOCKERs
     (F1, F3) are closed, so this is a verification lap rather than a gate — but it
     was the agreed process and the round-2 prompt is ready in the handoff's Part 12.
- **State:** config digest `8d0621941f86fbb8…` unchanged · `FORECAST_REL_DELTA_CAP =
  None` · `MIN_LOT_COHORT = 30` · 65 / 65 tests · 148 / 148 claim checks · no frozen
  artifact · **holdout unspent**.
- **Known limitation carried into freeze:** acceptance criterion **M5 fails** —
  `Input_Leakage_Current` is worse than median-ratio on calibration, driven by one
  component of 906. Stated, not reframed.
- **NEXT COMMANDS:**

```bash
python -m pytest tests/ -q                 # 65 passed
python scripts/14_verify_claims.py         # 148 / 148

# after round 2 and team sign-off:
python scripts/11_freeze.py --team-signoff "<who approved, and when>"
python scripts/12_predict_holdout.py --frozen     # once
```
