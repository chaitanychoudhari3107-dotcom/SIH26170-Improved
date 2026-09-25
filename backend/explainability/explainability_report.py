import pandas as pd
from pathlib import Path


# ============================================================
# 1. FILE PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"

FUSED_FILE = DATA_DIR / "fused_component_summary.csv"
PREDICTIONS_FILE = DATA_DIR / "moduleb_predictions_long.csv"


# ============================================================
# 2. LOAD FILES
# ============================================================

fused = pd.read_csv(FUSED_FILE)
predictions = pd.read_csv(PREDICTIONS_FILE)


# ============================================================
# 3. CHECK REQUIRED COLUMNS
# ============================================================

required_fused = [
    "component_id",
    "lot_id_A",
    "device_variant_A",
    "disposition_A",
    "risk_A",
    "driving_parameter_A",
    "confidence_A",
    "reason_code_A",
    "reason_text_A",
    "disposition_B",
    "risk_B",
    "driving_parameter_B",
    "driving_headroom_frac",
    "confidence_B",
    "extrapolation_flag",
    "reason_code_B",
    "reason_text_B",
    "final_decision"
]

required_predictions = [
    "component_id",
    "parameter",
    "unit",
    "value_0h",
    "value_24h",
    "pred_168h",
    "pred_168h_lo",
    "pred_168h_hi",
    "spec_limit",
    "limit_direction",
    "headroom_abs",
    "headroom_frac",
    "extrapolation_flag"
]


def check_columns(df, required_columns, file_name):
    missing = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{file_name} is missing columns: {missing}"
        )


check_columns(
    fused,
    required_fused,
    "fused_component_summary.csv"
)

check_columns(
    predictions,
    required_predictions,
    "moduleb_predictions_long.csv"
)


# ============================================================
# 4. CREATE EXPLAINABILITY REPORT
# ============================================================

reports = []


for _, component in fused.iterrows():

    component_id = component["component_id"]

    # --------------------------------------------------------
    # Select the most relevant parameter
    # --------------------------------------------------------

    parameter = component["driving_parameter_B"]

    if pd.isna(parameter) or str(parameter).strip() == "":
        parameter = component["driving_parameter_A"]

    # --------------------------------------------------------
    # Find prediction information for this component
    # --------------------------------------------------------

    component_predictions = predictions[
        predictions["component_id"] == component_id
    ]

    parameter_row = component_predictions[
        component_predictions["parameter"] == parameter
    ]

    # If exact driving parameter is not found,
    # use the first available parameter.
    if parameter_row.empty and not component_predictions.empty:
        parameter_row = component_predictions.iloc[[0]]

    # --------------------------------------------------------
    # Extract prediction information
    # --------------------------------------------------------

    if not parameter_row.empty:

        pred = parameter_row.iloc[0]

        unit = pred["unit"]
        value_0h = pred["value_0h"]
        value_24h = pred["value_24h"]
        pred_168h = pred["pred_168h"]
        pred_lo = pred["pred_168h_lo"]
        pred_hi = pred["pred_168h_hi"]
        spec_limit = pred["spec_limit"]
        limit_direction = pred["limit_direction"]
        headroom_abs = pred["headroom_abs"]
        headroom_frac = pred["headroom_frac"]

    else:

        unit = ""
        value_0h = ""
        value_24h = ""
        pred_168h = ""
        pred_lo = ""
        pred_hi = ""
        spec_limit = ""
        limit_direction = ""
        headroom_abs = ""
        headroom_frac = ""


    # ========================================================
    # 5. CREATE HUMAN-READABLE REASON
    # ========================================================

    final_decision = component["final_decision"]

    reason_a = str(component["reason_text_A"])
    reason_b = str(component["reason_text_B"])

    if final_decision == "REJECT":

        explanation = (
            f"Final decision is REJECT because at least one module "
            f"identified a reject condition. "
            f"Module A: {reason_a} "
            f"Module B: {reason_b}"
        )

    elif final_decision == "MONITOR":

        if str(component["extrapolation_flag"]).lower() == "true":

            explanation = (
                "Final decision is MONITOR because the Module B "
                "prediction involves extrapolation or uncertainty. "
                "The prediction should therefore be reviewed rather "
                "than treated as a confident PASS."
            )

        else:

            explanation = (
                f"Final decision is MONITOR because at least one "
                f"module identified a condition requiring attention. "
                f"Module A: {reason_a} "
                f"Module B: {reason_b}"
            )

    else:

        explanation = (
            "Final decision is PASS because neither Module A nor "
            "Module B identified a reject or monitor condition."
        )


    # ========================================================
    # 6. ADD REPORT ROW
    # ========================================================

    reports.append({

        "component_id": component_id,
        "lot_id": component["lot_id_A"],
        "device_variant": component["device_variant_A"],

        "final_decision": final_decision,

        "module_A_decision": component["disposition_A"],
        "module_A_risk": component["risk_A"],
        "module_A_reason_code": component["reason_code_A"],
        "module_A_reason": reason_a,

        "module_B_decision": component["disposition_B"],
        "module_B_risk": component["risk_B"],
        "module_B_reason_code": component["reason_code_B"],
        "module_B_reason": reason_b,

        "driving_parameter": parameter,
        "unit": unit,

        "value_0h": value_0h,
        "value_24h": value_24h,

        "predicted_168h": pred_168h,
        "prediction_lower": pred_lo,
        "prediction_upper": pred_hi,

        "spec_limit": spec_limit,
        "limit_direction": limit_direction,

        "headroom_abs": headroom_abs,
        "headroom_frac": headroom_frac,

        "confidence_A": component["confidence_A"],
        "confidence_B": component["confidence_B"],
        "extrapolation_flag": component["extrapolation_flag"],

        "explanation": explanation
    })


# ============================================================
# 7. SAVE REPORT
# ============================================================

report = pd.DataFrame(reports)

OUTPUT_FILE = DATA_DIR / "explainability_report.csv"

report.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# 8. PRINT SUMMARY
# ============================================================

print("\n======================================")
print("   EXPLAINABILITY REPORT COMPLETE")
print("======================================")

print(f"Report file: {OUTPUT_FILE}")

print(f"\nComponents explained: {len(report)}")

print("\nDecision counts:")
print(
    report["final_decision"].value_counts()
)

print("\nSample explanations:")

print(
    report[
        [
            "component_id",
            "driving_parameter",
            "final_decision",
            "explanation"
        ]
    ].head(5).to_string(index=False)
)
