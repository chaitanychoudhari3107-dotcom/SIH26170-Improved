# Round 2 — final adjudication

19 September 2026 · `ModuleB-FINAL01-RC2` · owner Nirmik

Round 1 (`docs/ROUND1_ADJUDICATION.md`) was an independent review of the *analysis*.
Round 2 is the release-engineering pass: what would have to be true for another
engineer to receive this package, verify it without this conversation, sign off
honestly, freeze it without editing code, run the holdout exactly once, and integrate
the result without discovering an undocumented contract.

**The fitted model did not change in this round.** No coefficient, hyper-parameter,
feature set or envelope offset moved; `frozen_config_digest()` still begins
`8d0621941f86fbb8`. Everything below is about refusal, provenance and claims.

---

## P0 — freeze blockers

### P0-B1 · A row count was standing in for a completeness proof — **CLOSED**

**The defect.** `predict_frame` refused a request only when some lot carried fewer
than `MIN_LOT_COHORT = 30` rows. The real FINAL-01 lots carry 68–82 components, so a
lot delivered with a quarter of itself missing passed the guard. It then produced
forecasts computed against the wrong cohort — the timing models read own-lot medians
and every evidence column ranks a component against the others present — and the
output frame looked exactly like a correct one. Counting the rows you were sent cannot
detect the rows you were not sent.

**The fix.** `moduleb/serving.py`. Completeness is proved from outside the rows, by one
of two sources:

| Proof | What supplies it | What it proves |
|---|---|---|
| `expected_lot_sizes={lot: n}` | request metadata, lot traveller, MES record | each delivered lot carries exactly the components it should |
| `DeliveryAttestation(sha256, n_rows, n_lots)` | the custodian's manifest entry for a whole file | the file is the delivery that was issued, entire |

Neither supplied ⇒ refused. `MIN_LOT_COHORT` survives as a **secondary sanity floor**
and is documented as one, never as the proof. `allow_partial_lot=True` remains the only
way past, and now records the offending lots, their observed and expected counts, the
serving-contract version and the runtime digest, and forces `report.clean = False`.

**Paths traced.** `predict_frame`, `predict_csv`, stage 10, stage 12, `moduleb/__init__`,
the notebooks. The check is unconditional inside `predict_frame`, before
`add_features`, so no caller reaches `models.predict_one` or `contract.build_output`
without passing it. `tests/test_serving.py::test_no_shipped_prediction_path_skips_the_proof`
scans every shipped call site and fails if one omits a proof or an explicit override.

**Tests.** Complete lot accepted (both proofs) · incomplete lot **above** the floor
rejected · incomplete lot below the floor rejected · expected-count mismatch rejected ·
undeclared lot rejected · no proof rejected · attestation hash/row mismatch rejected ·
override works and is recorded · override makes the report non-clean · complete-lot
predictions bit-identical under either proof · no shipped path bypasses the guard.

**Not done:** the fitted model was not touched, and no previously valid forecast moved.

---

### P0-B2 · Sign-off lived outside the artifact — **CLOSED**

**The defect.** Stage 11 called `joblib.dump`, *then* wrote `team_signoff` into a
manifest sidecar. The serialised artifact therefore carried a manifest with no approval
in it, and the only record of who approved the freeze sat in a JSON file anyone could
edit afterwards. Nothing compared the two.

**The fix.** `build_manifest` takes the sign-off and refuses without one — Module B does
not manufacture approval. The manifest is completed **before** serialisation, embedded
in the artifact, and the sidecar is written from the same dict. It carries its own
digest. `load_frozen` refuses: a missing or blank sign-off, a manifest that fails its
own digest, an embedded/sidecar mismatch, a missing sidecar, and a `REHEARSAL` artifact
presented as production.

**Rehearsal.** Stage 10 freezes with the placeholder sign-off
`"REHEARSAL — not a production sign-off"`, stamped `release_state="REHEARSAL"`, into a
**temporary directory** that is deleted at the end of the stage. The placeholder cannot
sign a production freeze: `build_manifest` rejects that combination explicitly. No fake
production sign-off exists anywhere in this package.

---

### P0-B3 · Recorded decisions were prose, and prose does not stop a freeze — **CLOSED**

**The fix.** `moduleb/decisions.py` gives each release decision a predicate that reads
the live implementation, not a copy of the decision:

