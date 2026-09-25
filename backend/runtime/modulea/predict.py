"""Inference. Reads a batch, returns the contract frame. No labels anywhere."""
from __future__ import annotations

import numpy as np
import pandas as pd

from modulea import config, contract, evidence, reason_codes, tiers
from modulea.constants import EPOCHS
from modulea.evidence import observed_evidence_score
from modulea.guards import validate_scoring_frame
from modulea.scoring import StatisticalCore
from modulea.specs import SpecLimits


class ModuleA:
    """A fitted, frozen Module A. Construct it from an artifact, not by hand."""

    def __init__(self, core: StatisticalCore, specs: SpecLimits, weights: dict,
                 operating_threshold: float, early_thresholds: dict,
                 expected_lot_sizes: dict, model_version: str, dataset_id: str) -> None:
        self.core = core
        self.specs = specs
        self.weights = weights
        self.operating_threshold = float(operating_threshold)
        self.early_thresholds = {int(k): float(v) for k, v in early_thresholds.items()}
        self.expected_lot_sizes = dict(expected_lot_sizes)
        self.model_version = model_version
        self.dataset_id = dataset_id

    @property
    def monitor_floor(self) -> float:
        return tiers.monitor_floor(self.operating_threshold)

    def predict(self, frame: pd.DataFrame, epoch: int = 168) -> pd.DataFrame:
        if epoch not in EPOCHS:
            raise ValueError(f"epoch must be one of {EPOCHS}")
        clean = validate_scoring_frame(
            frame, epoch, f"batch@{epoch}h", self.core.reference.variants,
            self.expected_lot_sizes)

        violated, ratio, worst_parameter = self.specs.violation(clean, epoch)

        per_parameter = evidence.per_parameter(clean, epoch, self.core.reference)
        primary, margin = reason_codes.primary_parameter(per_parameter)

        if epoch == 168:
            ranked = self.core.ranks(clean)
            statistical = self.core.score(clean, self.weights)
            threshold = self.operating_threshold
            status = "COMPLETE_4_EPOCH"
        else:
            # No 168 h feature exists yet, so the statistical view is the observed
            # per-parameter evidence and nothing more. It is NOT a forecast, and a
            # defect that has not begun is not visible here by construction.
            ranked = pd.DataFrame(0.0, index=clean.index,
                                  columns=list(self.weights))
            statistical = observed_evidence_score(per_parameter)
            if epoch not in self.early_thresholds:
                raise RuntimeError(f"no fitted early threshold for {epoch} h")
            threshold = self.early_thresholds[epoch]
            status = f"PARTIAL_{len([e for e in EPOCHS if e <= epoch])}_EPOCH"

        score = tiers.compose_score(statistical, violated, ratio)
        disposition, tier = tiers.assign(score, violated, threshold)
        codes = reason_codes.build(ranked, self.weights,
                                   np.asarray(disposition) == "MONITOR",
                                   violated, worst_parameter)
        # Below the operating threshold the primary parameter is noise being
        # ranked; do not publish an attribution nobody should act on.
        monitor = np.asarray(disposition) == "MONITOR"
        primary = np.where(monitor, primary, "")
        margin = np.where(monitor, margin, np.nan)

        out = contract.build_output(
            clean["component_id"].to_numpy(), score, disposition, primary, codes,
            tier, margin, statistical, np.where(violated, ratio, np.nan), epoch,
            status, self.model_version, self.dataset_id)
        contract.validate_output(out, threshold)
        return out
