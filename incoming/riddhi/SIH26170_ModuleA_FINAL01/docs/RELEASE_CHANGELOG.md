# Release changelog — Module A

## package `final01.4.0` — 22 Sep 2026 · confusion-matrix audit

**Model unchanged: still `ModuleA-FINAL01`**, `config_digest` `2b2fa4da5ee36e7c…`.

**Added**

- `scripts/20_confusion_matrix.py` — all four cells for every result the release quotes,
  ten matrices, each reconciled (TP+TN+FP+FN = n) and cross-checked against
  `sklearn.metrics.confusion_matrix` **on every run**, not only in tests.
- `tests/test_confusion_matrix.py` — 72 tests. Every cell against sklearn on randomised
  inputs, the algebraic identities, and hand-written single-component cases that pin the
  **orientation**: a transposed FP/FN still balances and still produces rates in [0,1],
  so arithmetic alone cannot catch it.
- `docs/MASTER_PROMPT_CONFUSION_MATRIX.md` — what each cell costs on this problem, the
  seven reporting obligations, and why accuracy is never a headline here.

**Changed**

- `modulea.metrics.confusion` now returns all four cells plus `specificity`, `fnr`,
  `npv`, `accuracy`, `n`, `positives`, `negatives`, `passed`, and asserts the cells
  partition the sample. An undefined rate is **NaN, never 0.0** — three holdout lots
  have no anomalies and therefore no recall.
- Input guards: a truth vector that is not 0/1, or shapes that disagree, now raise.

**Fixed**

- **The packet build was not idempotent.** Stage 18 embedded a claim count that the
  post-packet ledger then changed, so rebuilding produced different archives — an
  archive whose hash moves cannot be verified by its recipient. The ledger now writes
  `10_verify_claims_with_packets.csv` separately, and the owner packet omits the packet
  build's own outputs. **All six zips are now byte-identical across rebuilds.**
- A claim check banned the word "accuracy" rather than an accuracy *figure*, and failed
  on the sentence explaining that accuracy is not reported. Now matches a number.

**Verification**

| | final01.3.0 | final01.4.0 |
|---|---:|---:|
| tests | 79 | 151 |
| claim checks | 151 | 166 (+ packet self-checks) |
| reproducibility | 44 of 44 | 47 of 47 |
| confusion matrices | not reported | 10, all balance |

---

## package `final01.3.0` — 22 Sep 2026 · two-run final verification

**Model unchanged: still `ModuleA-FINAL01-RC1`**, `config_digest` `2b2fa4da5ee36e7c…`.

Two independent canonical analysis runs, from separate clean extractions, compared file
by file: **44 of 44 byte-identical, verdict REPRODUCIBLE** (`19_reproducibility.csv`).
The six packet zips are byte-deterministic and four of six were already identical before
the remaining nondeterminism was removed.

**Fixed — five defects the two-run protocol found**

- **A provenance baseline that could erase itself.** The at-freeze source hash list lived
  in `results/`. A clean re-run destroyed it and stage 17 silently re-baselined to
  "nothing changed since freeze" — how a post-freeze change disappears from the record.
  It now lives in `models/SOURCE_TREE_AT_FREEZE.json` and stage 17 **refuses** to
  recreate it without `--record-as-freeze-state`. Recovered from the shipped archive;
  digest unchanged at `820d0201e3162a07`.
- **Four layers of circularity.** The claim ledger checked the reproducibility verdict;
  the packets embedded the claim count; the packet checks fired only when packets
  existed. Each prevented two runs converging. Analysis and release are now separate
  phases — `scripts/run_canonical.sh` is compared, `scripts/release.sh` runs once after.
- **A results file no stage produced.** `09_ranking_comparison.json` had been written by
  an ad-hoc command, so a clean run could not regenerate it. Folded into stage 09.
- **`runtime_contract.json` dropped from Anushka's packet** by the packet-builder
  rewrite, while her letter still pointed at it. Restored, and every packet now verifies
  its own checksums in the ledger.
- **Packet zips carried filesystem timestamps**, so identical content produced different
  bytes. Fixed entry timestamps; archives are now byte-comparable by the recipient.

**Added**

- `scripts/run_canonical.sh` and `scripts/release.sh` — the two-phase protocol.
- Six role-scoped packets with per-role letters, every figure interpolated from
  `results/` rather than typed.
- `docs/MASTER_PROMPT_FINAL_VERIFICATION.md` — the protocol, executed once already.

**Verification**

| | final01.2.0 | final01.3.0 |
|---|---:|---:|
| tests | 79 | 79 |
| claim checks | 138 | 151 |
| reproducibility | not measured | 44 of 44 |

---

## package `final01.2.0` — 22 Sep 2026 · pre-integration hardening

**Model unchanged: still `ModuleA-FINAL01-RC1`.** The release candidate is deliberately
not bumped. `config_digest` tracks what the model computes, and bumping it for a
hardening pass would move the digest and announce a new model that does not exist.

