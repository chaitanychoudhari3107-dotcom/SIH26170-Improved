"""The frozen configuration, and its digest.

Everything a scoring run depends on is here, so the digest below changes if any
of it changes. A release whose recorded digest does not match what the code
computes is not the release it claims to be, and `freeze.py` refuses it.

Provenance of each value is stated because two of them are inherited rather than
selected under this release's protocol, and that distinction is the difference
between an honest number and an optimistic one.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field

from modulea.scoring import Depths

# --- component weights -------------------------------------------------
# PROVENANCE: SELECTED under this release's nested protocol, not inherited. The
# inherited Better Potential weights were 0.90 lot_relative / 0.10 overall_extreme,
# grid-searched over the FULL calibration set. scripts/04_nested_validation.py
# re-ran that search inside each of 12 leave-one-lot-out folds, and all twelve
# independently chose pure lot_relative. Adopted because it is strictly simpler —
# one component instead of two — and unanimously selected, not because of the one
# extra anomaly it caught. See results/04_selected_weights_per_fold.csv, DECISION_LOG D3.
WEIGHTS = {
    "electrical": 0.0,
    "temporal": 0.0,
    "timing": 0.0,
    "overall_extreme": 0.0,
    "lot_relative": 1.0,
}

# --- operating threshold ------------------------------------------------
# PROVENANCE: selected on calibration leave-one-lot-out scores as the loosest cut
# whose out-of-fold false-positive rate stays within OPERATING_FPR_BUDGET.
# It is a team decision, not a universal requirement; DECISION_LOG D2 records why
# this budget and not another. Short version: the curve has a knee there. Moving
# to a 3% budget buys one more anomaly of 54 and costs sixteen more false alarms.
OPERATING_FPR_BUDGET = 0.01
OPERATING_THRESHOLD = 0.9395405078597341

# The inherited configuration, kept only so the release can be compared against the
# published Better Potential / RC2 / RC3 numbers. Never used for a decision here, and
# deliberately outside config_payload() so quoting it cannot move the digest.
LEGACY_THRESHOLD = 0.936978
LEGACY_WEIGHTS = {
    "electrical": 0.0,
    "temporal": 0.0,
    "timing": 0.0,
    "overall_extreme": 0.10,
    "lot_relative": 0.90,
}

# --- early epochs --------------------------------------------------------
# Thresholds on the observed-evidence statistic, fitted on CALIBRATION NORMALS
# ONLY at the same budget. No early classifier is trained against a final label:
# at 0 h a component whose defect has not yet begun is not detectable, and a model
# taught otherwise is learning the lot, not the part.
EARLY_FPR_BUDGET = 0.03
EARLY_THRESHOLDS: dict[str, float] = {}     # written by scripts/03, read at freeze

DEPTHS = Depths()

DATASET_ID = "SIH26170-FINAL-01"
MODEL_VERSION = "ModuleA-FINAL01"
RELEASE_CANDIDATE = "ModuleA-FINAL01-RC1"
# Deliberately NOT part of config_payload(). The config digest tracks what the model
# computes; packaging, documentation and verification move without it. Bumping the
# release candidate for a hardening pass would move the digest and falsely announce a
# new model. See PROVENANCE_ADDENDUM.json.
PACKAGE_VERSION = "final01.5.0"


@dataclass(frozen=True)
class RuntimeContract:
    """What the serving path promises, separately digested from the fitted model."""
    join_key: str = "component_id"
    emits_disposition: tuple = ("PASS", "MONITOR")
    emits_reject: bool = False
    requires_complete_lots: bool = True
    min_lot_size: int = 30
    contract_fields: tuple = ("component_id", "module_a_score", "module_a_disposition",
                              "module_a_primary_parameter", "module_a_reason_codes")
    monitor_floor_is_published: bool = True
    invents_static_limits: bool = False


RUNTIME_CONTRACT = RuntimeContract()


def config_payload() -> dict:
    return {
        "dataset_id": DATASET_ID,
        "model_version": MODEL_VERSION,
        "release_candidate": RELEASE_CANDIDATE,
        "weights": WEIGHTS,
        "depths": asdict(DEPTHS),
        "operating_threshold": OPERATING_THRESHOLD,
        "operating_fpr_budget": OPERATING_FPR_BUDGET,
        "early_fpr_budget": EARLY_FPR_BUDGET,
    }


def _digest(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def config_digest() -> str:
    return _digest(config_payload())


def runtime_contract_digest() -> str:
    return _digest(asdict(RUNTIME_CONTRACT))
