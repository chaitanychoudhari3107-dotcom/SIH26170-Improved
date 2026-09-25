"""The ONLY door to the hidden labels.

Nothing in `modulea/` imports this. Nothing that fits, selects or thresholds
imports this. It takes predictions that are already on disk and returns numbers.

If you find yourself wanting to import it from a fitting path, the thing you want
is not available and the honest move is to say so.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from _common import ROOT  # noqa: F401
from modulea.metrics import confusion

DIAGNOSTIC_COLUMNS = ["defect_behavior", "severity", "primary_parameter",
                      "onset_epoch", "static_fail_target", "static_spec_pass_168h"]


def load_truth(release_root: str | Path, split: str) -> pd.DataFrame:
    truth = pd.read_csv(Path(release_root) / "hidden/Hidden_Ground_Truth.csv")
    truth["split"] = truth["split"].astype(str).str.strip().str.upper()
    truth = truth[truth["split"].eq(split.upper())].copy()
    if truth["component_id"].duplicated().any():
        raise ValueError("duplicate component_id in ground truth")
    return truth


def evaluate(predictions: pd.DataFrame, truth: pd.DataFrame) -> dict:
    if predictions["component_id"].duplicated().any():
        raise ValueError("duplicate component_id in predictions")
    merged = predictions.merge(truth, on="component_id", validate="one_to_one")
    if len(merged) != len(predictions):
        raise ValueError("prediction/label join lost rows; never join on row order")
    y = merged["is_anomalous"].astype(int).to_numpy()
    flag = merged["module_a_disposition"].eq("MONITOR").to_numpy()
    result = {"n": int(len(merged)), "overall": confusion(y, flag)}
    if "module_a_evidence_tier" in merged:
        rows = []
        for tier in ["CONFIRMED", "MONITOR", "PASS"]:
            mask = merged["module_a_evidence_tier"].eq(tier).to_numpy()
            rows.append({"tier": tier, "n": int(mask.sum()),
                         "anomalies": int((mask & (y == 1)).sum()),
                         "normals": int((mask & (y == 0)).sum())})
        result["tiers"] = rows
    breakdowns = {}
    anomalies = merged["is_anomalous"].astype(int).eq(1).to_numpy()
    for column in DIAGNOSTIC_COLUMNS:
        if column not in merged:
            continue
        sub = merged.loc[anomalies].assign(flagged=flag[anomalies])
        table = sub.groupby(column)["flagged"].agg(["count", "sum", "mean"])
        table.columns = ["actual", "detected", "detection_rate"]
        breakdowns[column] = table.reset_index().to_dict("records")
    result["breakdowns"] = breakdowns
    return result
