"""The output frame, and the assertions that stop a malformed one leaving."""
from __future__ import annotations

import numpy as np
import pandas as pd

from modulea.constants import CONTRACT_FIELDS, DIAGNOSTIC_FIELDS, DISPOSITIONS
from modulea import tiers


def build_output(component_id, module_a_score, disposition, primary_parameter,
                 reason_codes, evidence_tier, attribution_margin, statistical_score,
                 spec_exceedance_ratio, epoch, analysis_status, model_version,
                 dataset_id) -> pd.DataFrame:
    frame = pd.DataFrame({
        "component_id": np.asarray(component_id),
        "module_a_score": np.asarray(module_a_score, float),
        "module_a_disposition": np.asarray(disposition),
        "module_a_primary_parameter": np.asarray(primary_parameter),
        "module_a_reason_codes": np.asarray(reason_codes),
        "module_a_evidence_tier": np.asarray(evidence_tier),
        "module_a_attribution_margin": np.asarray(attribution_margin, float),
        "statistical_score": np.asarray(statistical_score, float),
        "spec_exceedance_ratio": np.asarray(spec_exceedance_ratio, float),
        "scored_epoch_h": int(epoch),
        "analysis_status": analysis_status,
        "model_version": model_version,
        "dataset_id": dataset_id,
    })
    return frame[CONTRACT_FIELDS + DIAGNOSTIC_FIELDS]


def validate_output(frame: pd.DataFrame, operating_threshold: float) -> None:
    missing = [c for c in CONTRACT_FIELDS if c not in frame.columns]
    if missing:
        raise AssertionError(f"contract fields missing from output: {missing}")
    if list(frame.columns[:len(CONTRACT_FIELDS)]) != CONTRACT_FIELDS:
        raise AssertionError("the five contract fields must come first, in order")
    if frame["component_id"].duplicated().any():
        raise AssertionError("duplicate component_id in output")
    bad = sorted(set(frame["module_a_disposition"]) - set(DISPOSITIONS))
    if bad:
        raise AssertionError(
            f"Module A emitted {bad}; it may only emit {DISPOSITIONS}. The final "
            "PASS / MONITOR / REJECT belongs to fusion.")
    score = frame["module_a_score"].to_numpy(float)
    if not np.isfinite(score).all():
        raise AssertionError("non-finite module_a_score")
    if score.min() < 0 or score.max() > 1:
        raise AssertionError("module_a_score must lie in [0, 1]")
    tiers.check_monotone(score, frame["module_a_disposition"].to_numpy(),
                         operating_threshold)
    confirmed = frame["module_a_evidence_tier"].eq("CONFIRMED").to_numpy()
    if confirmed.any():
        if score[confirmed].min() < tiers.CONFIRMED_FLOOR:
            raise AssertionError("a CONFIRMED row scores below the confirmed band")
        if (~confirmed).any() and score[~confirmed].max() >= tiers.CONFIRMED_FLOOR:
            raise AssertionError("a non-CONFIRMED row scores inside the confirmed band")
        if not frame.loc[confirmed, "module_a_disposition"].eq("MONITOR").all():
            raise AssertionError("a CONFIRMED row is not dispositioned MONITOR")
