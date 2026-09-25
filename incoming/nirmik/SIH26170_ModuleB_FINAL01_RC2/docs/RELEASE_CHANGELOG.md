# Module B release changelog

Newest first. Every entry says what moved, which digest it moved, and what it did
**not** move.

---

## `ModuleB-FINAL01-RC2` — 20 Sep 2026 · frozen, and the one-shot spent

**State:** `HOLDOUT_PREDICTION_DELIVERED`.

Team sign-off was recorded and the two gated stages ran, in order, once each. The
fitted model did not change: the config digest is still `8d0621941f86fbb8…` and the
runtime contract digest is still `d19cec26170eb725…`, so the artifact produced here is
the release that was verified on 19 Sep.

- **Stage 11** froze on train + calibration (4,057 rows / 54 lots), embedded the
  sign-off in the manifest **before** serialising, wrote the sidecar from the same dict
  and `models/FREEZE_RECEIPT.json`, then reloaded the artifact through every load-time
  check to confirm what it had just written.
- **Stage 12** opened `03_HOLDOUT_AFTER_FREEZE/ModuleB_Holdout.csv` for the first time,
  verified the delivery hash against the declared manifest, asserted the 18 holdout lots
  were disjoint from the artifact's own 54 training lots, predicted under the serving
  contract with a hash-verified delivery attestation, and wrote
  `results/ModuleB_Final_Holdout_Predictions.csv` (1,343 rows) plus
  `results/HOLDOUT_PREDICTION_RECEIPT.json`.

**Post-freeze source changes — verification suite only.** Four files were edited *after*
the freeze so that the package's own checks describe the state it is now in rather than
the state it was in: `moduleb/holdout_manifest.py` (the spend state is now read from
disk by `one_shot_state()` instead of being asserted in a constant that went stale the
moment stage 12 ran), `moduleb/decisions.py` (D14's predicate is about the pre-freeze
history, which does not change when the one-shot is spent),
`tests/test_release_gates.py` and `scripts/14_verify_claims.py` (both state-aware, and
now verify consistency between disk, the documents and the two receipts — a stronger
check than either fixed state). Documents were updated to match.

**The model config digest and the runtime contract digest are unchanged**, so the frozen
artifact still loads and every guarantee stage 12 made still holds. The **source tree
digest did move** — that is honest and expected, and both values are recorded: the
artifact's own manifest carries the digest of the tree it was frozen from.

---

## `ModuleB-FINAL01-RC2` — 19 Sep 2026 · release engineering

**State:** `READY_FOR_TEAM_SIGNOFF`. Not frozen. Holdout unspent. No sign-off claimed.

**The fitted model did not change.** No coefficient, no hyper-parameter, no feature
set, no envelope offset and no recorded metric moved in this round. Every number in
`results/` is still from the recorded run of 18 Sep 2026, and
`frozen_config_digest()` still begins `8d0621941f86fbb8`. What changed is the
machinery around the model: what it refuses, what it records, and what it claims.

### Freeze blockers closed

| ID | What was wrong | What it is now |
|---|---|---|
| **P0-B1** | `MIN_LOT_COHORT = 30` was a size floor being used as a completeness proof. A lot of 82 delivered with 61 rows cleared it and produced a different, confident answer. | `moduleb/serving.py`. Completeness must be **proved** — declared per-lot sizes, or the custodian's whole-file attestation — and any unproved lot is refused whatever its row count. The floor survives as a secondary sanity check. `allow_partial_lot=True` remains the one explicit, recorded, degraded override. |
| **P0-B2** | Team sign-off was written to a sidecar **after** the artifact had been serialised, so the pickled manifest carried no approval and the only record lived in an editable file. | The manifest is completed **before** serialisation, sign-off embedded, sidecar written from the same dict. `load_frozen` refuses a missing sign-off, an embedded/sidecar mismatch, a manifest that fails its own digest, and a rehearsal artifact presented as production. |
| **P0-B3** | D11 ("the cap stays off") was prose. Nothing stopped a freeze with the cap on. | `moduleb/decisions.py` carries a predicate per decision (D1, D10, D11, D12, D13, D14) that reads the live code. `freeze.freeze` and stage 11 run them as a preflight and refuse. A negative test turns the cap on and asserts the freeze fails. |
| **P0-B4** | One digest covered the fitted model only, so a serving-behaviour change was invisible to a consumer holding it. | `serving.runtime_contract_digest()` covers the non-fitted release surface; the manifest carries both, plus a source-tree digest; stage 12 validates both. Tested in each direction. |

