"""
moduleb.holdout_manifest — what Module B is allowed to know about the holdout
before the freeze, and nothing else.

Why this module exists
----------------------
Until 19 Sep 2026 several safe pre-freeze stages read the real holdout file's
contents to print its shape: stage 0 loaded it through `dataio.load_split`,
stage 1 tabulated its rows, lots and columns, stage 10 read its header to check
the stand-in matched, and stage 14 re-derived 18 lots from it. None of those
reads saw a 168 h answer — the file does not contain one — and no forecast, no
score and no model decision ever came from them. But "the holdout was never
opened" was still the wrong sentence to put in a document, and a stage that
opens the file is a stage that *could* start depending on its contents.

Decision D14 (19 Sep 2026) resolves both halves:

  * the history is recorded honestly rather than rewritten, and
  * from this release onward the structural facts live HERE, as declared
    constants, and the pre-freeze stages read this module instead of the file.

The values below were recorded from that earlier structural read and are
verified against the custodian's own delivery hash. Nothing here is derived from
a 168 h target, because the file has none: `HAS_TARGETS = False` is the point of
the split.

The only thing any pre-freeze stage may still do with the real file is hash it.
A SHA-256 is provenance, not content: it proves the delivery is the one the
manifest describes without reading a single measurement.
"""
from __future__ import annotations

from .constants import ID_COLS, PREDICTOR_COLS

# ---------------------------------------------------------------- declaration
SPLIT = "holdout"
PATH_HINT = "data/03_HOLDOUT_AFTER_FREEZE/ModuleB_Holdout.csv"

SHA256 = "e8082400cc815049ff52cbabf1940ca32663910e92d133f4ccc912e6b0d1cfe9"
N_ROWS = 1343
N_LOTS = 18
N_COLUMNS = 16
LOTS_PER_VARIANT = 6
ROWS_PER_LOT_MIN = 69
ROWS_PER_LOT_MAX = 82
HAS_TARGETS = False

# The declared header, in order. Identical to ID_COLS + PREDICTOR_COLS by
# construction — the holdout is the input contract with the answers removed —
# so the stand-in check in stage 10 can be made against the contract itself
# rather than against the file.
COLUMNS: list[str] = list(ID_COLS) + list(PREDICTOR_COLS)

# ---------------------------------------------------------------- provenance
PROVENANCE = dict(
    decision="D14",
    recorded="2026-09-19",
    predictor_only_file_read_before_freeze=True,
    hidden_168h_truth_available_to_module_b=False,
    holdout_forecast_generated=False,
    holdout_score_observed=False,
    model_or_config_decision_used_holdout_outcome=False,
    # The spend state is NOT asserted here. This block is the corrected record of what
    # happened BEFORE the freeze, and that record does not change when the one-shot is
    # later spent. Asking whether it has been spent is a question about disk, so it is
    # answered by one_shot_state() below and recorded in the release manifest and the
    # prediction receipt. A constant that said "UNSPENT" would have gone stale the
    # moment stage 12 ran — exactly the class of defect round 2 was about.
    one_shot_predictive_evaluation_at_record_time="UNSPENT (2026-09-19)",
    statement=(
        "The predictor-only holdout file was read for structural and schema "
        "checks before this release. It carries no 168 h targets, none were "
        "available to Module B, no holdout forecast was produced and no holdout "
        "score was ever observed, so no model or configuration decision used a "
        "holdout outcome. The one-shot predictive evaluation was unspent when this "
        "record was made; whether it has since been spent is read from disk by "
        "one_shot_state() and recorded in the release manifest and the prediction "
        "receipt, never asserted here. From this release onward the pre-freeze stages "
        "read moduleb.holdout_manifest instead of the file, and a test fails if one of "
        "them opens it."
    ),
)


def one_shot_state(root=None) -> str:
    """SPENT or UNSPENT, read from disk rather than asserted in a constant."""
    from pathlib import Path
    r = Path(root) if root is not None else Path(__file__).resolve().parent.parent
    return "SPENT" if (r / "results" / "ModuleB_Final_Holdout_Predictions.csv").exists() \
        else "UNSPENT"

# Stages that are allowed to READ THE CONTENTS of the real holdout file. Exactly
# one, and it is gated. tests/test_release_gates.py enforces this list against
# the source tree.
CONTENT_READERS = ("scripts/12_predict_holdout.py",)


def as_dict() -> dict:
    """The declared structure, for manifests and receipts."""
    return dict(split=SPLIT, path=PATH_HINT, sha256=SHA256, n_rows=N_ROWS,
                n_lots=N_LOTS, n_columns=N_COLUMNS, has_targets=HAS_TARGETS,
                columns=list(COLUMNS), provenance=dict(PROVENANCE))


def verify_delivery_hash(actual_sha256: str) -> None:
    """Confirm the file on disk is the delivery this module describes.

    Hashing does not read the measurements. If Chaitany reissues the holdout,
    this raises and the declared structure above must be reissued with it —
    which is the behaviour we want, rather than silently predicting on a file
    nobody attested to.
    """
    if actual_sha256 != SHA256:
        raise ValueError(
            "the holdout file on disk is not the delivery recorded in "
            "moduleb.holdout_manifest.\n"
            f"  declared: {SHA256}\n"
            f"  on disk : {actual_sha256}\n"
            "Do not predict on it. Ask Chaitany which delivery is current and "
            "reissue the declared manifest before the freeze.")
