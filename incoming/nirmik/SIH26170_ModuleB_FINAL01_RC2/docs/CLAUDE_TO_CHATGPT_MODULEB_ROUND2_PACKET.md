# SIH 26170 · MODULE B
# CLAUDE → CHATGPT ROUND-2 VERIFICATION PACKET

**Prepared by:** Claude (Module B working engineer) · **For:** ChatGPT Plus, round 2
**Date:** 19 Sep 2026 · **Dataset:** `SIH26170-FINAL-01` · `v4-final1` · `LOTSPLIT-05`
**Config digest:** `8d0621941f86fbb817196919748c0d2007043391ec6539757720dd77ca46ab7d`
**State when written:** Round-1 findings adjudicated and corrected · model **not frozen**

---

> **This is a dated review packet, not current state.** It records what was sent to an
> independent reviewer on 19 Sep 2026, including the "was / now" pairs for the round-1
> findings. Two things in it have since been superseded:
>
> * where it says the holdout was "unopened", read the corrected provenance in
>   decision **D14** and `moduleb/holdout_manifest.py` — the predictor-only file *was*
>   read for structural checks; no targets existed, no forecast was made, no score was
>   seen, and the one-shot evaluation remains unspent;
> * the round-2 release-engineering work that followed is recorded in
>   `docs/ROUND2_FINAL_ADJUDICATION.md`, and the current state of the release is
>   `docs/FINAL_FREEZE_READINESS.md` and `RELEASE_MANIFEST.json`.
>
> Nothing in this file should be quoted as the current behaviour of Module B.

---

## 1. PURPOSE OF ROUND 2

Round 1 was a search. **Round 2 is a verification and regression lap.** The findings have already been made, adjudicated and acted on. Your job now is not to look for a different model, a better metric or a new architecture. It is to establish whether the corrections are real.

Five questions, in order:

1. **Were the accepted Round-1 findings corrected correctly** — in the implementation, not only in the prose?
2. **Did the fixes create new contract violations or regressions?** A fix that silences a symptom while moving the defect elsewhere is worse than the original.
3. **Does the documentation now match the implementation**, everywhere, including the files nobody reads?
4. **Do any unsupported claims remain**, including ones Round 1 did not raise?
5. **Is Module B technically ready to freeze?**

You may find new defects, and you should say so clearly if you do. But **do not manufacture novelty.** A clean Round 2 is an acceptable and useful outcome. An adversarial review that invents a finding because it feels obliged to produce one is less valuable than one that says "these fixes hold, here is what I checked".

Equally: **do not reward the work for having fixed things.** Round 1 found two genuine defects that the project's own 59-test suite had missed. That is evidence the suite had blind spots, not evidence that the project is careful. Verify the fixes the way you would verify a stranger's.

---

## 2. NON-NEGOTIABLE CONTRACT

These are contractual, not preferences. **A proposed fix that violates any of them must be rejected on that ground, and the ground must be stated.** A recommendation that breaks one also tells me you skimmed, and it discounts the surrounding findings.

1. **0 h and 24 h predictors only.** The 96 h measurements exist in the wider dataset and are forbidden as Module B predictors. Not for accuracy, not for a demo, not "just to compare".
2. **Whole-lot splitting only.** Never random-row validation. Components within a lot are dependent. Significance is tested on per-lot statistics: **42 lots is the sample size, not 3,151 rows.**
3. **The blind holdout stays blind and one-shot.** It has not been opened, predicted, inspected or scored. Do not propose anything that requires touching it, and do not use it to establish freeze readiness.
4. **No invented static limits.** Seven of eighteen variant × parameter cells have no `static_spec_max`. They stay empty. No default, no proxy, no "conservative estimate".
5. **Module B emits no disposition.** No PASS / MONITOR / REJECT, and no null placeholder column.
6. **The dataset is fixed.** A disappointing result is never grounds to regenerate it.
7. **Differences under 5 % MAE are ties**, whatever the rank or the p-value. The threshold was set before the results were seen.
8. **The p95 envelope is evidence, never a safety or detection guarantee.**
9. **No evaluator, master, or other team member's private files.** Work only from Nirmik's Module B package.
10. **FINAL-01 only for current results.** Candidate V1 appears only as clearly labelled history. The mock datasets are excluded entirely.

---

## 3. ROUND-1 FINDINGS AND FINAL ADJUDICATION

