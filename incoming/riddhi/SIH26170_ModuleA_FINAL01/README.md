# Module A — observed-anomaly detection on SIH26170-FINAL-01

**Owner:** Nirmik · **Dataset:** `SIH26170-FINAL-01` ·
**Model:** `ModuleA-FINAL01-RC1` · **Package:** `final01.2.0` ·
**Status:** frozen 22 Sep 2026; the one-shot holdout run is **spent**.
`models/module_a_final01.joblib` exists, `results/ModuleA_Final_Holdout_*.csv` and the
prediction receipt exist. **Nothing here may be retuned in response to the scores.**

Module A asks whether a component **already looks abnormal**, against its variant's
normal references and against the other components in its own lot. It emits a score,
a disposition of PASS or MONITOR, and its evidence. Module B forecasts; fusion decides.

---

## Where things are

```
modulea/     the package — 13 small modules, none over 200 lines
scripts/     thin numbered runners. All the logic is in modulea/
tests/       38 tests. Run them before trusting any number
docs/        MASTER_PROMPT first, then model card, validation summary,
             decision log, limitations, integration note, runbook
results/     everything the scripts produce - regenerable, safe to delete
prediction/  the spent one-shot holdout outputs and their receipt. NOT regenerable;
             kept out of results/ so clearing that directory cannot destroy them
models/      the frozen artifact and its receipt
packets/     the six role-scoped team packets, built by stage 18
state/       the checkpoint that lets an interrupted session resume
```

`scripts/_evaluator.py` is the only file in the release that can open
`hidden/Hidden_Ground_Truth.csv`. Nothing in `modulea/` imports it.

## Quick start

```bash
pip install -r requirements.txt
export SIH26170_RELEASE=/path/to/SIH26170_FINAL_RELEASE_01
python run_all.py --release $SIH26170_RELEASE            # stages 0-6, nothing gated
```

Full sequence, and which stages are gated: **`docs/RUNBOOK.md`**.

## The stages

| | script | what it decides | state |
|---|---|---|---|
| 0 | `00_selfcheck.py` | are the code and inputs what we think they are | ✅ |
| 1 | `01_audit.py` | data bug, or a modelling problem to live with | ✅ clean |
| 2 | `02_spec_witness.py` | how good is the one non-statistical witness | ✅ 0 FP in 5,076 normals |
| 3 | `03_threshold_curve.py` | recall against review workload; the thresholds | ✅ |
| 4 | `04_nested_validation.py` | what does the whole procedure score out of sample | ✅ 48/54 at 25 FP |
| 5 | `05_blindspot_report.py` | what this detector cannot see, named precisely | ✅ |
| 6 | `06_dryrun.py` | rehearse freeze and serving on a stand-in | ✅ |
| 7 | `07_freeze.py` | **GATED** — freeze the model | ✅ 22 Sep 2026 |
| 8 | `08_predict_holdout.py` | **GATED** — the one-shot holdout run | ✅ **spent** |
| 9 | `09_evaluate_holdout.py` | open the labels, against predictions already hashed | ✅ diagnostic |
| 10 | `10_verify_claims.py` | do the docs and the code match `results/` | ✅ 18 of 18 |
| 11 | `11_release_manifest.py` | write the manifest and checksums | ✅ |
| 12 | `12_robustness.py` | what happens when the input is perturbed | ✅ 19 cases, 0 failures |
| 13 | `13_score_semantics.py` | what the score means, and what it is not | ✅ monotone, not a probability |
| 14 | `14_sensitivity.py` | where it does badly; does B corroboration mean anything | ✅ |
| 15 | `15_fusion_dryrun.py` | actually join to Module B and prove it | ✅ 1,343 rows, 9 checks |
| 17 | `17_provenance.py` | what moved after the freeze, and did it matter | ✅ no build mismatch |
| 18 | `18_build_packets.py` | the serving example and the teammate packets | ✅ |
| 19 | `19_reproducibility_check.py` | do two independent runs agree | ✅ 44 of 44 |
| 20 | `20_confusion_matrix.py` | all four cells, every result, cross-checked | ✅ 10 matrices balance |

## The result in eight lines

- **The CONFIRMED tier has raised no false positive on any of the 5,400 components in
  this release** — 81 flags, 81 real anomalies, 0 normals. It fires when a measured
  value exceeds its own datasheet `static_spec_max`, so it is not a fitted threshold.
  Zero observed errors in 5,076 normals is not a zero rate: the 95% upper bound is
  **0.06%**, and that is how the claim is written everywhere here.
- **The statistical tier is not zero-false-positive and cannot be made so** at useful
  recall. It operates at a 1% calibration false-alarm budget, chosen at the curve's
  knee: moving to 3% buys one more anomaly of 54 and costs sixteen more false alarms.
- **Honest nested estimate: 45 of 54 anomalies at 9 false alarms** (recall 83.3%,
  FPR 1.06%), with the weights *and* the threshold selected inside each of 12
  leave-one-lot-out folds, at the budget the release ships at. The before-state gives
  44 of 54 at 7 under the same protocol — a gain of one anomaly for two false alarms,
  and it is stated as small. No previous Module A candidate reported a number with the
  selection inside the fold at all.