| | Decision | Predicate reads |
|---|---|---|
| D1 | no Module B disposition | the contract column list and `FORBIDDEN_OUTPUT_COLS` |
| D10 | `Output_Fall_Time` stays `own+lot+cross` | `config.RECOMMENDED` |
| D11 | the relative-delta cap is OFF | `config.FORECAST_REL_DELTA_CAP is None` |
| D12 | cohort serving contract, completeness proved | `serving.REQUIRES_COMPLETENESS_PROOF`, `PARTIAL_LOT_DEFAULT`, `MIN_LOT_COHORT` |
| D13 | tail ranked by true relative drift | a live call to `envelope.coverage_report` |
| D14 | corrected holdout provenance, one-shot unspent | `holdout_manifest.PROVENANCE` |

`freeze.freeze` runs the set as a preflight and raises; stage 11 prints each one and
refuses. **Mandatory negative test:** `test_a_non_none_cap_fails_the_freeze_preflight`
sets the cap to 0.5, asserts D11 fails, asserts the freeze raises, and asserts no
artifact was written. D1 and D10 have equivalent negative tests.

---

### P0-B4 · One digest was covering two different questions — **CLOSED**

`frozen_config_digest()` answers "is this the same fitted model?". It could not answer
"does this still behave the same way?", so a change to lot completeness, the output
contract, the evidence thresholds, the static-limit policy or the clipping semantics
was invisible to a consumer holding it.

`serving.runtime_contract_digest()` now covers exactly that surface — serving-contract
version, completeness policy, partial-lot default and override semantics, input
contract, output contract, envelope τ, reason-code runtime thresholds, static-limit
policy, clipping and fallback semantics, `emits_disposition`. The manifest carries both,
plus `source_tree_digest()` for the code neither covers. `load_frozen` and stage 12
validate both.

**Tests.** A runtime-only change moves the runtime digest and leaves the model digest
alone; a model-only change does the reverse; a stale artifact is refused at load in
both directions.

---

## P1 — governance and provenance

### P1-G1 · "The holdout was never opened" — **CLOSED, and the claim withdrawn**

The sentence was not accurate. The corrected history is recorded in
`moduleb/holdout_manifest.py` and as decision **D14**:

- the **predictor-only** holdout file *was* read before the freeze, for structural and
  schema checks — stage 0 loaded it, stage 1 tabulated its shape, stage 10 read its
  header, stage 14 re-derived its lot count;
- the file carries **no 168 h targets**, and the hidden truth has never been available
  to Module B;
- **no holdout forecast was generated**;
- **no holdout score was observed**;
- **no model or configuration decision used a holdout outcome**;
- the one-shot predictive evaluation is therefore **UNSPENT**.

The history is preserved rather than rewritten. Going forward, the pre-freeze stages
read the **declared** structure — row count, lot count, header, delivery SHA-256 — from
`moduleb/holdout_manifest.py`, and `scripts/12_predict_holdout.py` is the only stage
permitted to read the contents. `tests/test_release_gates.py` fails if any other stage
does.

Hashing the file is still allowed everywhere. A SHA-256 reads bytes, not measurements,
and it is what proves the delivery is the one the manifest describes.

One check genuinely moved rather than being dropped: the train/holdout and
calibration/holdout lot-disjointness tests used to compare two files in stage 1. They
now run in **stage 12**, against the frozen artifact's own recorded `train_lots`. That
is a stronger statement — the artifact, not a second file, is the thing that must not
have seen those lots.

---

## P2 — documentation and executable claims

All nine were found **in code as often as in prose**. A withdrawn claim printed by a
runner script is still a claim the project makes.

| # | Withdrawn claim | Where it still lived | Now |
|---|---|---|---|
| 1 | Pearson *r* is a "ceiling" on same-parameter predictability | `scripts/02_drift_structure.py`, `notebooks/N1_audit.ipynb` | described as a **linear** diagnostic; a low *r* does not rule out nonlinear or multivariate routes |
| 2 | Reason-code sparsity proves "actionability" | `scripts/08_reason_code_audit.py` | passes the **pre-declared sparsity gate**; sparsity limits alert flooding and establishes neither precision nor recall |
| 3 | Enabling the cap "is not a retune" | `scripts/07_extrapolation_risk.py` | the coefficients are untouched, but enabling it is a model/pipeline behaviour change with its own digest |
| 4 | The holdout was "never opened" | `scripts/10`, `docs/CHATGPT_REVIEW_PROMPT.md` | replaced by the D14 provenance statement |
| 5 | "53 checks" / "53 load-bearing figures" | `docs/COMPLETE_GUIDE.md` §8 | the count is no longer written in prose; stage 14 prints it and `RELEASE_MANIFEST.json` records it |
| 6 | Arbitrary batch size gives equivalent predictions | already corrected in round 1; re-scanned across code | absent outside correction notes |
| 7 | Finite-sample conformal validity is guaranteed | `moduleb/envelope.py` docstrings | the `(n+1)` rank is the construction; coverage here is **measured**, not derived — exchangeability across whole lots is not established |
| 8 | "one forecast in 5,400" | already corrected in round 1; re-scanned across code | absent outside correction notes |
| 9 | The validation protocol is "sound" | already corrected in round 1; re-scanned across code | absent outside correction notes |

