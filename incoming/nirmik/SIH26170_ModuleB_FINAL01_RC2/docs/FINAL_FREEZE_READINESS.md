# Final freeze readiness

`ModuleB-FINAL01-RC2` · dataset `SIH26170-FINAL-01` · 19 September 2026 · owner Nirmik

**RELEASE_STATE: `HOLDOUT_PREDICTION_DELIVERED`** *(updated 20 Sep 2026)*

## 0 · Outcome — the gate opened and was used

The team signed off on **20 September 2026**, and the two gated stages ran in order,
each exactly once.

| | |
|---|---|
| Sign-off recorded | `Team sign-off 2026-09-20 — confirmed by Nirmik, Module B owner, on behalf of the team` |
| Frozen at | `2026-09-20T13:05:53+00:00` |
| Frozen artifact | `models/module_b_final01.joblib` · SHA-256 `6896b6273df915cb3dab58f8cb51b3a7…` |
| Freeze receipt | `models/FREEZE_RECEIPT.json` |
| Fitted on | 4,057 rows / 54 lots (train + calibration) |
| One-shot run | **spent** — stage 12, once |
| Prediction output | `results/ModuleB_Final_Holdout_Predictions.csv` · 1,343 rows / 18 lots · SHA-256 `d80d05653f9d0b5bc1256aa6c10c2501…` |
| Prediction receipt | `results/HOLDOUT_PREDICTION_RECEIPT.json` |
| Components carrying a `B_` code | 186 of 1,343 (13.85 %) |
| Completeness proof used | `delivery_attestation`, hash-verified against the declared delivery |
| Clipping | one `Output_Fall_Time` envelope raised to its point forecast — reported in the run and recorded in the receipt, never silent |
| Blindness | the 18 holdout lots are disjoint from all 54 lots the artifact was fitted on, asserted at run time against the artifact's own manifest |

**Nothing in this package may now be retuned in response to a score.** Any change from
here is a different model with a different digest, and it cannot be evaluated on this
holdout.

The sections below are the pre-freeze gate report, unchanged. They are what the freeze
was authorised on.

---

## 1 · Gate status

| Gate | Result |
|---|---|
| P0-B1 complete-lot serving contract | **CLOSED** |
| P0-B2 sign-off inside the frozen artifact | **CLOSED** |
| P0-B3 release decisions machine-enforced | **CLOSED** |
| P0-B4 runtime contract digest | **CLOSED** |
| P1-G1 corrected holdout provenance | **CLOSED** |
| P2 documentation / executable claims | **CLOSED** |
| S1–S8 secondary technical audit | **COMPLETE** — seven corrections, one verified unchanged |
| Full test suite | **PASS** — 101 passed, 0 failed |
| Claim checker | **PASS** — 197 / 197 |
| `WHITE_BOX_RECHECK` | **PASS** |
| `CLEAN_ROOM_RECHECK` | **PASS** |
| `OWNER_HANDOFF_CHECK` | **PASS** |
| `TEAM_DISTRIBUTION_AUDIT` | **PASS** |
| `CORE_RELEASE_ZIP_VERIFICATION` | **PASS** |
| Holdout prediction | **UNSPENT** |
| Team sign-off | **PENDING** |

Counts and digests are recorded by the run itself in `RELEASE_MANIFEST.json`; if a
number here and a number there ever disagree, the manifest is the one produced by the
code and this document is the stale one.

## 2 · Identity

| | |
|---|---|
| Release candidate | `ModuleB-FINAL01-RC2` (`moduleb.__version__ = final01.2.0`) |
| Dataset | `SIH26170-FINAL-01` · `v4-final1` · split `LOTSPLIT-05` · 5,400 rows / 72 lots |
| Model config digest | `8d0621941f86fbb8…` — **unchanged since 18 Sep**; no fitted parameter moved in round 1 or round 2 |
| Runtime contract digest | `d19cec26170eb725…` — new in RC2; it did not exist before |
| Source tree digest | `565a567fa0c8c44c…` |
| Serving contract | `mb-serving-2.0` |

Three digests because they answer three different questions: *is this the same fitted
model*, *does it still behave the same way to a caller*, and *is this the same code*.
One digest could not answer the second, which is what P0-B4 was about.

## 3 · What the rechecks actually did

**White-box (Recheck 1).** Thirty-six adversarial probes against the working tree,
written as though by someone who had not made the changes: refusing a request with no
proof, with an empty proof, with a proof for other lots, with a lot short by **one** of
82, and with a short lot padded back to its expected count by a duplicated
`component_id`; an attestation whose hash does not match; the override's recorded
contents; a stray `*_96h` column, a hidden-label column and a missing predictor;
contract ordering and the absence of any disposition column; the D11 enforcement; the
separation of the two digests; the holdout isolation; and the F3 tail-definition
regression. All passed.

**Clean-room (Recheck 2).** The release ZIP was extracted to a fresh directory and
everything below was run **only** from that copy: internal checksums against
`SHA256SUMS.txt`, package import, the full test suite, the claim checker, the manifest
digests against the live code, and the absence of a frozen model, a holdout prediction
output, a receipt, a rehearsal artifact, a cache, an evaluator-truth file, another
member's package or an absolute path baked into the code.