- **No fold, at either budget, chose the inherited `overall_extreme` component** — 24
  fold-selections, zero. That is why it is dropped. At the shipped budget the folds
  split 6/6 between the two survivors, so the release ships the simpler one. PR AUC
  against the inherited weights is +0.0008, 95% CI [−0.0081, +0.0171]: a tie, written
  as one.
- **On the holdout the weight change did not transfer**: PR AUC 0.8166 against the
  inherited 0.8239, and 1–2 fewer true positives at matched workload. Within noise,
  predicted by the calibration tie, and **not** grounds to reopen the freeze. Reported
  in `docs/VALIDATION_SUMMARY.md` at the same volume as everything else.
- **168 h holdout, frozen configuration: 65 TP, 13 FP, 25 FN** across 1,343 components
  — 78 flagged, of which 23 are CONFIRMED with zero normals among them.
- **The blind spot is named precisely.** Not "static outliers" but *static offsets that
  stay inside specification*: caught 6 of 21 across both splits, against 7 of 7 for
  those that fail spec. Nine statistics from five families all land in the same place,
  so it is a ceiling of within-lot statistics, not a deficiency of this candidate.
- **The calibration split cannot be used to tune for that blind spot**, because it
  contains four of those cases against the holdout's seventeen. That is a dataset
  finding for whoever owns the generator, not another modelling round.

## Before integration

The pre-integration hardening pass (`docs/MASTER_PROMPT_DEPLOYMENT.md`) added the
verification an integrator needs and changed nothing the model computes — `config_digest`
and `runtime_contract_digest` are identical to the first freeze, and the four frozen
holdout prediction files are byte-identical.

- **19 perturbation cases**: six invariances hold exactly (row order, reversal, column
  order, non-monotonic index, lot interleaving, an unexpected extra column), eleven
  malformed inputs are refused, two sensitivities measured, one semantic documented.
- **The score's meaning is measured.** Monotone in the observed anomaly rate; **not** a
  probability — the largest gap between a band midpoint and its observed rate is 0.75.
- **The join to Module B is done, not described.** 1,343 rows against
  `ModuleB-FINAL01-RC2`'s real frozen packet, nine checks, all passing.
- **One latent serving failure found and fixed.** A statistical rank of exactly 1.0
  mapped onto the out-of-specification floor, which would have made the contract
  validator refuse the frame — turning the top-ranked component of any batch into a
  crash. Eight holdout components sit at that rank and escaped only because all eight are
  also datasheet violations. Predictions byte-identical after the fix.
- **A measured weakness worth stating**: a global unit error is invisible to the
  statistical score, because a lot-relative robust z is scale-free. Unit validation
  belongs upstream of Module A.
- **An interrupted session resumes from a file.** `state/CHECKPOINT.json` plus
  `CONTINUATION.md`; no conversation history required.

Verification: **79 tests, 151 claim checks**, both recorded in `RELEASE_MANIFEST.json`,
plus **two independent runs agreeing byte-for-byte on 44 of 44 analysis outputs**.

The two-run protocol is `docs/MASTER_PROMPT_FINAL_VERIFICATION.md`. Analysis
(`scripts/run_canonical.sh`) is what gets compared; release (`scripts/release.sh`) runs
once afterwards and builds the six team packets. They are separate because the packets
embed the reproducibility verdict, so a run that built them could never be compared.

## The four outcomes, in full

Every headline in this release is a view of four integers, so all four are reported for
every result in `results/20_confusion_matrices.csv`, cross-checked against
`sklearn.metrics.confusion_matrix` on every run. `docs/MASTER_PROMPT_CONFUSION_MATRIX.md`
sets the rules; the two that matter:

| result | TP | TN | FP | FN | recall | precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|
| calibration, out of fold, shipped config | 47 | 844 | 8 | 7 | 87.0% | 85.5% | 0.94% |
| holdout 168 h, frozen release — DIAGNOSTIC | 65 | 1,240 | 13 | 25 | 72.2% | 83.3% | 1.04% |

**FN is the expensive cell** — 25 real defects passed onward. FP costs review time only.
The datasheet-limit rule across all 5,400 components: 81 TP, 5,076 TN, **0 FP**, 243 FN.
Its 243 false negatives are why it certifies rather than detects, and they are reported
wherever its perfect precision is.

Accuracy is deliberately absent: with 90 anomalies in 1,343 components, flagging nothing
scores 93.3%.

## Rules the code enforces, not the reader

- A model scoring at epoch *e* cannot read a column later than *e* — the columns are
  dropped before scoring, and a test poisons a 168 h column with 1e6 and asserts a
  24 h score is unchanged.
- One threshold on `module_a_score` reproduces `module_a_disposition` exactly. A frame
  where it does not is refused before it can leave.
- Module A cannot emit REJECT. The contract validator raises.
- A batch is scored only when every lot in it is proved complete against external lot
  metadata. A count taken from the batch itself is not a proof.
- A feature whose reference MAD is zero falls down a declared ladder and raises if
  every rung fails. It is never silently scored as normal.
- A component with zero weight is never named as the reason a flag was raised.
- No static limit is invented. The seven empty `Device_Specs` cells stay empty.
- The hidden labels have exactly one door, and no fitting path imports it.
- A freeze without a real recorded sign-off is refused, and the sign-off is embedded in
  the artifact before the bytes are written.
- Predictions are hashed when written; the evaluator refuses to score a file that
  changed afterwards.
