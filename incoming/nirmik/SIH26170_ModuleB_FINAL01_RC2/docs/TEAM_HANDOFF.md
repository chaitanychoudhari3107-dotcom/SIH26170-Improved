# Module B — team handoff

`ModuleB-FINAL01-RC2` · dataset `SIH26170-FINAL-01` · owner **Nirmik** · 19 Sep 2026
State: **HOLDOUT_PREDICTION_DELIVERED**. Frozen 20 Sep 2026 on a recorded team sign-off;
the one-shot holdout run is spent. Sign-off on record:
`Team sign-off 2026-09-20 — confirmed by Nirmik, Module B owner, on behalf of the team`.

One section per member. Each says what you get, why you get it, when you use it, what
you must **not** get or use, and your exact next action. The authoritative role
boundaries are the team's own `SIH26170_FINAL_File_Distribution_Guide.docx`; this
document applies them to Module B and does not extend them.

**Rules that hold for everyone, inherited from the distribution guide:**

- Everyone uses `SIH26170-FINAL-01`. The old 297-component mock and Candidate V1 are
  not sources of current results.
- The final parameter name is `Active_Supply_Current`. `Supply_Current_ICC` must not
  appear in new code.
- Module A and Module B outputs join on **`component_id`**, never on row number.
  Component IDs are identifiers, not chronological order.
- Hidden truth and hidden 168 h targets stay with Sanskruti and Chaitany. Nobody else
  opens them before evaluation.
- The dataset is not regenerated because a score disappoints. Only a real correctness
  bug justifies it.
- Operational or live data must never automatically retrain or modify the frozen
  benchmark dataset.

---

## 1 · Chaitany — master / custodian

**You receive:** `SIH26170_FINAL_Chaitany_ModuleB_Custody_Packet.zip` — the Module B
release-candidate archive, `RELEASE_MANIFEST.json`, `SHA256SUMS.txt`, the environment
snapshot, `docs/RELEASE_CHANGELOG.md`, `docs/FINAL_FREEZE_READINESS.md`, the decision
state, and re-verification instructions.

**Why:** you hold version custody and recovery for the project. Module B's release is
identified by four digests — model config, runtime contract, source tree, release
manifest — and this packet is what lets you prove months from now which code and which
input files produced a given result.

**When:** archive on receipt, after the six-artifact audit. Re-verify whenever anyone
claims a Module B number.

**You must not receive or be asked for:** Sanskruti's hidden ground truth or the hidden
168 h targets **from Module B** — Module B has never held them and must never import
them. You are also not asked to regenerate `SIH26170-FINAL-01`. Module B's calibration
result on `Input_Leakage_Current` is a recorded limitation, not a data bug; the
distinction is written out in `docs/DATA_BUG_VS_MODEL_PROBLEM.md`.

**Your next action:** archive the packet, verify `SHA256SUMS.txt` against the files,
and record `ModuleB-FINAL01-RC2` against the frozen dataset version.

---

## 2 · Riddhi — Module A

**You receive:** `SIH26170_FINAL_Riddhi_ModuleB_Interface_Packet.zip` — the
`component_id` join rule, the exact Module B output contract, parameter naming, a short
summary of what the `B_` evidence codes mean, and the release identity and digests.

**Why:** so that Module A and Module B outputs join cleanly and nobody discovers a
naming or key mismatch during integration. That is the entire overlap between our
modules.

**When:** before the final A/B compatibility and integration checks.

**You must not receive or be asked for:** Module B's training package, evaluator data,
or any instruction that changes Module A's thresholds, model or holdout process.
**You own Module A.** Module B emits no disposition of any kind — no PASS, no MONITOR,
no REJECT, not even as `NOT_SET` (decision D1) — so nothing in this packet competes
with `module_a_disposition`.

**Your next action:** confirm your output uses `component_id` as the join key and that
your column names match `ModuleA_Output_Contract.csv`, then tell Anushka both contracts
are stable.

---

## 3 · Nirmik — Module B owner

**You receive:** `SIH26170_FINAL_Nirmik_ModuleB_Release_Packet.zip` — the complete
verified release candidate: source, tests, scripts, notebooks, permitted data and
reference files, `results/`, `RELEASE_MANIFEST.json`, checksums, environment snapshot,
runtime contract, decision state, `docs/FINAL_FREEZE_READINESS.md`,
`docs/ROUND2_FINAL_ADJUDICATION.md`, `docs/TEAM_HANDOFF.md`,
`docs/RELEASE_CHANGELOG.md`, `docs/COMPLETE_GUIDE.md`, `docs/FUTURE_RELEASE_ITEMS.md`,
and the exact freeze and holdout commands.

**Why:** you own Module B — the six 168 h point forecasts, the six forecast-risk
envelopes, `module_b_primary_parameter`, the `B_` evidence codes, the release and
runtime contract, and the technical documentation.

**When:** now, and it stays with you. It is the authoritative copy.

**You must not add:** hidden evaluator targets, another member's private package, a
fabricated sign-off, a frozen artifact produced without genuine approval, or a holdout
prediction produced before the legitimate post-freeze run.

**Done, 20 Sep 2026:** sign-off recorded → stage 11 freeze → stage 12 one-shot run.
`models/module_b_final01.joblib`, `models/FREEZE_RECEIPT.json`,
`results/ModuleB_Final_Holdout_Predictions.csv` and
`results/HOLDOUT_PREDICTION_RECEIPT.json` all exist.

**Your next action, in order:**