### Governance

| ID | Change |
|---|---|
| **P1-G1** | The claim that the holdout had "never been opened" is withdrawn and replaced by the recorded history in `moduleb/holdout_manifest.py` (**D14**): the predictor-only file *was* read for structure, it has no targets, no forecast was generated, no score was observed, no decision used one, and the one-shot is unspent. Pre-freeze stages now read the declared structure instead of the file; exactly one gated stage may open it, and a test enforces that. Hashing the file is still allowed everywhere — provenance, not content. |

### Documentation and executable claims

**P2.** Nine withdrawn or overstated claims were still being asserted, most of them by
code rather than by prose — a `print()` that says the wrong thing ships the wrong
thing. Corrected at source in `scripts/02`, `scripts/07`, `scripts/08`, `scripts/10`,
`moduleb/envelope.py`, `notebooks/N1_audit.ipynb`, `docs/COMPLETE_GUIDE.md` and
`docs/CHATGPT_REVIEW_PROMPT.md`. Stage 14 now scans the scripts, the notebooks, the
package source and `RELEASE_MANIFEST.json` in addition to the documents, and it no
longer quotes its own check count in prose — the count is recorded in
`RELEASE_MANIFEST.json`.

**S1–S8.** Secondary technical audit; see `docs/ROUND2_FINAL_ADJUDICATION.md` for the
per-item disposition. Six wording corrections (S1, S2, S3, S4, S5, S6, S7), one item
verified with no change required (S8).

### Added

`moduleb/serving.py` · `moduleb/decisions.py` · `moduleb/holdout_manifest.py` ·
`scripts/15_release_manifest.py` · `tests/test_serving.py` ·
`tests/test_release_gates.py` · `RELEASE_MANIFEST.json` ·
`docs/TEAM_HANDOFF.md` · `docs/FINAL_FREEZE_READINESS.md` ·
`docs/ROUND2_FINAL_ADJUDICATION.md` · `docs/RELEASE_CHANGELOG.md` ·
`docs/FUTURE_RELEASE_ITEMS.md` · `TEAM_DISTRIBUTION/`

### Removed

`models/FREEZE_SIGNOFF.json` — superseded by the embedded manifest and
`models/FREEZE_RECEIPT.json`. The rehearsal artifact no longer lands in `results/`; it
is written to a temporary directory and deleted.

---

## `ModuleB-FINAL01-RC1` — 19 Sep 2026 · round-1 review applied

Serving contract declared cohort-level (D12); tail metric re-ranked by observed drift
(D13); the conformal validity claim withdrawn (F2); the false batch-size invariance
test replaced by one that measures what actually happens (F1); cap denominators
corrected (F5); four further wording corrections. Full adjudication in
`docs/ROUND1_ADJUDICATION.md`. The fitted model did not change.

## `ModuleB-FINAL01-RC0` — 18 Sep 2026 · the recorded run

The frozen Candidate-V1 configuration rerun untouched on `SIH26170-FINAL-01`:
benchmarked, grid-checked, calibrated, the pre-declared fall-time rule executed and
spent, extrapolation risk measured, reason codes audited, envelope coverage measured,
freeze and holdout rehearsed. Every figure quoted anywhere in this package comes from
this run.
