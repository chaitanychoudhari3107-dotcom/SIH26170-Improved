"""Fixed facts about SIH26170-FINAL-01. Nothing here is fitted or tuneable."""
from __future__ import annotations

DATASET_ID = "SIH26170-FINAL-01"
MODEL_VERSION = "ModuleA-FINAL01"

PARAMETERS = [
    "IDDQ",
    "Input_Leakage_Current",
    "Active_Supply_Current",
    "Propagation_Delay",
    "Output_Rise_Time",
    "Output_Fall_Time",
]
EPOCHS = [0, 24, 96, 168]
IDENTIFIERS = ["component_id", "lot_id", "device_family", "device_variant"]

# The five fields the integration contract fixes. Order is part of the contract.
CONTRACT_FIELDS = [
    "component_id",
    "module_a_score",
    "module_a_disposition",
    "module_a_primary_parameter",
    "module_a_reason_codes",
]
# Additive diagnostic columns. The handoff permits these; fusion may ignore them.
DIAGNOSTIC_FIELDS = [
    "module_a_evidence_tier",
    "module_a_attribution_margin",
    "statistical_score",
    "spec_exceedance_ratio",
    "scored_epoch_h",
    "analysis_status",
    "model_version",
    "dataset_id",
]

DISPOSITIONS = ["PASS", "MONITOR"]          # Module A never emits REJECT. Fusion owns that.
EVIDENCE_TIERS = ["PASS", "MONITOR", "CONFIRMED"]

# module_a_score is one monotone number with a reserved band, so that a single
# threshold on it reproduces Module A's own decision exactly.
#   [0.00, 0.90)  statistical evidence, rank-based
#   [0.90, 1.00]  a datasheet static limit is exceeded — CONFIRMED
STATISTICAL_BAND = (0.0, 0.90)
CONFIRMED_BAND = (0.90, 1.0)


def observed_columns(epoch: int) -> list[str]:
    """Columns a model is allowed to read when scoring at `epoch`. Nothing later."""
    return [f"{p}_{e}h" for p in PARAMETERS for e in EPOCHS if e <= epoch]


def future_columns(epoch: int) -> list[str]:
    return [f"{p}_{e}h" for p in PARAMETERS for e in EPOCHS if e > epoch]