**Checker extended.** Stage 14 now scans `README.md`, every current doc, every runner
script, every notebook, the package source and `RELEASE_MANIFEST.json`. The
"never asserted" rule is unchanged — a withdrawn phrase may survive only within 400
characters of a correction marker — so provenance is kept without the claim being made.
The checker excludes its own source, which necessarily quotes every withdrawn phrase.

---

## S1–S8 — secondary technical claim audit

| | Claim examined | Disposition |
|---|---|---|
| **S1** | "1.075× median-ratio — **a tie**" | **CORRECTED.** 1.075× is a **7.5 % MAE deficit**, outside the pre-declared 5 % tie band in either direction. The tie rule (`metrics.verdict`) calls a result a tie when the effect is under 5 % **or** the per-lot paired test misses α = 0.05 — and no paired test was run for the row-removed variant, so no verdict is claimed for it. The row removal shows where the error is concentrated, not a different verdict. |
| **S2** | D10 threshold: `≥ 4 of 6` translated as "more than half" | **AMBIGUITY RECORDED.** `≥ 4 of 6` is two-thirds; onto 12 lots that is `≥ 8`, while "more than half" gives `≥ 7`. The looser reading was used. Observed **2 of 12** fails `≥ 4`, `≥ 7` and `≥ 8`, so D10's outcome is unchanged under every reading and no interpretation was chosen after seeing the result. |
| **S3** | "MAE optimises the conditional median" | **CORRECTED.** The deployed models are **Huber** regressors. The objective down-weights large residuals rather than chasing the mean; that is an empirically robust fit, not an estimator of the conditional median. |
| **S4** | Error above the noise floor ⇒ "real predictable drift still being missed" | **CORRECTED.** The 3.1×–6.1× ratio bounds how much of the error the *assumed measurement noise* can explain. It does not establish that the remainder is recoverable from the 0 h/24 h features Module B may use. |
| **S5** | "42 lots cannot resolve smaller effects" | **CORRECTED.** 5 % is a **pre-declared practical threshold** agreed before results were seen, paired with a per-lot significance test. No formal power or resolution analysis was run, and none is claimed. |
| **S6** | "The robust loss is doing real work, exactly as predicted" | **CORRECTED.** The result is **consistent with** robust loss being beneficial here; the grid varies loss and structure together and does not isolate the loss causally. |
| **S7** | "a learned forecaster for four and a scaling rule for two" | **CORRECTED.** All six deployed point models are Huber regressors. Module B **materially beats median-ratio on four parameters and ties it on two under the 5 % rule**; what differs between them is whether the fitted model beats a per-variant constant, not which model is deployed. |
| **S8** | Domain/physical claims and their VERIFIED / CALIBRATED / ASSUMED labels | **VERIFIED — no change required.** The labels are visible in `docs/COMPLETE_GUIDE.md` §4 and §16, the measurement-noise CVs are labelled `ASSUMED` at every point of use, and no external standard is cited as authority for any threshold. Carried into Tanisha's packet for domain review. |

---

## Rejected in this round

Nothing in the round-2 brief was rejected as wrong. Three things were deliberately
**not** done, each because doing them would have broken a contract rule:

- **No re-run of the 24-configuration grid or any model selection.** `features.py`,
  `featureset.py`, `models.py`, `cv.py` and the frozen settings are unchanged, so the
  grid's dependencies are unchanged and re-running it would only add compute and a
  second copy of the same numbers.
- **No fix for the `Input_Leakage_Current` calibration regression.** Every available fix
  is tuned on the calibration outcome. It stays a recorded limitation; the cap stays off
  (D11); the idea is parked in `docs/FUTURE_RELEASE_ITEMS.md`.
- **No production freeze, no holdout run, no Sanskruti scoring packet.** The furthest
  this pass may advance is `READY_FOR_TEAM_SIGNOFF`, and sign-off is a human act.

---

## Verification after the round

Recorded in `RELEASE_MANIFEST.json` under `verification`, produced by the run that
wrote it: the full unit-test suite and the claim checker, both green, plus the
white-box, clean-room, owner-handoff and team-distribution audits described in
`docs/FINAL_FREEZE_READINESS.md`.