1. Send the prediction file **and** its receipt to Sanskruti for blind scoring.
2. Send `models/FREEZE_RECEIPT.json` to Chaitany for the archive.
3. Send the prediction file to Anushka **only if** final fusion needs it.
4. Change nothing in response to the scores. The one-shot is spent, and any change from
   here is a different model that cannot be evaluated on this holdout.

---

## 4 · Anushka — integration, fusion, dashboard

**You receive:** `SIH26170_FINAL_Anushka_ModuleB_Integration_Packet.zip` — the final
`ModuleB_Output_Contract`, the input/request contract, the complete-lot serving
semantics and the expected-lot metadata requirement, the runtime-contract version and
digest, the `component_id` join rule, reason-code and primary-parameter semantics, the
p95 envelope's limitation, missing-static-limit behaviour, the partial-lot override and
why normal integration should never use it, fail-closed behaviour, a safe schema
example, and `docs/INTEGRATION_NOTE.md`.

**Why:** you should be able to integrate Module B without reading its internals or
knowing how it was calibrated.

**When:** before final fusion and dashboard wiring.

**The three things that will bite if they are missed:**

1. **Requests carry whole, complete lots.** Module B refuses a lot it cannot prove is
   complete — supply `expected_lot_sizes` from your request metadata, or the delivery
   attestation. A row count is not a proof, and a partial lot changes the timing
   forecasts and every evidence column.
2. **The p95 envelope is evidence, never a screen.** Marginal coverage is calibrated;
   coverage on the worst-drifting decile is 0.407–0.769. Do not turn it into a pass/fail
   rule or describe it as a safety guarantee.
3. **Module B emits no disposition.** The final PASS / MONITOR / REJECT is yours,
   from Module A plus fusion.

**You must not receive or be asked for:** hidden targets, evaluator truth, or
responsibility for Module B's model selection, calibration or tuning. Fusion policy
stays yours; the only thing Module B asks of it is that the limitations above are not
reinterpreted as guarantees.

**Your next action:** wire the contract and the request metadata, confirm the join is on
`component_id`, and run your integration against the real prediction file — it exists as
of 20 Sep 2026 and comes with a receipt whose digests must match the ones in your
packet's `RELEASE_IDENTITY.json`.

---

## 5 · Tanisha — domain and standards validation

**You receive:** `SIH26170_FINAL_Tanisha_ModuleB_Domain_Validation_Packet.zip` —
`Device_Specs.csv`, the schema/data dictionary, parameter definitions and units,
reference-device mappings, the source-backed static limits, the explicit list of the
**seven** variant × parameter cells with no limit, the VERIFIED / CALIBRATED / ASSUMED
labels, and the physical and domain claims Module B's documentation makes.

**Why:** these are the statements that need someone who knows the domain to say
"that sentence is wrong" before they reach judges.

**When:** before the presentation and report wording is locked.

**What we specifically want checked:** that no assumption reads as an established
physical guarantee; that the measurement-noise CVs are described as the team's
assumptions everywhere they are used; that no threshold in the package is attributed to
NASA, ISRO, MIL-STD or any other standard, because none is; and that the sub-linear
drift description (`t^0.58`–`t^0.80` on FINAL-01) is stated as measured-on-this-dataset
rather than as physical law.

**You must not receive or be asked for:** hidden evaluator truth, model training files,
ML model-selection work, or any request to tune Module B. You validate wording and
domain facts, not the ML release.

**Your next action:** return a short list of any domain or specification wording that is
factually wrong or misleading, with the file and line.

---

## 6 · Sanskruti — evaluation

**You receive now:** `SIH26170_FINAL_Sanskruti_ModuleB_Evaluation_Handoff_Packet.zip` —
the Module B output contract, the `component_id` scoring/join key, the release identity
and digests, the expected prediction-file name and schema, the freeze and prediction
receipt schemas, and the provenance information needed to confirm which release produced
a prediction.

**You receive now, as of 20 Sep 2026:** the actual
`ModuleB_Final_Holdout_Predictions.csv` (1,343 rows, 18 lots) and
`HOLDOUT_PREDICTION_RECEIPT.json`. Sign-off was recorded, stage 11 froze the model and
stage 12 ran exactly once. Check the receipt's digests against `RELEASE_IDENTITY.json`
before you score: if they differ, the file came from a different build.

**Why:** so that when the prediction file arrives you can verify it came from the
release you were told about, and score it without asking Module B anything.

**When:** the handoff packet after the six-artifact audit; the prediction file and its
receipt are being sent now, after the freeze.

**What stays yours and must never come back to Module B:**
`EVALUATOR_ONLY/Hidden_Ground_Truth.csv` and
`EVALUATOR_ONLY/ModuleB_Holdout_168h_Targets.csv`. Module B has never held them, does
not want them, and the corrected access history for the predictor-only holdout file is
recorded as decision D14 in `moduleb/holdout_manifest.py`. Do not send scores,
partial scores or hints before the freeze, and do not send the targets at any point.

**Your next action:** verify the receipt's digests against `RELEASE_IDENTITY.json`, then
score the predictions against your hidden targets. The one-shot has been spent, so if a
field you need is missing, it cannot be added for this evaluation — say so anyway, and
it is recorded for the next release.

---

## What is NOT in any of these packets

- No hidden ground truth and no hidden 168 h targets, in any direction.
- No other member's private working package.
- No frozen production artifact **inside the distributed packets** — it lives with
  Nirmik; its hash travels in the receipts instead.
- No hidden 168 h targets, in any packet, in any direction.
- No score. Scoring is Sanskruti's, after she receives the prediction file.
- No Module B disposition column.
- No Candidate V1 or mock result presented as a current FINAL-01 number.