| # | Original claim | Adjudication | Evidence used | Change made | Files changed | Tests / checks | Fitted model changed? | Recorded numbers changed? | Remaining caveat |
|---|---|---|---|---|---|---|---|---|---|
| **F1** | Batch-size invariance claim is false; the test does not exercise the production path; the evidence layer is also request-dependent | **ACCEPTED** (BLOCKER) | Source read of `predict_frame` → `add_features`; then direct measurement on calibration lot `B_L23` (72 components), full-lot vs one-at-a-time | Serving contract declared **cohort-level**; `MIN_LOT_COHORT = 30` enforced in `predict_frame`; `allow_partial_lot=True` as a recorded override; false test renamed to what it proves; 4 new tests on the raw path | `moduleb/config.py`, `moduleb/guards.py`, `moduleb/predict.py`, `tests/test_pipeline.py`, `tests/test_edge_cases.py`, `tests/conftest.py`, `docs/COMPLETE_GUIDE.md` §6.5/§7.3/§7.4/§16.2/§17–§20, `docs/INTEGRATION_NOTE.md`, `docs/ACCEPTANCE_CRITERIA.md`, `docs/MODEL_CARD.md`, `docs/FINDINGS_FOR_TEAM.md`, `docs/DECISION_LOG.md` (D12), `README.md` | `test_raw_request_composition_changes_timing_forecasts`, `test_single_row_request_is_refused_by_default`, `test_partial_lot_override_is_recorded`, `test_evidence_layer_is_a_cohort_statistic`; stage 10 rerun | **No** | **No** — all recorded results were computed on full cohorts | Evidence-layer statistics remain cohort-dependent **by design**; this is now disclosed rather than eliminated |
| **F2** | The finite-sample conformal guarantee is stronger than the construction supports under within-lot dependence | **ACCEPTED-AS-CLAIM-CORRECTION** (MAJOR) | Source read of `fit_envelope`: whole-lot holdback, but component-level conformity scores inside those lots | Removed "finite-sample valid rather than asymptotic"; replaced with the empirical held-out-lot claim plus an explicit statement that no cluster-conformal derivation exists for the implemented construction | `docs/COMPLETE_GUIDE.md` §15.1, `docs/MODEL_CARD.md` | Claim checker: "finite-sample valid" is never asserted; model card must contain "empirical" + "exchangeab" | **No** | **No** | The envelope was **not** rebuilt. Six conformal lots would give very coarse lot-level calibration and there is no measured reason to expect improvement |
| **F3** | Tail coverage ranks by forecast residual, not observed drift | **ACCEPTED** (BLOCKER in effect — every document quoted it) | Source read of `coverage_report`: `drift_rank = y_true - point` | `coverage_report` now takes a **required** `x24` and ranks by `(y₁₆₈ − x₂₄)/x₂₄`; returns `tail_cut_rel_drift` and `tail_rank_basis`; stage 9 re-run as a **corrective run** | `moduleb/envelope.py`, `scripts/09_envelope_coverage.py`, `results/09_envelope_coverage.csv`, `docs/COMPLETE_GUIDE.md` §15 + glossary + appendices, `docs/MODEL_CARD.md`, `docs/INTEGRATION_NOTE.md`, `docs/ACCEPTANCE_CRITERIA.md` (E5, new E6), `docs/VALIDATION_SUMMARY.md`, `docs/FINDINGS_FOR_TEAM.md`, `README.md` | `test_tail_is_ranked_by_true_drift_not_by_forecast_residual`, `test_coverage_report_requires_x24` | **No** | **Yes** — tail coverage only. Marginal coverage unchanged. Old file preserved under its own name | The corrected numbers are **worse** (0.407–0.769 vs 0.473–0.802), which strengthens the "evidence, not a screen" conclusion |
| **F4** | The ±0.50 cap is post-hoc selection on calibration and should not be enabled | **ACCEPTED** (MAJOR) → **D11 = LEAVE_OFF** | `results/07_cap_sweep.csv`, `results/07_target_tails.csv`, `results/07_predicted_rel_delta.csv`, `results/07_error_concentration.csv` + a new train-only bound computation | D11 closed LEAVE_OFF; cap code path kept, disabled; "not a retune" reworded to "post-model guard candidate"; removed any implication ±0.50 is an established optimum or a false-positive fix | `docs/COMPLETE_GUIDE.md` §13.5–13.7, `docs/DECISION_LOG.md`, `docs/FINDINGS_FOR_TEAM.md`, `docs/MODEL_CARD.md`, `docs/RUNBOOK.md`, `docs/MASTER_PROMPT.md`, `docs/ACCEPTANCE_CRITERIA.md`, `README.md` | Claim checker: `FORECAST_REL_DELTA_CAP is None`; `LEAVE_OFF` in decision log; no document still calls D11 open | **No** | **No** | Acceptance criterion **M5 still FAILS** and is carried into freeze as a stated limitation |
| **F5** | "One forecast in 5,400" uses a denominator including the unpredicted holdout | **ACCEPTED** (MAJOR) | `results/07_cap_sweep.csv` contains only `train_oof` (n=3,151) and `calibration` (n=906) → **4,057** forecasts exist | Split denominators: at ±0.50, **1 of 906 calibration rows** and **2 of 3,151 train-OOF rows**, all `Input_Leakage_Current`. Explicit statement that no claim is made about the 1,343 holdout rows | `docs/COMPLETE_GUIDE.md` §13.5, `docs/FINDINGS_FOR_TEAM.md`, `scripts/14_verify_claims.py`, `README.md` | Claim checker **fails** on "one forecast in 5,400" and "rows touched (of 5,400)" outside a correction note; requires split denominators present | **No** | **No** — wording only, no rerun | None |
| **F6** | Pearson `r`/`r²` is not a ceiling on same-parameter predictability | **ACCEPTED** (MINOR) | Statistical reasoning; `r²` bounds linear association only | §9.2.1 now reads "a diagnostic of the simple linear early→late relationship; low values indicate weak linear signal but do not rule out nonlinear predictability" | `docs/COMPLETE_GUIDE.md` §9.2.1 | Claim checker: "ceiling on what a same-parameter…" never asserted | **No** | **No** | None |
| **F7** | Calibration-vs-CV absolute MAE comparison does not prove the protocol sound | **ACCEPTED** (MINOR) — and the better diagnostic was computed rather than the prose merely weakened | New computation on permitted train + calibration data: median per-lot advantage over median-ratio, same method on 42 CV lots and 12 calibration lots | Claim downgraded; new §5.5 in `scripts/05_calibration_report.py` produces `results/05_relative_effect_transfer.csv`; guide §11.2 now carries the transfer table | `scripts/05_calibration_report.py`, `results/05_relative_effect_transfer.csv`, `docs/COMPLETE_GUIDE.md` §11.2, `docs/VALIDATION_SUMMARY.md` | Stage 5 rerun; claim checker: file exists; "validation protocol is sound" never asserted | **No** | **No** — new file, no existing number altered | Five of six transfer within ±2.6 pp; `Input_Leakage_Current` shifts −4.39 pp and is documented as the explicit exception |
| **A1** | "Sparse enough to be actionable" overstates what the audit measures | **ACCEPTED-AS-CLAIM-CORRECTION** | The audit measures firing rates against pre-declared gates; Module B has no correctness label for its codes and by design never will | §14.7 now reads "Every code passes the pre-declared sparsity gate. Sparsity limits alert flooding. It does not establish precision, usefulness or downstream actionability." | `docs/COMPLETE_GUIDE.md` §14.7 | Claim checker: old phrase never asserted | **No** | **No** | Precision of the reason codes remains unmeasurable from Module B's permitted data |
| **A2** | The tail conclusion must be regenerated after F3 before being repeated | **ACCEPTED** — discharged by the F3 corrective run | Follows from F3 | All quoted tail figures recomputed and replaced; superseded file retained | Same set as F3 | Claim checker fails if `0.473` appears outside a correction note in any document | **No** | **Yes** — via F3 | The `Output_Rise_Time` "fails first" ranking happens to survive, but is now quoted as a recomputed number (**0.407**), not preserved because it was convenient |

**Nothing was rejected.** Three *remediations proposed within accepted findings* were declined, each on a stated ground — see §4 and §7.

---

## 4. F1 — SERVING CONTRACT FIX

### 4.1 What the old test actually proved