This recheck found a real defect on its first run: the packaging script excluded paths
by substring, and the string `models` — meant to keep the frozen-artifact directory out
of the ZIP — also matched `moduleb/models.py`, so the shipped package was missing a
module and failed to import. The exclusion now matches whole path segments, a comment
in `scripts/16_package_release.py` records why, and both rechecks were re-run from the
start afterwards. This is the argument for the clean-room step: the working tree
imported perfectly the entire time.

**Owner handoff.** Against the extracted copy, each of the eleven questions in the
handoff list was answered from the package alone, including the exact freeze command,
the exact one-shot holdout command, and exactly which file Sanskruti receives. Every
current-release document was scanned for unresolved markers. Two real stale items were
found and fixed: `VALIDATION_SUMMARY.md` still said the relative-delta cap "must be
decided before the freeze" (and so did its generator, so a rerun would have
reintroduced it) although D11 closed on 19 Sep, and `COMPLETE_GUIDE.md`'s subtitle still
carried the old promise to say what remained unresolved. The two dated review artifacts now carry banners
saying they are records rather than current state.

**Team distribution.** Every handoff was checked against the team's own distribution
guide: six role sections in order, each stating what is received, what must not be, and
the next action; no evaluator truth in any direction; Module A ownership left with
Riddhi and Module B freeze ownership left with Nirmik; Tanisha not asked to do model
selection; Anushka consuming the interface rather than the internals; Chaitany not
asked to regenerate; `component_id` as the only join key; no obsolete parameter name;
and no Candidate V1 or mock figure presented as a current FINAL-01 result.

## 4 · What did NOT change

The fitted model. No coefficient, hyper-parameter, feature set or envelope offset
moved in this round, and the 24-configuration grid was not re-run because none of its
dependencies changed. Every figure in `results/` is still from the recorded run of
18 September 2026.

## 5 · Known limitations carried into the freeze

These travel with the release. They are measured, not hedges, and every one of them is
settled — a limitation the release carries, not a question waiting on an answer.

1. `Input_Leakage_Current` is about **33 % worse** than the median-ratio baseline on the
   twelve calibration lots — acceptance criterion **M5, FAIL**. 27.7 % of that error sits
   on one component of 906. D11 closed with the cap **off**: every candidate bound was
   post-hoc on calibration, and the motivating case is a true positive with an
   exaggerated magnitude.
2. `IDDQ` and `Active_Supply_Current` **tie** a single per-variant constant under the
   pre-declared 5 % rule. Module B beats the baseline on four of six parameters, not six.
3. The p95 envelope is **evidence, never a screen**. Marginal coverage 0.933–0.974;
   coverage on the worst-drifting decile 0.407–0.769, measured and reported.
4. Conformal coverage here is **measured, not derived** — no cluster-conformal result
   has been produced for whole-lot units with this score construction.
5. Timing forecasts and every evidence column are **cohort statistics**. This is why a
   lot must be proved complete, and why the partial-lot override is recorded as degraded.
6. Seven of eighteen variant × parameter cells have **no static limit**, so the
   limit-based codes never fire there. None is invented.
7. The measurement-noise CVs are the team's **stated assumptions**, and everything
   derived from them inherits that status.
8. FINAL-01 is **synthetic**; realism claims are about the generator, not silicon.
9. Module B has **no correctness label** for its own `B_` codes: sparsity is measured,
   precision and recall are not.

The full list also lives in `RELEASE_MANIFEST.json` under `known_limitations`, so a
consumer reads it from the artifact rather than from a document.

## 6 · Exactly what happens next

Nothing further is required from Nirmik before sign-off. There is no remaining
engineering step.

1. The team reviews this release candidate.
2. **Genuine** team sign-off.
3. `python scripts/11_freeze.py --team-signoff "<who approved, and when>"`
   Refuses if the unit tests fail, if the pre-declared fall-time decision has not been
   executed, if `moduleb/config.py` disagrees with it, if any recorded release decision
   no longer holds — including `FORECAST_REL_DELTA_CAP` not being `None` — if
   `RELEASE_MANIFEST.json` is missing, or if a frozen artifact already exists without
   `--force --reason`. Writes the artifact, the embedded and sidecar manifests, and
   `models/FREEZE_RECEIPT.json`.
4. `python scripts/12_predict_holdout.py --frozen` — **once**.
   Refuses a rehearsal artifact, a missing or placeholder sign-off, an embedded/sidecar
   mismatch, a manifest that fails its own digest, either digest going stale, a holdout
   delivery whose hash is not the attested one, a holdout lot that appears in the
   artifact's training lots, a holdout file carrying answers, and a spent one-shot.
   Writes the prediction file and `results/HOLDOUT_PREDICTION_RECEIPT.json`.
5. Nirmik sends the prediction file and its receipt to Sanskruti, who scores it
   independently; Anushka receives the prediction file only if final fusion needs it.

Between step 2 and step 4, nothing in the package changes. After step 4, nothing
changes in response to what Sanskruti reports.
