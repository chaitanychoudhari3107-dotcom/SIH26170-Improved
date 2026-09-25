"""
moduleb.constants — the vocabulary of the dataset contract.

Nothing here is tunable. These names come from SIH26170-FINAL-01's
Schema_Data_Dictionary.csv and ModuleB_Output_Contract.csv; if one of them ever
disagrees with this file, the CSV wins and this file is the bug.

Read alongside:  data/REFERENCE/Schema_Data_Dictionary.csv
                 data/REFERENCE/ModuleB_Output_Contract.csv
"""
from __future__ import annotations

DATASET_ID = "SIH26170-FINAL-01"
MODULE = "B"

# ---------------------------------------------------------------- parameters
# Order is load-bearing: it fixes the column order of the output contract.
PARAMS: list[str] = [
    "IDDQ",
    "Input_Leakage_Current",
    "Active_Supply_Current",
    "Propagation_Delay",
    "Output_Rise_Time",
    "Output_Fall_Time",
]

UNITS: dict[str, str] = {
    "IDDQ": "uA",
    "Input_Leakage_Current": "uA",
    "Active_Supply_Current": "uA",
    "Propagation_Delay": "ns",
    "Output_Rise_Time": "ns",
    "Output_Fall_Time": "ns",
}

# The two physical blocks. They are separated because their early-signal
# structure differs, not because it is tidy — see moduleb.config.RECOMMENDED.
CURRENT_GROUP = ["IDDQ", "Input_Leakage_Current", "Active_Supply_Current"]
TIMING_GROUP = ["Propagation_Delay", "Output_Rise_Time", "Output_Fall_Time"]

# ---------------------------------------------------------------- epochs
PREDICTOR_EPOCHS = ("0h", "24h")   # the only epochs Module B may read as input
FORBIDDEN_EPOCHS = ("96h",)        # hard rule: never a Module B predictor
TARGET_EPOCH = "168h"              # target only; absent from the holdout file

# ---------------------------------------------------------------- context
ID_COLS = ["component_id", "lot_id", "device_family", "device_variant"]
JOIN_KEY = "component_id"
GROUP_KEY = "lot_id"               # every split is by whole lot, never by row
VARIANTS = ["CMOS_A", "CMOS_B", "CMOS_C"]
DEVICE_FAMILY = "DIGITAL_CMOS"

# ---------------------------------------------------------------- derived
PREDICTOR_COLS = [f"{p}_{e}" for p in PARAMS for e in PREDICTOR_EPOCHS]
TARGET_COLS = [f"{p}_{TARGET_EPOCH}" for p in PARAMS]
INPUT_COLS = ID_COLS + PREDICTOR_COLS          # what a holdout row must carry

# ---------------------------------------------------------------- output contract
# ModuleB_Output_Contract.csv, exactly. There is deliberately NO
# module_b_disposition column — see docs/DECISION_LOG.md D1.
def contract_columns(tau_pct: int) -> list[str]:
    return (
        [JOIN_KEY]
        + [f"predicted_{p}_{TARGET_EPOCH}" for p in PARAMS]
        + [f"module_b_p{tau_pct}_{p}_{TARGET_EPOCH}" for p in PARAMS]
        + ["module_b_primary_parameter", "module_b_reason_codes"]
    )

FORBIDDEN_OUTPUT_COLS = ["module_b_disposition", "module_b_pass", "module_b_verdict"]

# Substrings that mark a column as hidden generator truth. Matched
# case-insensitively against every incoming column name.
HIDDEN_LABEL_TOKENS = (
    "anomal", "defect", "ground_truth", "groundtruth", "severity", "behavior",
    "behaviour", "onset", "spec_pass", "is_bad", "label", "truth", "injected",
    "trajectory", "is_fail", "disposition",
)