`tests/test_pipeline.py::test_prediction_is_batch_size_invariant` received the `synth_feat` fixture — **already feature-engineered** — split it, and called `models.predict_one()` on the two halves. The own-lot medians had been computed by `add_features` *before* the split and were therefore identical in both halves by construction.

The test proved: *a fitted estimator is insensitive to how its design-matrix rows are chunked.* That is true and uninteresting.

It was cited as proving: *a one-component API call returns the same answer as a full-lot call.* It does not exercise that path at all. `predict.predict_frame()` calls `add_features(raw, artifact["base"])`, which recomputes lot medians **from whatever rows are in the request**.

### 4.2 Why single-component prediction is not equivalent

Two mechanisms, both real:

**Feature construction.** The three timing parameters use the `own+lot+cross` feature set, which includes `lotmed_<p>_0h` and `lotmed_<p>_24h` for all six parameters. On a one-row request the lot median *is* that row's own value.

**Evidence construction.** `reason_codes.drift_z_within_variant()` computes robust z-scores from the current request frame. On one row, MAD = 0, so `_robust_z()` returns zeros for all six parameters and `idxmax()` resolves the primary parameter from an all-zero row. `B_WIDE_ENVELOPE` ranks width within the request and skips groups under `_MIN_RANKING_POP = 10`. `B_LOT_OUTLIER_24H` requires real lot context.

### 4.3 The measurement — calibration lot `B_L23`, 72 components

Full-lot request vs one-component-at-a-time, through `predict_frame` on raw 16-column input:

| Parameter | Feature set | max \|Δ\| | median \|Δ\| | components changed |
|---|---|---|---|---|
| `IDDQ` | `own` | **0.00000 %** | 0.00000 % | **0 / 72** |
| `Input_Leakage_Current` | `own` | **0.00000 %** | 0.00000 % | **0 / 72** |
| `Active_Supply_Current` | `own` | **0.00000 %** | 0.00000 % | **0 / 72** |
| `Propagation_Delay` | `own+lot+cross` | **7.180 %** | 0.551 % | **72 / 72** |
| `Output_Rise_Time` | `own+lot+cross` | **3.857 %** | 0.633 % | **72 / 72** |
| `Output_Fall_Time` | `own+lot+cross` | **3.279 %** | 0.656 % | **72 / 72** |

For scale: 7.18 % is most of the **8.95 %** advantage Module B has over the median-ratio baseline on `Propagation_Delay`.

### 4.4 The primary-parameter failure

Under the full-lot call, the first six components of `B_L23` received five different values of `module_b_primary_parameter` (`Input_Leakage_Current`, `Active_Supply_Current`, `Output_Fall_Time`, `IDDQ`). Under one-row calls, **every one returned `IDDQ`** — the degenerate all-zero-z outcome. Reason codes present under the cohort call (e.g. `B_WIDE_ENVELOPE:Input_Leakage_Current`) vanished entirely.

### 4.5 The fix

**Contract:** cohort-level. A request carries whole lots.

**Enforcement point:** `moduleb/predict.py::predict_frame`, immediately after the existing input and quality guards:

```python
guards.assert_input_clean(raw, allow_target=allow_target, name=name)
guards.assert_data_quality(raw, name=name, expect_targets=allow_target)
if not allow_partial_lot:
    guards.assert_cohort_sufficient(raw, min_rows=config.MIN_LOT_COHORT, name=name)
```

**Guard:** `moduleb/guards.py::assert_cohort_sufficient` groups by `lot_id`, raises `DataQualityError` naming every offending lot and its size.

**Constant:** `moduleb.config.MIN_LOT_COHORT = 30`, deliberately **outside** the `FROZEN_V1` block and **not** in `frozen_config_digest()`. Justification given in the source comment: the smallest real FINAL-01 lot carries 68 components; 30 is a little under half, so a partial delivery still works while a handful of rows does not. It is a pragmatic threshold, stated as such, not a statistical one.

**Override:** `predict_frame(..., allow_partial_lot=True)` proceeds, sets `report.partial_lot_override = True`, which makes `report.clean` **False**, and emits a warning line through `PredictReport.lines()`.

**New tests** (`tests/test_pipeline.py`):

| Test | What it pins |
|---|---|
| `test_raw_request_composition_changes_timing_forecasts` | Starts from **raw** frames, asserts the three `own` parameters are bit-identical and that at least one timing parameter moves. Fails loudly if the divergence ever disappears, so nobody re-derives the old claim |
| `test_single_row_request_is_refused_by_default` | The guard fires |
| `test_partial_lot_override_is_recorded` | Override works, is recorded, and makes `clean` false |
| `test_evidence_layer_is_a_cohort_statistic` | Single-row primary parameter collapses to one label; cohort call discriminates |

Renamed: `test_prediction_is_batch_size_invariant` → `test_estimator_is_insensitive_to_chunking_a_built_design_matrix`, with a docstring recording why it was renamed.

`tests/conftest.py` fixture lot size raised 20 → 35, because 20 is smaller than any real FINAL-01 lot and the fixture was quietly exercising a request shape production now refuses.

### 4.6 Why the fix was made at the serving-contract level

Three options were considered. Two were declined:

