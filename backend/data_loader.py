"""
data_loader.py — Authoritative data loader for SIH26170 Final Holdout Dataset.

Loads final dataset artifacts from data/final/ and data/reference/ into memory
at startup for low-latency API serving.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

PARAMS = [
    "IDDQ",
    "Input_Leakage_Current",
    "Active_Supply_Current",
    "Propagation_Delay",
    "Output_Rise_Time",
    "Output_Fall_Time",
]

def _load_json(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _load_csv(path: Path) -> pd.DataFrame:
    if path.exists():
        df = pd.read_csv(path)
        return df.replace({np.nan: None})
    return pd.DataFrame()


def _clean(val: Any) -> Any:
    """Recursively convert numpy scalars to native python primitives and NaN to None."""
    if val is None:
        return None
    if isinstance(val, (np.integer, int)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        if np.isnan(val) or np.isinf(val):
            return None
        return float(val)
    if isinstance(val, np.ndarray):
        return [_clean(x) for x in val.tolist()]
    if isinstance(val, dict):
        return {k: _clean(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_clean(v) for v in val]
    return val

# Final Data
fusion_df = _load_csv(DATA_DIR / "final" / "Fusion_Joined_Holdout.csv")
holdout_input_df = _load_csv(DATA_DIR / "final" / "ModuleB_Holdout.csv")
holdout_measurements_df = _load_csv(DATA_DIR / "final" / "ModuleA_Holdout_Measurements.csv")
if not holdout_measurements_df.empty:
    if not holdout_measurements_df["component_id"].is_unique:
        raise ValueError("Duplicate component IDs in full holdout measurements")
    holdout_measurements_df.set_index("component_id", drop=False, inplace=True)

if not holdout_input_df.empty and "component_id" in holdout_input_df.columns:
    holdout_input_df.set_index("component_id", drop=False, inplace=True)
    # Merge lot_id and device_variant into fusion_df if not already present
    for col in ["lot_id", "device_family", "device_variant"]:
        if col in holdout_input_df.columns and col not in fusion_df.columns:
            fusion_df[col] = fusion_df["component_id"].map(holdout_input_df[col])

if not fusion_df.empty:
    fusion_df.set_index("component_id", drop=False, inplace=True)

module_a_dfs = {
    0: _load_csv(DATA_DIR / "final" / "ModuleA_Final_Holdout_0h.csv"),
    24: _load_csv(DATA_DIR / "final" / "ModuleA_Final_Holdout_24h.csv"),
    96: _load_csv(DATA_DIR / "final" / "ModuleA_Final_Holdout_96h.csv"),
    168: _load_csv(DATA_DIR / "final" / "ModuleA_Final_Holdout_168h.csv"),
}
for epoch, df in module_a_dfs.items():
    if not df.empty and "component_id" in df.columns:
        df.set_index("component_id", drop=False, inplace=True)

module_b_df = _load_csv(DATA_DIR / "final" / "ModuleB_Final_Holdout_Predictions.csv")
if not module_b_df.empty and "component_id" in module_b_df.columns:
    module_b_df.set_index("component_id", drop=False, inplace=True)

# Manifests & References
module_a_manifest = _load_json(DATA_DIR / "final" / "ModuleA_Release_Manifest.json")
module_b_manifest = _load_json(DATA_DIR / "final" / "ModuleB_Release_Manifest.json")
device_specs_df = _load_csv(DATA_DIR / "reference" / "Device_Specs.csv")
schema_dictionary_df = _load_csv(DATA_DIR / "reference" / "Schema_Data_Dictionary.csv")
dataset_version = _load_json(DATA_DIR / "reference" / "Dataset_Version_Safe.json")

def compute_verdict(row: pd.Series) -> str:
    """Compute fused final verdict from Module A screening + Module B 168h prognosis."""
    tier = row.get("module_a_evidence_tier")
    if tier == "CONFIRMED":
        return "REJECT"
    for p in PARAMS:
        pred = row.get(f"predicted_{p}_168h")
        p95 = row.get(f"module_b_p95_{p}_168h")
        lim = row.get(f"evidence_{p}_limit")
        if lim is not None and lim > 0:
            if (pred is not None and pred > lim) or (p95 is not None and p95 > lim):
                return "REJECT"
    if row.get("module_a_disposition") == "MONITOR":
        return "MONITOR"
    b_codes = str(row.get("module_b_reason_codes") or "")
    if any(c in b_codes for c in ["B_HIGH_FORECAST_DRIFT", "B_WIDE_ENVELOPE", "B_LOT_OUTLIER_24H"]):
        return "MONITOR"
    return "PASS"

if not fusion_df.empty:
    fusion_df["fused_verdict"] = fusion_df.apply(compute_verdict, axis=1)

EVAL_DIR = BASE_DIR / "incoming" / "riddhi" / "SIH26170_ModuleA_FINAL01" / "results"
eval_confusion_df = _load_csv(EVAL_DIR / "20_confusion_matrices.csv")
eval_confusion_meta = _load_json(EVAL_DIR / "20_confusion_matrices.json")
eval_variants_df = _load_csv(EVAL_DIR / "14_per_variant.csv")
eval_operating_points_df = _load_csv(EVAL_DIR / "03_operating_points.csv")

def generate_explanation(row: pd.Series) -> str:
    """Generate engineering explanation based on Module A and Module B reason codes and metrics."""
    parts = []
    
    a_disp = row.get("module_a_disposition")
    a_tier = row.get("module_a_evidence_tier")
    a_codes = str(row.get("module_a_reason_codes") or "").split("|")
    a_param = row.get("module_a_primary_parameter")
    
    if a_tier == "CONFIRMED":
        parts.append(f"CRITICAL: Module A flagged confirmed static specification violation on {a_param or 'measured parameters'}.")
    elif a_disp == "MONITOR":
        parts.append(f"ATTENTION: Module A placed component on MONITOR status (tier: {a_tier}) primarily driven by {a_param or 'statistical drift'}.")
    else:
        parts.append("Module A: No abnormal statistical drift or static spec violations detected up to 168h (PASS).")
        
    for code in a_codes:
        code = code.strip()
        if code == "A_STATIC_LIMIT_EXCEEDED":
            parts.append("Measured parameter exceeded datasheet static limit.")
        elif code == "A_LOT_RELATIVE_DEVIATION":
            parts.append("Component deviates significantly compared to its lot peer distribution.")
        elif code == "A_OVERALL_EXTREME":
            parts.append("Measurements are extreme against variant historical baseline.")
        elif code == "A_ELECTRICAL":
            parts.append("Elevated electrical current anomalies detected.")
        elif code == "A_TEMPORAL":
            parts.append("Unusual parameter trajectory drift observed across burn-in epochs.")

    b_codes = str(row.get("module_b_reason_codes") or "").split("|")
    b_param = row.get("module_b_primary_parameter")
    b_fired = [c.strip() for c in b_codes if c.strip()]
    
    if b_fired:
        parts.append(f"Module B forecast flagged {len(b_fired)} warning indicator(s), driven by {b_param}: {', '.join(b_fired)}.")
    else:
        parts.append(f"Module B: 168h drift forecast within normal operational envelopes (primary drift parameter: {b_param}).")

    b_status = row.get("b_evidence_status")
    if b_status == "SAME_PARAMETER_DRIFT_SUPPORT":
        parts.append("FUSION CORROBORATION: Both Module A and Module B identify the identical parameter as driving anomaly.")
    elif b_status == "NO_MATCHING_DRIFT_CODE":
        parts.append("Note: Module A and Module B flag independent parameters; each provides distinct analytical perspectives.")

    return " ".join(parts)


def get_component(component_id: str) -> Optional[dict]:
    """Retrieve full component record from fusion dataframe."""
    if component_id not in fusion_df.index:
        return None
    return fusion_df.loc[component_id].to_dict()


def get_component_analysis(component_id: str) -> Optional[dict]:
    """Build rich, fully structured analysis view matching frontend expectations."""
    if component_id not in fusion_df.index:
        return None
    
    row = fusion_df.loc[component_id]
    
    # 1. Module A data (13 contract columns)
    ma_keys = [
        "module_a_score", "module_a_disposition", "module_a_primary_parameter",
        "module_a_reason_codes", "module_a_evidence_tier", "module_a_attribution_margin",
        "statistical_score", "spec_exceedance_ratio", "scored_epoch_h",
        "analysis_status", "model_version", "dataset_id"
    ]
    module_a = {k: row.get(k) for k in ma_keys}
    module_a["component_id"] = component_id
    
    # Enrich from Module A 168h file if present
    if 168 in module_a_dfs and component_id in module_a_dfs[168].index:
        a168_row = module_a_dfs[168].loc[component_id]
        for k in ["statistical_score", "spec_exceedance_ratio", "scored_epoch_h", "analysis_status", "model_version", "dataset_id"]:
            if module_a.get(k) is None:
                module_a[k] = a168_row.get(k)

    # Alias standard keys for convenient component access
    module_a["disposition"] = module_a.get("module_a_disposition")
    module_a["score"] = module_a.get("module_a_score")
    module_a["evidence_tier"] = module_a.get("module_a_evidence_tier")
    module_a["primary_parameter"] = module_a.get("module_a_primary_parameter")
    module_a["reason_codes"] = module_a.get("module_a_reason_codes")
    
    # 2. Module B data
    predictions = {}
    evidence_dict = {}
    flat_b = {}
    flat_evidence = {}
    
    for p in PARAMS:
        pred_val = row.get(f"predicted_{p}_168h")
        p95_val = row.get(f"module_b_p95_{p}_168h")
        lim_val = row.get(f"evidence_{p}_limit")
        frac_val = row.get(f"evidence_{p}_pred_frac_of_limit")
        delta_val = row.get(f"evidence_{p}_pred_rel_delta_from_24h")
        lotdev_val = row.get(f"evidence_{p}_lot_rel_dev_24h")
        
        predictions[p] = {
            "predicted_168h": pred_val,
            "p95_168h": p95_val
        }
        evidence_dict[p] = {
            "limit": lim_val,
            "pred_frac_of_limit": frac_val,
            "pred_rel_delta_from_24h": delta_val,
            "lot_rel_dev_24h": lotdev_val
        }
        
        # Include flat keys for direct access
        flat_b[f"predicted_{p}_168h"] = pred_val
        flat_b[f"module_b_p95_{p}_168h"] = p95_val
        flat_evidence[f"evidence_{p}_limit"] = lim_val
        flat_evidence[f"evidence_{p}_pred_frac_of_limit"] = frac_val
        flat_evidence[f"evidence_{p}_pred_rel_delta_from_24h"] = delta_val
        flat_evidence[f"evidence_{p}_lot_rel_dev_24h"] = lotdev_val

    module_b = {
        **flat_b,
        "predictions": predictions,
        "primary_parameter": row.get("module_b_primary_parameter"),
        "reason_codes": row.get("module_b_reason_codes"),
        "evidence": evidence_dict,
    }
    
    b_ev_status = row.get("b_evidence_status")
    explanation_text = generate_explanation(row)
    
    evidence = {
        **flat_evidence,
        "b_evidence_status": b_ev_status,
        "explanation": explanation_text,
    }
    
    # 3. Show actual observed measurements separately from Module B's early-only inputs.
    historical_measurements = []
    history = holdout_measurements_df if component_id in holdout_measurements_df.index else holdout_input_df
    if component_id in history.index:
        h_row = history.loc[component_id]
        for e in [0, 24, 96, 168]:
            if not all(f"{p}_{e}h" in h_row.index for p in PARAMS):
                continue
            meas = {"epoch_h": e}
            for p in PARAMS:
                meas[p] = h_row.get(f"{p}_{e}h")
            historical_measurements.append(meas)
            
    return _clean({
        "component_id": component_id,
        "lot_id": row.get("lot_id"),
        "device_family": row.get("device_family"),
        "device_variant": row.get("device_variant"),
        "fused_verdict": row.get("fused_verdict", "PASS"),
        "fused_disposition": row.get("fused_verdict", "PASS"),
        "module_a": module_a,
        "module_b": module_b,
        "evidence": evidence,
        "b_evidence_status": b_ev_status,
        "historical_measurements": historical_measurements
    })


def search_components(query: str, limit: int = 50) -> List[dict]:
    """Search components by component_id or lot_id."""
    q = str(query).strip().upper()
    if not q:
        return []
    mask = fusion_df["component_id"].str.upper().str.contains(q, na=False, regex=False)
    if "lot_id" in fusion_df.columns:
        mask = mask | fusion_df["lot_id"].str.upper().str.contains(q, na=False, regex=False)
    
    matches = fusion_df[mask].head(limit)
    return matches.to_dict(orient="records")


fusion_dryrun = _load_json(DATA_DIR / "final" / "Fusion_Dryrun.json")


def get_models_info() -> dict:
    return _clean({
        "module_a": module_a_manifest,
        "module_b": module_b_manifest,
        "integration": {
            "status": "VERIFIED_PASS" if fusion_dryrun.get("failures") == 0 else "ATTENTION",
            "module_b_release": fusion_dryrun.get("module_b_release", "ModuleB-FINAL01-RC2"),
            "rows_joined": fusion_dryrun.get("rows_joined", len(fusion_df)),
            "failures": fusion_dryrun.get("failures", 0),
            "checks": fusion_dryrun.get("checks", []),
            "primary_parameter_agreement": fusion_dryrun.get("primary_parameter_agreement_where_both_name_one"),
            "primary_parameter_note": fusion_dryrun.get("primary_parameter_note")
        }
    })


def get_summary_counts() -> dict:
    total = len(fusion_df)
    by_disp = fusion_df["module_a_disposition"].value_counts().to_dict() if "module_a_disposition" in fusion_df.columns else {}
    by_tier = fusion_df["module_a_evidence_tier"].value_counts().to_dict() if "module_a_evidence_tier" in fusion_df.columns else {}
    by_var = fusion_df["device_variant"].value_counts().to_dict() if "device_variant" in fusion_df.columns else {}
    by_verdict = fusion_df["fused_verdict"].value_counts().to_dict() if "fused_verdict" in fusion_df.columns else {}
    
    return _clean({
        "total": total,
        "total_components": total,
        "pass_count": by_verdict.get("PASS", by_disp.get("PASS", 0)),
        "monitor_count": by_verdict.get("MONITOR", by_disp.get("MONITOR", 0)),
        "reject_count": by_verdict.get("REJECT", by_tier.get("CONFIRMED", 0)),
        "confirmed_count": by_tier.get("CONFIRMED", 0),
        "by_fused_verdict": by_verdict,
        "by_disposition": by_disp,
        "by_evidence_tier": by_tier,
        "by_variant": by_var,
        "module_b_summary": {
            "total_predictions": len(module_b_df),
            "forecast_horizon": "168h",
            "input_epochs": ["0h", "24h"],
            "parameters": PARAMS
        },
        "dataset_id": dataset_version.get("dataset_id", "SIH26170-FINAL-01"),
        "dataset_status": dataset_version.get("status", "AUTHORITATIVE_FROZEN_FINAL"),
        "total_lots": 18
    })


def get_evaluation_metrics() -> dict:
    """Return authoritative model evaluation and confusion matrix metrics from final evaluation results."""
    # 1. Headline 168h holdout baseline metrics
    headline = {
        "scope": "module_a_holdout_168h_alert_if_monitor_or_confirmed",
        "description": "Module A only: MONITOR or CONFIRMED counts as an alert at 168h; 13 false positives and 25 missed defects on the synthetic holdout. Not a fusion metric.",
        "tp": 65,
        "tn": 1240,
        "fp": 13,
        "fn": 25,
        "n": 1343,
        "positives": 90,
        "negatives": 1253,
        "flagged": 78,
        "passed": 1265,
        "recall": 65 / 90, # 0.7222
        "precision": 65 / (65 + 13), # 0.8333
        "specificity": 1240 / 1253, # 0.9896
        "fpr": 13 / 1253, # 0.0104
        "accuracy": (65 + 1240) / 1343, # 0.9717
        "f1": (2 * 65) / (2 * 65 + 13 + 25), # 0.7738
        "f2": (5 * 65) / (5 * 65 + 13 + 4 * 25), # 0.7420
    }

    # 2. Evolution across burn-in epochs
    epochs = [
        {"epoch": "0h", "tp": 14, "tn": 1221, "fp": 32, "fn": 76, "recall": 0.1556, "precision": 0.3043, "f1": 0.2059, "accuracy": 0.9196},
        {"epoch": "24h", "tp": 19, "tn": 1221, "fp": 32, "fn": 71, "recall": 0.2111, "precision": 0.3725, "f1": 0.2695, "accuracy": 0.9233},
        {"epoch": "96h", "tp": 32, "tn": 1222, "fp": 31, "fn": 58, "recall": 0.3556, "precision": 0.5079, "f1": 0.4183, "accuracy": 0.9337},
        {"epoch": "168h", "tp": 65, "tn": 1240, "fp": 13, "fn": 25, "recall": 0.7222, "precision": 0.8333, "f1": 0.7738, "accuracy": 0.9717},
    ]

    # 3. Variant breakdown
    variant_records = []
    if not eval_variants_df.empty:
        variant_records = eval_variants_df.to_dict(orient="records")

    # 4. Calibration operating curve points (not holdout sensitivity results)
    operating_points = []
    if not eval_operating_points_df.empty:
        operating_points = eval_operating_points_df.to_dict(orient="records")

    # Retrospective Module B evaluation on the same held-out components.
    # The 96h/168h measurements are used only as outcomes, never as predictors.
    forecast_metrics = []
    if not holdout_measurements_df.empty and not module_b_df.empty:
        common_ids = holdout_measurements_df.index.intersection(module_b_df.index)
        measured = holdout_measurements_df.loc[common_ids]
        forecasts = module_b_df.loc[common_ids]
        units = {"IDDQ": "µA", "Input_Leakage_Current": "µA", "Active_Supply_Current": "µA",
                 "Propagation_Delay": "ns", "Output_Rise_Time": "ns", "Output_Fall_Time": "ns"}
        for parameter in PARAMS:
            actual = pd.to_numeric(measured[f"{parameter}_168h"], errors="coerce")
            predicted = pd.to_numeric(forecasts[f"predicted_{parameter}_168h"], errors="coerce")
            upper = pd.to_numeric(forecasts[f"module_b_p95_{parameter}_168h"], errors="coerce")
            unchanged_24h = pd.to_numeric(measured[f"{parameter}_24h"], errors="coerce")
            valid = actual.notna() & predicted.notna() & upper.notna() & unchanged_24h.notna()
            if not valid.any():
                continue
            actual, predicted, upper, unchanged_24h = (series[valid] for series in (actual, predicted, upper, unchanged_24h))
            forecast_metrics.append({
                "parameter": parameter,
                "unit": units[parameter],
                "n": len(actual),
                "mae": float((actual - predicted).abs().mean()),
                "unchanged_24h_mae": float((actual - unchanged_24h).abs().mean()),
                "upper_coverage": float((actual <= upper).mean()),
                "upper_misses": int((actual > upper).sum()),
            })

    return _clean({
        "baseline": headline,
        "epochs": epochs,
        "by_variant": variant_records,
        "operating_points": operating_points,
        "module_b_forecasts": forecast_metrics,
        "f2_formula": "5 * TP / (5 * TP + FP + 4 * FN)",
        "meta": eval_confusion_meta
    })


def get_lots_summary() -> List[dict]:
    """Aggregate all 18 holdout lots with verified metrics and counts."""
    if "lot_id" not in fusion_df.columns:
        return []
        
    lots = []
    for lot_id, group in fusion_df.groupby("lot_id"):
        var = group["device_variant"].iloc[0] if "device_variant" in group.columns else "UNKNOWN"
        first_id = group["component_id"].min()
        last_id = group["component_id"].max()
        verdicts = group["fused_verdict"].value_counts().to_dict() if "fused_verdict" in group.columns else {}
        tiers = group["module_a_evidence_tier"].value_counts().to_dict() if "module_a_evidence_tier" in group.columns else {}
        
        lots.append({
            "lot_id": lot_id,
            "device_variant": var,
            "component_count": len(group),
            "first_component_id": first_id,
            "last_component_id": last_id,
            "pass_count": verdicts.get("PASS", 0),
            "monitor_count": verdicts.get("MONITOR", 0),
            "reject_count": verdicts.get("REJECT", 0),
            "confirmed_count": tiers.get("CONFIRMED", 0),
            "mean_risk_score": float(group["module_a_score"].mean()) if "module_a_score" in group.columns else 0.0
        })
    return _clean(sorted(lots, key=lambda x: x["lot_id"]))


def get_pipeline_architecture() -> dict:
    """Return the authoritative data lineage and analytical processing pipeline."""
    return _clean({
        "name": "SIH26170 Analytical Architecture",
        "description": "Integrated static screening, prognostic drift modeling, and rule-based decision fusion for semiconductor reliability.",
        "stages": [
            {
                "id": 1,
                "name": "Raw Holdout Partition",
                "source": "incoming/ (18 Whole Lots, 1,343 Parts)",
                "description": "Whole-lot holdout split (LOTSPLIT-05) isolating 6 lots per variant (CMOS_A, CMOS_B, CMOS_C).",
                "status": "FROZEN_BENCHMARK"
            },
            {
                "id": 2,
                "name": "Epoch Partitioning",
                "source": "0h, 24h, 96h, 168h Physical Test Data",
                "description": "Parametric measurements across 6 critical physical channels (IDDQ, Input/Active current, delay, rise/fall times).",
                "status": "INGESTED"
            },
            {
                "id": 3,
                "name": "Module A Screening Scorer",
                "source": "Multi-Epoch Static & Lot Outlier Classifier",
                "description": "Static datasheet limit checking combined with robust lot-relative Mahalanobis outlier scoring across all epochs.",
                "status": "EXECUTED_168H"
            },
            {
                "id": 4,
                "name": "Module B Prognosis Engine",
                "source": "0h-24h Early Burn-in Readings",
                "description": "Linear and exponential trend projections estimating 168h completion values with P95 uncertainty intervals.",
                "status": "EXECUTED_WIDE"
            },
            {
                "id": 5,
                "name": "Decision Fusion Layer",
                "source": "Fusion_Joined_Holdout.csv",
                "description": "Project policy: observed hard-limit breaches or forecast-bound crossings -> REJECT (distinct evidence types); statistical warnings -> MONITOR; otherwise PASS.",
                "status": "SYNTHESIZED"
            },
            {
                "id": 6,
                "name": "FastAPI Analytical Engine",
                "source": "backend/ (Port 8001)",
                "description": "FastAPI serves the stored benchmark outputs and operational measurement records; new records are not yet passed through the frozen models.",
                "status": "ONLINE"
            },
            {
                "id": 7,
                "name": "Interactive Application",
                "source": "frontend/ (Port 5174)",
                "description": "Modern dark-theme analytical console for fleet monitoring, component-level failure diagnostics, and operational screening.",
                "status": "ONLINE"
            }
        ]
    })
