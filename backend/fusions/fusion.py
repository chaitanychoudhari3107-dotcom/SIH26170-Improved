import pandas as pd
from pathlib import Path


# ============================================================
# 1. FILE PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"

MODULE_A_FILE = DATA_DIR / "modulea_component_summary.csv"
MODULE_B_FILE = DATA_DIR / "moduleb_component_summary.csv"


# ============================================================
# 2. LOAD MODULE A AND MODULE B OUTPUTS
# ============================================================

module_a = pd.read_csv(MODULE_A_FILE)
module_b = pd.read_csv(MODULE_B_FILE)


# ============================================================
# 3. CHECK REQUIRED COLUMNS
# ============================================================

required_a = [
    "component_id",
    "lot_id",
    "device_variant",
    "disposition_A",
    "risk_A",
    "driving_parameter",
    "n_params_flagged",
    "confidence",
    "reason_code",
    "reason_text"
]

required_b = [
    "component_id",
    "lot_id",
    "device_variant",
    "disposition_B",
    "risk_B",
    "driving_parameter",
    "driving_headroom_frac",
    "n_params_predicted",
    "n_params_flagged",
    "confidence",
    "extrapolation_flag",
    "reason_code",
    "reason_text"
]


def check_columns(df, required_columns, module_name):
    missing = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{module_name} is missing columns: {missing}"
        )


check_columns(module_a, required_a, "Module A")
check_columns(module_b, required_b, "Module B")


# ============================================================
# 4. JOIN MODULE A + MODULE B
# ============================================================

merged = pd.merge(
    module_a,
    module_b,
    on="component_id",
    how="inner",
    suffixes=("_A", "_B")
)


# ============================================================
# 5. CHECK JOIN
# ============================================================

if len(merged) == 0:
    raise ValueError("No components were matched between Module A and Module B.")

print(f"Module A components : {len(module_a)}")
print(f"Module B components : {len(module_b)}")
print(f"Joined components   : {len(merged)}")


# ============================================================
# 6. FUSION LOGIC
# ============================================================

def fuse_decision(row):

    disposition_a = str(row["disposition_A"]).upper()
    disposition_b = str(row["disposition_B"]).upper()

    extrapolation = row["extrapolation_flag"]

    # --------------------------------------------------------
    # RULE 1:
    # Module A REJECT -> Final REJECT
    # --------------------------------------------------------
    if disposition_a == "REJECT":
        return "REJECT"

    # --------------------------------------------------------
    # RULE 2:
    # Module B REJECT -> Final REJECT
    # --------------------------------------------------------
    if disposition_b == "REJECT":
        return "REJECT"

    # --------------------------------------------------------
    # RULE 3:
    # Extrapolation / uncertain prediction
    # -> At least MONITOR
    # --------------------------------------------------------
    if extrapolation is True or str(extrapolation).lower() == "true":
        return "MONITOR"

    # --------------------------------------------------------
    # RULE 4:
    # Module A MONITOR -> Final MONITOR
    # --------------------------------------------------------
    if disposition_a == "MONITOR":
        return "MONITOR"

    # --------------------------------------------------------
    # RULE 5:
    # Module B MONITOR -> Final MONITOR
    # --------------------------------------------------------
    if disposition_b == "MONITOR":
        return "MONITOR"

    # --------------------------------------------------------
    # RULE 6:
    # Both modules PASS -> Final PASS
    # --------------------------------------------------------
    if disposition_a == "PASS" and disposition_b == "PASS":
        return "PASS"

    # --------------------------------------------------------
    # SAFETY FALLBACK:
    # Anything unknown -> MONITOR
    # --------------------------------------------------------
    return "MONITOR"


merged["final_decision"] = merged.apply(
    fuse_decision,
    axis=1
)


# ============================================================
# 7. CREATE FINAL INTEGRATION OUTPUT
# ============================================================

final_output = merged[
    [
        "component_id",
        "lot_id_A",
        "device_variant_A",
        "disposition_A",
        "risk_A",
        "driving_parameter_A",
        "n_params_flagged_A",
        "confidence_A",
        "reason_code_A",
        "reason_text_A",

        "disposition_B",
        "risk_B",
        "driving_parameter_B",
        "driving_headroom_frac",
        "n_params_flagged_B",
        "confidence_B",
        "extrapolation_flag",
        "reason_code_B",
        "reason_text_B",

        "final_decision"
    ]
].copy()


# ============================================================
# 8. SAVE FUSED OUTPUT
# ============================================================

OUTPUT_FILE = DATA_DIR / "fused_component_summary.csv"

final_output.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# 9. PRINT SUMMARY
# ============================================================

print("\n======================================")
print("       FUSION COMPLETE")
print("======================================")

print(f"Output file: {OUTPUT_FILE}")

print("\nFinal decision counts:")
print(final_output["final_decision"].value_counts())

print("\nFirst 10 results:")
print(
    final_output[
        [
            "component_id",
            "disposition_A",
            "disposition_B",
            "final_decision"
        ]
    ].head(10)
)