| Option | Declined because |
|---|---|
| **Remove the timing lot features** so a one-row API is trivially correct | A model change forbidden by D2/D5. The 24-configuration grid also says no configuration change clears the 5 % tie threshold, so there is no independent case for it |
| **Freeze training reference distributions for the reason codes** (Round 1's "preferred if the backend must request one component at a time") | Changes evidence semantics, requires a full reason-code firing-rate re-audit, and alters the config digest. Unnecessary once the contract is cohort-level — and burn-in is physically performed in lots, so the backend does not in fact need single-component calls |

The chosen option changes **no fitted parameter and no previously valid forecast.** The frozen pipeline has always scored whole cohorts — the 1,343-row holdout is eighteen complete lots in one call. Only the *promise about the API* was wrong, so the promise was corrected.

### 4.7 What you should check

1. **Is the guard on the real production path?** Trace every route that reaches a prediction. `predict_frame` is the intended chokepoint; `predict_csv` delegates to it.
2. **Does any alternate path bypass it?** Specifically: does `scripts/12_predict_holdout.py` go through `predict_frame`? Does `scripts/10_dryrun_freeze_predict.py`? Can `models.predict_one` or `contract.build_output` be called directly by anything shipped, skipping the guard? Is `moduleb/__init__.py` exporting something that permits it?
3. **Is `allow_partial_lot=True` sufficiently loud and auditable?** It sets a report field and a warning line. Is that enough, or should it also be recorded in the output frame or the run log? Argue the case.
4. **Does the integration documentation actually tell Anushka this?** `docs/INTEGRATION_NOTE.md` — check the "Required input columns, and the request unit" section and the "What you can rely on, and the one thing you cannot" section. Is the constraint discoverable by someone who reads only that file?
5. **Do the new tests genuinely begin from raw inputs?** Check that `_raw()` strips targets and that `predict_frame` — not `models.predict_one` — is the function under test.
6. **Does any sentence anywhere still claim arbitrary batch-size or one-row equivalence?** The claim checker has negative checks for this; verify their coverage is real rather than nominal.

---

## 5. F3 — TAIL-COVERAGE CORRECTION

### 5.1 The erroneous formula

```python
covered = y_true <= upper
drift_rank = y_true - point          # forecast residual, NOT drift
cut = np.quantile(drift_rank, tail_pctl)
tail = drift_rank >= cut
```

Every document described the result as coverage of the **worst-drifting decile**. `y_true - point` selects the components the point model most **under-predicted**. Those are different populations: a component can be badly under-predicted while barely drifting, and a heavy drifter the model saw coming never enters the residual tail at all. The definition also depended on the forecast, so changing the model silently changed which components were called the worst drifters.

### 5.2 The corrected formula

```python
covered = y_true <= upper
true_rel_drift = (y_true - x24) / x24     # the physical quantity
cut = np.quantile(true_rel_drift, tail_pctl)
tail = true_rel_drift >= cut
```

`x24` is a **required positional argument**, not optional with a fallback — a silent fallback is exactly how a corrected metric gets un-corrected. The returned dict now also carries `tail_cut_rel_drift` and `tail_rank_basis="true_relative_drift_from_24h"`, so the result carries its own definition.

### 5.3 The numbers — τ = 0.95, calibration lots

| Parameter | superseded (residual-ranked) | **corrected (true drift)** | Δ |
|---|---|---|---|
| `IDDQ` | 0.8022 | **0.6813** | −0.121 |
| `Input_Leakage_Current` | 0.7363 | **0.7692** | +0.033 |
| `Active_Supply_Current` | 0.6044 | **0.5934** | −0.011 |
| `Propagation_Delay` | 0.6154 | **0.6044** | −0.011 |
| `Output_Rise_Time` | 0.4725 | **0.4066** | −0.066 |
| `Output_Fall_Time` | 0.5495 | **0.4505** | −0.099 |

**Corrected range 0.407 – 0.769**, against the superseded 0.473 – 0.802.

**Marginal coverage is unchanged** (0.933 – 0.974) — it never depended on the tail definition. At τ = 0.99 the tail figures are also unchanged, because at that level essentially everything is covered in both rankings.

The correction makes the envelope's limitation **larger**. The qualitative conclusion — evidence, not a screen — is strengthened rather than rescued.

### 5.4 Provenance

| File | Status |
|---|---|
| `results/09_envelope_coverage.csv` | **Authoritative.** Corrective run, 19 Sep, tail ranked by true drift, carries `tail_rank_basis` |
| `results/09_envelope_coverage_SUPERSEDED_2026-09-18_residual_ranked.csv` | **Historical.** Preserved for provenance. Not bad arithmetic — it measures a different quantity than the documents claimed. **Never to be quoted as tail coverage** |

The correction is recorded as D13 in `docs/DECISION_LOG.md` and flagged in the header of `scripts/09_envelope_coverage.py` and the docstring of `coverage_report`.

### 5.5 What you should check

1. **Does the implementation rank by true 24→168 h relative drift?** Read `moduleb/envelope.py::coverage_report`.
2. **Does the correction use 96 h anywhere?** It must not. `x24` and `y_true` only.
3. **Does the calculation use only train/calibration truth?** `scripts/09_envelope_coverage.py` fits on train, scores on calibration. Confirm no holdout path.
4. **Is the statistic consistently named** across `COMPLETE_GUIDE.md` §15, the glossary, `MODEL_CARD.md`, `INTEGRATION_NOTE.md`, `VALIDATION_SUMMARY.md` and `ACCEPTANCE_CRITERIA.md`?
5. **Can the old numbers silently reappear?** Check whether `0.473` / `0.802` survive anywhere outside an explicit correction note. The claim checker enforces this — assess whether its window heuristic (±400 characters, correction-marker keywords) is robust or gameable.
6. **Is p95 still never represented as a safety or detection guarantee**, in any file?

---

## 6. D11 — CAP DECISION CLOSED

### 6.1 The decision

**`FORECAST_REL_DELTA_CAP = None`. LEAVE_OFF.** Closed 19 Sep 2026, recorded in `docs/DECISION_LOG.md`. The code path is kept, disabled, documented and unit-tested, as a candidate safeguard for a future release.

### 6.2 The complete argument

**Post-hoc selection.** The three candidate values (0.25, 0.50, 1.00) were evaluated against calibration truth, and ±0.50 is attractive precisely because it most improves the one extreme calibration forecast. Calling it "not a retune" was too narrow: the fitted coefficients are untouched, but choosing an *inference transformation* from observed calibration outcomes is still post-hoc pipeline selection. The protocol permitted exactly one pre-declared calibration decision — the `Output_Fall_Time` feature-set rule (D10) — and that is executed and spent.

**The motivating case is a true positive.** Component `C03478`, lot `B_L23`, CMOS_B: measured 0 h = 0.51133 µA, 24 h = 0.69613 µA (+36.14 %), true 168 h = 1.04689 µA (+50.39 % from 24 h), forecast 168 h = 2.05571 µA (+195.30 %). CMOS_B's `Input_Leakage_Current` static limit is 1.0 µA. **Both the truth and the forecast exceed it**, so `B_FORECAST_EXCEEDS_LIMIT` fired correctly. The defect is the *magnitude of the assertion*, not its direction. A cap fixes an exaggeration, not a false alarm.

**No independently justified cap is also effective.** The natural independent bound is "do not assert a drift larger than anything the training targets contain". For `Input_Leakage_Current` the training relative-delta distribution is:

| statistic | value | would it clip the +1.95 forecast? |
|---|---|---|
| p99 | **0.2472** | Yes — but see below |
| p99.9 | **7.8097** | **No** |
| max | **13.3193** | **No** |

So the two genuinely train-derived bounds are far too high to affect the offending forecast. The only bound tight enough is ≈ p99 = 0.247, which sits **inside the range the training distribution itself says can contain legitimate drift**, and which would also begin clipping other parameters: train-OOF predicted relative-delta maxima are 0.190 (IDDQ), 0.164 (`Propagation_Delay`), 0.137 (`Output_Rise_Time`), 0.138 (`Output_Fall_Time`) against per-parameter p99 of 0.184 / 0.108 / 0.099 / 0.113. That configuration has **never been measured**, and measuring it now — after calibration truth has been seen — is the same post-hoc selection this finding rejects.

**±0.25 is also empirically worse than ±0.50** on this data (−23.3 % vs −27.7 % improvement), because it additionally clips two legitimate large-drift forecasts. The optimum is not monotone, which is itself a warning that the curve is being read off very few points.

**Suppression risk.** A hard cap can silence a future legitimate extreme forecast, and nothing in the available evidence distinguishes that case from this one.

### 6.3 What remains open as a limitation

Extrapolation risk is **uncapped and documented**. Acceptance criterion **M5 fails**: `Input_Leakage_Current` is 33 % worse than median-ratio on the calibration lots (macro-lot −33.08 %; row-weighted −31.51 %), driven by one component of 906 carrying **27.7 %** of that parameter's total calibration error. Remove that row and Module B is 1.075× median-ratio — a tie. This is stated as a failure, not reframed.

**What would reopen D11:** a cap fixed independently of the observed calibration outcome — a source-backed engineering or physical assertion bound, or a genuinely pre-specified train-only rule — followed by a calibration check showing it controls the intended failure mode without creating materially worse misses.

### 6.4 What you should check

1. **Is any cap enabled anywhere in actual inference?** `moduleb/config.py::FORECAST_REL_DELTA_CAP` should be `None`; `moduleb/predict.py` should skip the clip block entirely when it is.
2. **Do docs and config agree?** Check `COMPLETE_GUIDE.md` §13.7, `DECISION_LOG.md`, `FINDINGS_FOR_TEAM.md` §4, `MODEL_CARD.md` limitations, `MASTER_PROMPT.md`, `ACCEPTANCE_CRITERIA.md` M5.
3. **Does any stale ±0.50 recommendation remain** — anything implying ±0.50 is an established accuracy optimum or a false-positive fix?
4. **Does extrapolation evidence still reach fusion without becoming a disposition?** The `evidence_<p>_pred_rel_delta_from_24h` columns and `B_HIGH_FORECAST_DRIFT` should still carry the signal; no disposition column should exist.
5. **Is D11 actually recorded as closed before freeze**, with a date and reasoning, in a file the freeze gate can be audited against?

---

## 7. F2, F4, F5, F6, F7, A1, A2 — CLAIM AND METHOD CLEANUP

### F2 — conformal guarantee

| | |
|---|---|
| **Was** | "The conformal quantile is the `ceil((n+1)(1−α))`-th smallest score — the `(n+1)` is not cosmetic; it is what makes the guarantee **finite-sample valid rather than asymptotic**." |
| **Now** | Six complete training lots are withheld from envelope fitting and supply the conformity scores. **What is claimed:** an *empirical* out-of-lot calibration — marginal coverage measured on twelve unseen calibration lots. **What is not claimed:** a finite-sample split-conformal theorem. That result needs exchangeable calibration and test units; the conformity scores here are per-component inside those six lots, while this project treats within-lot components as dependent everywhere else. No cluster-conformal derivation has been produced for the implemented construction. |
| **Code or prose** | **Prose only.** The envelope was deliberately not rebuilt — with six conformal lots a lot-level scheme would be very coarse, and Round 1 itself said not to claim an improvement until measured. |
| **Verifying check** | Claim checker asserts "finite-sample valid" is never asserted in any document; `MODEL_CARD.md` must contain both "empirical" and "exchangeab". |

### F4 — the cap decision

| | |
|---|---|
| **Was** | The cap presented as an open decision, described as "not a retune", with ±0.50 implicitly favoured. |
| **Now** | D11 closed **LEAVE_OFF**. Reworded to "post-model guard candidate; enabling it is a model/pipeline behaviour change". No implication that ±0.50 is an accuracy optimum or a false-positive fix. Full reasoning in §6 above. |
| **Code or prose** | **Prose + config state.** `FORECAST_REL_DELTA_CAP` remains `None`; the code path is retained and tested. |
| **Verifying check** | Claim checker asserts the cap is `None`, that `LEAVE_OFF` appears in the decision log, and that no document still says "must close before freeze" or "The one open decision". |

### F5 — the cap denominator

| | |
|---|---|
| **Was** | "±0.50 touches exactly **one forecast in 5,400**"; table column headed "rows touched (of 5,400)". |
| **Now** | Split denominators. At ±0.50: **1 of 906 calibration rows** and **2 of 3,151 train-OOF rows**, all `Input_Leakage_Current`, zero elsewhere. **4,057 forecasts exist.** Explicit sentence: *"No statement is made about how many of the 1,343 holdout rows it would clip, because the holdout has not been predicted and will not be until after freeze."* |
| **Code or prose** | **Prose + checker.** No rerun needed. |
| **Verifying check** | Claim checker **fails** on "one forecast in 5,400" and "rows touched (of 5,400)" anywhere outside a correction note, and requires "906 rows" and "3,151 rows" to be present in the guide. |

### F6 — Pearson r as a ceiling

| | |
|---|---|
| **Was** | "This is **the ceiling** on what a same-parameter early feature can do." |
| **Now** | "This is a diagnostic of the **simple linear** early→late relationship, and `r²` … is the share of late-drift variance that linear association explains. A low value means weak *linear* signal. It is **not** an upper bound on predictability: a nonlinear function, or an interaction between the 0 h and 24 h readings, is not constrained by a Pearson correlation." |
| **Code or prose** | **Prose only.** |
| **Verifying check** | Claim checker asserts "ceiling on what a same-parameter" is never asserted. |

### F7 — CV-to-calibration transfer

| | |
|---|---|
| **Was** | "…the **strongest single piece of evidence that the validation protocol is sound**." |
| **Now** | "The absence of a one-direction shift is reassuring against a large *global* optimism effect" — followed by the diagnostic that actually tests the relative effect. |
| **Code or prose** | **Both.** New §5.5 in `scripts/05_calibration_report.py`; new `results/05_relative_effect_transfer.csv`. |

Median per-lot advantage over median-ratio, computed identically on 42 CV lots and 12 calibration lots:

| Parameter | CV | lots won | Calibration | lots won | shift |
|---|---|---|---|---|---|
| `IDDQ` | +1.27 % | 22/42 | +0.69 % | 7/12 | −0.58 pp |
| `Input_Leakage_Current` | +7.02 % | 34/42 | **+2.64 %** | 8/12 | **−4.39 pp** |
| `Active_Supply_Current` | +1.87 % | 25/42 | +4.04 % | 10/12 | +2.17 pp |
| `Propagation_Delay` | +7.90 % | 31/42 | +10.10 % | 8/12 | +2.19 pp |
| `Output_Rise_Time` | +9.23 % | 33/42 | +7.46 % | 9/12 | −1.76 pp |
| `Output_Fall_Time` | +6.34 % | 30/42 | +8.92 % | 9/12 | +2.58 pp |

Described as **generally stable lot-level transfer with an explicit `Input_Leakage_Current` exception** — not as proof the validation protocol is universally sound. Note the detail that matters: even for input leakage the *typical calibration lot* retains a +2.64 % advantage while the *mean* reverses to −33 %. The gap between those two sentences is one component.

**Verifying check:** claim checker asserts `results/05_relative_effect_transfer.csv` exists and that "validation protocol is sound" is never asserted.

### A1 — reason-code actionability

| | |
|---|---|
| **Was** | "**PASS.** Every code is **sparse enough to be actionable**." |
| **Now** | "**PASS.** Every code passes the pre-declared sparsity gate. Sparsity limits alert flooding. It does not establish precision, usefulness or downstream actionability — and as §14.1 says, Module B has no correctness label for its codes and by design never will." |
| **Code or prose** | **Prose only.** |
| **Verifying check** | Claim checker asserts "sparse enough to be actionable" is never asserted. |

### A2 — regenerate the tail conclusion

| | |
|---|---|
| **Was** | Tail figures and the "`Output_Rise_Time` fails first" ranking quoted from the residual-ranked metric. |
| **Now** | All recomputed. `Output_Rise_Time` **does** remain worst, but at **0.407**, and it is quoted as a recomputed number rather than preserved because the qualitative conclusion was convenient. The guide states plainly: *"The correction makes the envelope's limitation larger, not smaller, so the conclusion below is strengthened rather than rescued."* |
| **Code or prose** | **Both** — discharged by the F3 corrective run. |
| **Verifying check** | Claim checker fails if `0.473` appears outside a correction note in any document. |

---

## 8. REGRESSION / FREEZE-READINESS EVIDENCE

### 8.1 Current verified state

| Item | Value |
|---|---|
| Config digest | `8d0621941f86fbb817196919748c0d2007043391ec6539757720dd77ca46ab7d` — **unchanged by all R1 corrections** |
| Unit tests | **65 pass**, 0 fail (was 59) |
| Claim checker | **148 checks pass**, 0 fail (was 53) |
| Negative phrase checks | Included — a withdrawn phrase may survive only within ±400 characters of a correction marker |
| `FORECAST_REL_DELTA_CAP` | `None` |
| `MIN_LOT_COHORT` | `30` |
| Frozen artifact | **None exists** (`models/` absent) |
| Holdout | **Unopened, unpredicted, unscored** (`results/ModuleB_Final_Holdout_Predictions.csv` absent) |
| Dataset | **Unchanged** — SHA-256 prefixes `f4965db3803b9c93` (train), `5f6e977e2ea746dc` (calibration), `e8082400cc815049` (holdout) |
| 96 h predictors | **None added** — guards check the file *and* every feature matrix |
| Invented static limits | **None** — 7 of 18 cells remain `NaN`; limit codes verified to fire 0 times there |
| Module B disposition | **Not added** — `guards.assert_output_contract` rejects it |

### 8.2 What the corrective runs altered

| Stage re-run | Why | What it produced | Model config touched? |
|---|---|---|---|
| 5 — calibration report | New F7 relative-effect diagnostic | `results/05_relative_effect_transfer.csv` (new); existing metrics unchanged | No |
| 9 — envelope coverage | **F3 corrective run** | `results/09_envelope_coverage.csv` (tail coverage changed, marginal unchanged); superseded file preserved | No |
| 10 — freeze/predict rehearsal | Confirm the cohort guard does not break the real path | Clean: 906 rows across 12 lots, determinism check bit-identical | No |
| 13 — validation summary | Regenerated from `results/` | `docs/VALIDATION_SUMMARY.md` | No |
| 14 — claim checker | 53 → 148 checks | 148/148 pass | No |
| Full test suite | All R1 changes | 65/65 pass | No |

**Stages 0–4 and 6–8 were not re-run**, because nothing they depend on changed: `features.py`, `featureset.py`, `models.py`, `cv.py`, `metrics.py` and `baselines.py` are untouched by Round 1, and the config digest confirms it.

**Derived diagnostic artefacts changed. The fitted model configuration did not.** No fitted parameter moved; no previously valid cohort-level forecast changed. The `MIN_LOT_COHORT` guard converts silently-wrong outputs into explicit errors — it does not alter any output that was ever correct.

---

## 9. FILE MANIFEST FOR CHATGPT

Attach exactly these five. Do not attach more; context spent on duplicates is context not spent on inspection.

| # | File | Why ChatGPT needs it |
|---|---|---|
| 1 | **`CLAUDE_TO_CHATGPT_MODULEB_ROUND2_PACKET.md`** (this file) | The complete statement of what Round 1 found, what was accepted, what changed, and what Round 2 must verify. |
| 2 | **`COMPLETE_GUIDE.md`** (the corrected complete guide) | The full technical description of Module B with all R1 corrections applied and marked. This is where stale-claim hunting happens. |
| 3 | **`ROUND1_ADJUDICATION.md`** | The formal per-finding adjudication with evidence, file lists and digest impact. Needed to check that what was claimed to change actually changed. |
| 4 | **`DECISION_LOG.md`** | D11 (LEAVE_OFF), D12 (cohort contract) and D13 (tail metric) with dates and reasoning. Needed to verify the freeze boundary. |
| 5 | **`SIH26170_ModuleB_FINAL01.zip`** | The source. Mandatory for any finding about implementation — guard placement, the corrected formula, test contents, config values, the claim checker. |

### Duplicate resolution

If two copies of the Round-1 adjudication are present (for example one named `Round1 adjudication.md` and one named `Final01 round1 adjudication.md`), **they are the same document.** Attach only one. The copy inside the ZIP at `docs/ROUND1_ADJUDICATION.md` is authoritative.

Quick check that you have the post-R1 build rather than the 18 Sep one: the ZIP must contain `results/09_envelope_coverage_SUPERSEDED_2026-09-18_residual_ranked.csv`. If that file is absent, you have the wrong ZIP.

---

## 10. EXACT ROUND-2 TASK FOR CHATGPT

> Paste everything between the rules, after attaching the five files.

---

You are performing the **second and final adversarial verification lap** of SIH 26170 Module B — early 168 h drift forecasting.

Round 1 already found defects. **Do not reward the work for fixing them. Verify them.** Two of the Round-1 findings exposed real implementation bugs that the project's own 59-test suite had missed. That tells you the suite had blind spots, not that the project is careful. Inspect the corrections the way you would inspect a stranger's.

Attached: this packet, the corrected complete guide, the Round-1 adjudication, the decision log, and the source ZIP.

**Priority order:**

1. Verify **F1** is genuinely fixed **on the real raw-input production path** — not only in the tests, and not only in the prose.
2. Verify **F3** now measures the intended population.
3. Verify **D11** is closed cleanly with the cap **OFF**, and that nothing stale recommends enabling it.
4. Check every **F2 / F4 / F5 / F6 / F7 / A1 / A2** correction against the source, the code and the results — not against Claude's description of them.
5. Search for **regressions introduced by the fixes**. A fix that moves a defect is worse than the original.
6. Search for **stale claims** across all documents, including files nobody reads.
7. Decide whether anything **still blocks freeze**.

**When a finding concerns implementation, open the ZIP and read the code.** A verification claim without a source citation is an opinion.

**Classify every Round-1 item** as exactly one of: `VERIFIED_FIXED`, `PARTIALLY_FIXED`, `NOT_FIXED`, `NEW_DEFECT`, `NEEDS_DATA`.

**Do not merely repeat Claude's adjudication.** If you agree, say what you checked that makes you agree. If a source inspection disproves a Round-1 concern, say so plainly — that is a valuable result.

**Non-negotiable rules.** Reject any proposed action that violates one, and state which: 0 h/24 h predictors only · whole-lot splitting only · blind one-shot holdout, unopened · no invented static limits · no Module B disposition · dataset fixed · under 5 % MAE is a tie · the p95 envelope is never a safety or detection guarantee · FINAL-01 only for current results.

**Do not invent numbers.** If a claim needs a figure you have not been shown, write "I need X to judge this" and move on.

Begin with the Round-1 fix verification, in the schema below.

---

## 11. REQUIRED ROUND-2 CHATGPT OUTPUT FORMAT

```text
## ROUND-1 FIX VERIFICATION

### F1
- STATUS: VERIFIED_FIXED | PARTIALLY_FIXED | NOT_FIXED | NEEDS_DATA
- EVIDENCE:
- REGRESSION FOUND:
- REQUIRED ACTION:

### F2
- STATUS:
- EVIDENCE:
- REGRESSION FOUND:
- REQUIRED ACTION:

### F3
- STATUS:
- EVIDENCE:
- REGRESSION FOUND:
- REQUIRED ACTION:

### F4
- STATUS:
- EVIDENCE:
- REGRESSION FOUND:
- REQUIRED ACTION:

### F5
- STATUS:
- EVIDENCE:
- REGRESSION FOUND:
- REQUIRED ACTION:

### F6
- STATUS:
- EVIDENCE:
- REGRESSION FOUND:
- REQUIRED ACTION:

### F7
- STATUS:
- EVIDENCE:
- REGRESSION FOUND:
- REQUIRED ACTION:

### A1
- STATUS:
- EVIDENCE:
- REGRESSION FOUND:
- REQUIRED ACTION:

### A2
- STATUS:
- EVIDENCE:
- REGRESSION FOUND:
- REQUIRED ACTION:

### D11
- STATUS:
- EVIDENCE:
- REGRESSION FOUND:
- REQUIRED ACTION:

## NEW FINDINGS

### N<n>. <one-line claim>
- SEVERITY: BLOCKER | MAJOR | MINOR
- TYPE:
- WHERE:
- WHY IT MATTERS:
- HOW I WOULD CHECK IT:
- CONFIDENCE:
- WHAT I ASSUMED:

(If none: "No new defect found.")

## CONTRACT AUDIT

- 0h/24h only:
- whole-lot:
- holdout blind:
- static limits:
- no disposition:
- dataset unchanged:
- 5% tie rule:
- p95 language:
- cohort-serving contract:

## CLAIM AUDIT

List any stale, overstated, or contradictory claims that remain, with file and location.
If none, say so explicitly.

## FREEZE VERDICT

- TECHNICAL_BLOCKER: YES | NO
- BLOCKERS:
- NON_BLOCKING_LIMITATIONS:
- READY_TO_FREEZE_AFTER_TEAM_SIGNOFF: YES | NO
- REASON:
```

**The freeze verdict is about technical readiness only.** You must **not** run, request, or recommend opening the blind holdout to establish readiness. A verdict that depends on seeing holdout results is not a valid verdict.

---

## 12. ROUND-2 REVIEW RULES

- **No praise.** If something is right, say "correct" and move on. Spend the space on what is not.
- **No generic ML suggestions.** "Consider cross-validation" is worthless — whole-lot GroupKFold is already in use. Advice that ignores what has been done is the failure mode this lap most needs to avoid.
- **No changing the dataset.** It is frozen.
- **No 96 h.** Ever.
- **No random-row validation.** Lots are the unit of independence.
- **No opening the holdout.** Not to check, not to illustrate, not to settle a disagreement.
- **No inventing static limits** for the seven empty cells.
- **No Module B disposition**, not even a null placeholder.
- **No treating a sub-5 % difference as a win.**
- **No safety or detection guarantee** attached to the p95 envelope.
- **No fabricated numbers.** If you have not been shown it, you do not have it.
- **Every criticism must name a falsifiable check** — something that could come back negative. If the check cannot fail, it is an opinion, and label it as one.
- **If a source inspection disproves a Round-1 concern, say so.** Being right about that is worth more than adding a finding.
- **Do not manufacture a new defect merely because this is an adversarial review.** An empty severity tier is a legitimate result.
- **A clean Round 2 is acceptable** if the fixes genuinely withstand inspection.

---

## 13. WHAT CHATGPT MUST PAY SPECIAL ATTENTION TO

### A. Serving semantics

Can the model still be called with an undersized or partial cohort through **any unguarded path**? Trace every route from raw input to a written output frame. `predict_frame` is the intended chokepoint. Check `predict_csv`, `scripts/10_dryrun_freeze_predict.py`, `scripts/12_predict_holdout.py`, and whether `models.predict_one` or `contract.build_output` are reachable directly from anything shipped. If a bypass exists, that is a `NOT_FIXED` or a `NEW_DEFECT`, not a nitpick.

### B. Lot-derived features

Do the same rules apply consistently across **CV, calibration scoring, the stage-10 rehearsal, freeze-time fitting and final prediction**? Cross-validation builds folds from a single fully-featured frame while inference builds features per request — confirm that this asymmetry does not make the CV scores optimistic relative to how the model will actually be called. This is the deepest question in the packet and it was not raised in Round 1.

### C. Evidence semantics

Does `module_b_primary_parameter`, or any reason-code statistic, still depend on request composition in a way the integration contract **does not disclose**? The guide and integration note now state that the evidence layer is a cohort statistic. Check that the disclosure is complete: are there reason codes whose cohort-dependence is not described? Is `_MIN_RANKING_POP = 10` documented anywhere a reader of `INTEGRATION_NOTE.md` would find it? What happens to `B_WIDE_ENVELOPE` for a legitimate 30-row lot where a parameter drives fewer than 10 components?

### D. Corrective-run provenance

Are the corrected F3 numbers **clearly separated** from the recorded 18 Sep run rather than silently blended into it? Check that `results/09_envelope_coverage.csv` and its superseded twin are both present and distinguishable, that every document quoting tail coverage says which run it came from, and that nothing presents a corrected value as though 18 Sep produced it.

### E. Config digest semantics — **this question is important, and do not assume Claude's choice is correct**

`MIN_LOT_COHORT = 30` was deliberately placed **outside** the `FROZEN_V1` block and **outside** `frozen_config_digest()`. Claude's reasoning: it alters no fitted parameter and no previously valid forecast, so it is a serving-contract setting rather than model behaviour.

**The counter-argument deserves a serious hearing.** Two deployments could carry the **same model digest** and behave differently — one refusing a 20-row cohort, another accepting it with `allow_partial_lot=True` and returning materially different timing forecasts. If you believe the serving configuration needs its own **contract or runtime digest**, or a separate manifest entry recorded at freeze time alongside the model digest, say so. That change would not touch the fitted-model digest and is therefore available before freeze.

State plainly whether you think the current arrangement is defensible, and if not, what the minimum fix is.

### F. Claim checker

Do the **148 automated checks** meaningfully cover the withdrawn claims, or are they cosmetic? Specifically assess the `nowhere()` helper in `scripts/14_verify_claims.py`: it permits a withdrawn phrase to survive only within ±400 characters of a correction marker drawn from a fixed keyword list. Is that window robust, or could a stale claim sit just inside it and pass? Is there obvious stale wording **outside** the checker's search scope — files it does not read, or phrasings it does not match?

### G. Freeze boundary

Is **every decision that can affect prediction behaviour or output semantics** now closed and recorded? Enumerate them from the decision log and check for gaps. In particular: is there anything that would change a forecast, an envelope, a reason code, or a contract column that is not covered by a dated, closed decision entry?

---

## 14. CLAUDE'S CURRENT FREEZE ASSESSMENT

**Current Claude assessment: TECHNICALLY READY TO FREEZE, after Round 2 and team sign-off.**

This is Claude's assessment and **ChatGPT must verify it independently.** Do not adopt it. If you reach a different conclusion, say so and give the blocker.

Remaining human steps, neither of which the code can supply:

1. Round-2 independent verification — this lap.
2. Team sign-off, required by the `scripts/11_freeze.py --team-signoff` gate.

### Known limitations that are **not** blockers

These are stated, documented and carried into freeze deliberately. They are not defects to be fixed before freezing; they are the honest description of what Module B is.

1. **Two parameters remain ties with the simple baseline** under the declared 5 % rule. On the 42-lot train CV, `IDDQ` (+0.44 %, p = 0.603) and `Active_Supply_Current` (+3.86 %, p = 0.034 — significant but under the threshold) are ties with median-ratio. Module B is a learned forecaster for four parameters and a well-calibrated scaling rule for two.
2. **`Input_Leakage_Current` has extreme-tail instability.** Acceptance criterion M5 fails: −33 % against median-ratio on calibration, driven by one component of 906 carrying 27.7 % of that parameter's error. The training target's max is 53.9× its own p99 — no other parameter exceeds 15×.
3. **Extrapolation risk remains uncapped.** D11 = LEAVE_OFF. The failure mode is documented, the code path exists and is disabled, and the conditions to reopen are written down.
4. **Envelope tail coverage is materially below nominal** — 0.407 – 0.769 at τ = 0.95, worst on `Output_Rise_Time`. The envelope is **evidence for fusion, never a screen**. A fusion rule treating "inside the envelope" as a pass fails first there.
5. **The dataset is synthetic.** Every number describes `SIH26170-FINAL-01`. None of it is a claim about real silicon, and no safety margin is presented as a NASA, ISRO or MIL-STD requirement.
6. **The measurement-noise CVs are `ASSUMED`**, from the design record §6.3, not measured. Everything derived from them — `B_NO_EARLY_SIGNAL`, the SNR table, the noise-floor ratios — inherits that status.
7. **Module B does not own the final disposition.** PASS / MONITOR / REJECT belongs to Module A + fusion (D1). No disposition column is emitted, not even a placeholder.
8. **Cohort context is required** for the lot-aware timing forecasts and for the entire evidence layer. This is now the declared contract (D12), enforced at `MIN_LOT_COHORT = 30`, and disclosed to integration.

Additionally, two items are recorded as **still needing data** and are explicitly *not* being resolved before freeze, because resolving either now would repeat the post-hoc selection Round 1 rejected:

- Whether a **per-parameter train-p99 cap** would control the extrapolation without harming the timing parameters. The right experiment for a future release, pre-declared before its calibration is opened.
- Whether a **cluster-conformal construction** gives a better envelope. Six conformal lots is too coarse to expect a gain, and it would be a pre-freeze change to a component D2 froze.

---

*End of packet. Attach the five files in §9, paste the prompt in §10, and require the schema in §11.*