No change to the fitted model. `config_digest` and `runtime_contract_digest` are
identical to RC1; the four frozen holdout prediction files are byte-identical and still
verify against the hashes stage 08 recorded.

**Added**

- Robustness suite (stage 12): 19 cases — 6 invariances, 11 refusals, 2 sensitivities,
  1 documented semantic.
- Score semantics (stage 13): monotone in the anomaly rate; **not** a probability,
  largest gap 0.747; individual scores stable to ~0.02 under reference resampling.
- Sensitivity (stage 14): per lot, per variant, per severity; and the Module B
  corroboration association, recorded and explicitly ruled out as a rule.
- Fusion dry run (stage 15): Module A joined to `ModuleB-FINAL01-RC2`'s real frozen
  packet. 1,343 rows, 9 checks, all passing.
- Provenance (stage 17): per-file source hashes, at-freeze baseline, and an addendum
  that explains every post-freeze change and proves the one in the prediction path
  changed no emitted value.
- Packet builder (stage 18): a worked serving example, `RELEASE_IDENTITY.json`, and the
  integration packet for Anushka — derived from `results/`, never authored.
- Fail-safe: `state/CHECKPOINT.json` and `CONTINUATION.md`, so an interrupted session
  resumes without conversation history.
- Documents: `MASTER_PROMPT_DEPLOYMENT.md`, `ACCEPTANCE_CRITERIA.md`,
  `FUTURE_RELEASE_ITEMS.md`, `TEAM_HANDOFF.md`, this changelog.

**Corrected**

- **The headline nested estimate was quoted at the wrong budget.** An earlier revision
  reported 48 of 54 at 25 false alarms, which came from a 3% run while the release
  ships at 1%. The shipped figure is **45 of 54 at 9 false alarms**. Caught by
  `scripts/10_verify_claims.py` when stage 04 was re-run under the current config.
- **The weight-unanimity claim was budget-dependent and overstated.** "All 12 folds
  chose pure `lot_relative`" holds at a 3% budget; at the shipped 1% budget the folds
  split 6/6 between pure `lot_relative` and 0.9 `lot_relative` + 0.1 `temporal`. What
  *is* robust, and is now what the decision rests on: across all 24 fold-selections, no
  fold chose the inherited `overall_extreme`. Decision D3 restated.
- **One nested arm was mislabelled.** The arm described as "everything inherited" was
  using the newly selected weights with the inherited threshold, because the weights
  changed after that script was written. `config.LEGACY_WEIGHTS` now makes the
  before-state explicit, and a fourth `shipped` arm reports the actual configuration.

**Fixed**

- **A latent serving failure.** An empirical rank of exactly 1.0 mapped to exactly
  `CONFIRMED_FLOOR`, putting a component in the reserved out-of-specification band on
  statistical evidence alone; `contract.validate_output` would then correctly refuse the
  frame, so the top-ranked component of any batch was a crash waiting to happen. Eight
  holdout components sit at rank 1.0 and escaped only because all eight are also
  datasheet violations. Found by `tests/test_score_semantics.py`. The statistical band is
  now closed just below the floor. **Predictions byte-identical; both digests unchanged.**

**Verification**

| | final01.1.0 | final01.2.0 |
|---|---:|---:|
| tests | 38 | 79 |
| claim checks | 18 | 138 |

---

## package `final01.1.0`, model `ModuleA-FINAL01-RC1` — 22 Sep 2026 · first frozen release

First Module A release with the configuration selected under a protocol that holds out
whole lots and chooses inside the fold.

**Model**

- Better Potential's scoring formula, reimplemented with the aggregation depths as named
  parameters. `tests/test_equivalence.py` asserts bit-for-bit agreement with the
  inherited code under the inherited weights.
- **Weights changed to pure `lot_relative`**, selected unanimously by 12
  leave-one-lot-out folds. Adopted for simplicity, not performance — the difference
  against the inherited 0.90/0.10 is a statistical tie (PR AUC +0.0008, CI spans zero).
- **Operating threshold at a 1% calibration false-alarm budget**, at the curve's knee.
  The 3% figure from the RC2/RC3 work was a development budget and is not inherited.
- **A non-statistical CONFIRMED tier** from datasheet `static_spec_max`: 81 flags across
  5,400 components, 81 real anomalies, no observed false positive in 5,076 normals
  (95% upper bound 0.06%).

**Fixed from the inherited packages**

- C1 score/disposition non-monotonicity · C2 OOF threshold on a refit model ·
  C3 zero MAD scored as normal · C4 zero-weight component named as a reason ·
  C5 unstable attribution shipped without its margin · C6 selection on the full
  calibration set. Detail in `docs/IMPROVEMENTS.md`.

**Reported and not acted on**

- The frozen weights rank slightly *worse* on the holdout than the ones they replaced
  (PR AUC 0.8166 against 0.8239). Within noise, predicted by the calibration tie, and
  deliberately not reverted — decision D6.
