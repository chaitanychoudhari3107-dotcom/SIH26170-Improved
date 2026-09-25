"""The statistical score: five components, ranked against calibration, weighted.

This is the Better Potential formula. It is kept because, measured properly, it
is the best thing anyone on this problem has produced: at a matched review
workload it equals RC3 exactly and beats RC2 on both axes, and it ranks better
than RC2's combined score (PR AUC 0.8239 against 0.8000). See
`docs/VALIDATION_SUMMARY.md`.

Two things are different here from the inherited implementation:

* the aggregation depths are named parameters rather than slice literals, so the
  configuration is legible and testable;
* the reference scales come from `reference.py`, which refuses a degenerate scale
  instead of turning it into `z = 0`.

Neither changes the numbers on this dataset. `tests/test_equivalence.py` asserts
that against the inherited code.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from modulea import features
from modulea.reference import VariantReference, lot_relative_z

COMPONENT_NAMES = ["electrical", "temporal", "timing", "overall_extreme", "lot_relative"]


@dataclass(frozen=True)
class Depths:
    """How many of the largest deviations each component averages."""
    group: int = 3
    electrical: int = 6
    temporal: int = 6
    overall: int = 8
    lot: int = 8


def _topk_mean(values: np.ndarray, k: int) -> np.ndarray:
    k = max(1, min(int(k), values.shape[1]))
    return np.sort(values, axis=1)[:, -k:].mean(axis=1)


class StatisticalCore:
    """Fitted on train (variant references) plus calibration (rank references)."""

    def __init__(self, depths: Depths | None = None) -> None:
        self.depths = depths or Depths()
        self.reference: VariantReference | None = None
        self.rank_reference: dict[str, np.ndarray] = {}
        self.group_columns = features.group_columns(168)

    # -- fitting ---------------------------------------------------------
    def fit_reference(self, train: pd.DataFrame) -> "StatisticalCore":
        self.reference = VariantReference.fit(train, features.build(train, 168))
        return self

    def fit_ranks(self, calibration: pd.DataFrame) -> "StatisticalCore":
        components = self.components(calibration)
        self.rank_reference = {c: np.sort(components[c].to_numpy(float))
                               for c in COMPONENT_NAMES}
        return self

    def fit(self, train: pd.DataFrame, calibration: pd.DataFrame) -> "StatisticalCore":
        return self.fit_reference(train).fit_ranks(calibration)

    # -- scoring ---------------------------------------------------------
    def components(self, frame: pd.DataFrame) -> pd.DataFrame:
        if self.reference is None:
            raise RuntimeError("fit_reference must run before components")
        d = self.depths
        block = features.build(frame, 168)
        z = self.reference.z(frame, block)

        group_scores = pd.DataFrame(index=frame.index)
        for group, cols in self.group_columns.items():
            group_scores[group] = _topk_mean(z[cols].to_numpy(float), d.group)

        electrical_cols = sum([self.group_columns[g]
                               for g in ["IDDQ", "Leakage", "ActiveSupply"]], [])
        temporal_cols = [c for cols in self.group_columns.values() for c in cols
                         if "_abs_" in c or "_pct_" in c or c.endswith("_max_step")]

        lot_z = lot_relative_z(frame, block)
        return pd.DataFrame({
            "electrical": _topk_mean(z[electrical_cols].to_numpy(float), d.electrical),
            "temporal": _topk_mean(z[temporal_cols].to_numpy(float), d.temporal),
            "timing": group_scores[["Delay", "Rise", "Fall"]].mean(axis=1).to_numpy(),
            "overall_extreme": _topk_mean(z.to_numpy(float), d.overall),
            "lot_relative": _topk_mean(lot_z.to_numpy(float), d.lot),
        }, index=frame.index)

    def ranks(self, frame: pd.DataFrame) -> pd.DataFrame:
        if not self.rank_reference:
            raise RuntimeError("fit_ranks must run before ranks")
        components = self.components(frame)
        out = pd.DataFrame(index=frame.index)
        for name, reference in self.rank_reference.items():
            out[name] = np.searchsorted(reference, components[name].to_numpy(float),
                                        side="right") / len(reference)
        return out

    def score(self, frame: pd.DataFrame, weights: dict[str, float]) -> np.ndarray:
        check_weights(weights)
        ranked = self.ranks(frame)
        total = np.zeros(len(ranked))
        for name, weight in weights.items():
            total += weight * ranked[name].to_numpy(float)
        return total

    def state(self) -> dict:
        return {"depths": asdict(self.depths),
                "variant_median": {k: v.to_dict() for k, v in self.reference.median.items()},
                "variant_scale": {k: v.to_dict() for k, v in self.reference.scale.items()},
                "variant_method": {k: v.to_dict() for k, v in self.reference.method.items()},
                "rank_reference": {k: v.tolist() for k, v in self.rank_reference.items()}}

    @classmethod
    def from_state(cls, state: dict) -> "StatisticalCore":
        core = cls(Depths(**state["depths"]))
        reference = VariantReference()
        for variant in state["variant_median"]:
            reference.median[variant] = pd.Series(state["variant_median"][variant])
            reference.scale[variant] = pd.Series(state["variant_scale"][variant])
            reference.method[variant] = pd.Series(state["variant_method"][variant])
        core.reference = reference
        core.rank_reference = {k: np.asarray(v, dtype=float)
                               for k, v in state["rank_reference"].items()}
        return core


def check_weights(weights: dict[str, float]) -> None:
    if set(weights) != set(COMPONENT_NAMES):
        raise ValueError(f"weights must cover exactly {COMPONENT_NAMES}, got {sorted(weights)}")
    if any(w < 0 for w in weights.values()):
        raise ValueError("negative component weight")
    total = sum(weights.values())
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"weights must sum to 1, got {total}")


def contributing_components(weights: dict[str, float], ranked_row: pd.Series,
                            floor: float = 0.75) -> list[str]:
    """Components that are both elevated and actually carry weight.

    Intake defect C4: the inherited reason code ranked all five components and
    could name `A_ELECTRICAL` on a component whose electrical weight is 0.0, so
    the stated reason contributed literally nothing to the score that raised the
    flag. A component with zero weight is not a reason.
    """
    return [name for name in COMPONENT_NAMES
            if weights.get(name, 0.0) > 0 and float(ranked_row[name]) >= floor]
