"""Robust reference scales, with degenerate cases refused rather than absorbed.

Intake defect C3, in the inherited Better Potential code:

    scale = 1.4826 * MAD
    scale = scale.replace(0, np.nan)
    z = (x - median).abs().div(scale).fillna(0)

A feature whose reference MAD is zero — a constant, a saturated sensor, a coarsely
quantised reading — comes out as ``z = 0`` for every component of that variant.
The most degenerate reference produces the most reassuring answer, silently. On
SIH26170-FINAL-01 no feature is currently in that state, so the defect is dormant
rather than active, but it is still wrong and a different lot mix will wake it.

Here a degenerate MAD falls down a declared ladder instead, and which rung was
used is recorded on the reference so it can be reported and tested:

    1.4826 * MAD   ->   IQR / 1.349   ->   standard deviation   ->   REFUSE

Refusing means raising. It never means scoring the feature as normal.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

MAD_TO_SIGMA = 1.4826
IQR_TO_SIGMA = 1.349
DEGENERATE = 1e-12


class DegenerateScaleError(ValueError):
    """Every fallback was also degenerate. The caller must decide, not this module."""


def robust_scale(values: np.ndarray) -> tuple[float, float, str]:
    """Return (median, scale, method). Raises if no rung of the ladder works."""
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        raise DegenerateScaleError("no finite values to build a reference from")
    median = float(np.median(arr))

    scale = MAD_TO_SIGMA * float(np.median(np.abs(arr - median)))
    if np.isfinite(scale) and scale > DEGENERATE:
        return median, scale, "MAD"

    q25, q75 = np.quantile(arr, [0.25, 0.75])
    scale = float(q75 - q25) / IQR_TO_SIGMA
    if np.isfinite(scale) and scale > DEGENERATE:
        return median, scale, "IQR"

    if arr.size > 1:
        scale = float(np.std(arr, ddof=1))
        if np.isfinite(scale) and scale > DEGENERATE:
            return median, scale, "STD"

    raise DegenerateScaleError(
        "reference is constant to within 1e-12; no dispersion estimate is available. "
        "This feature carries no information and must be excluded explicitly, not "
        "scored as normal."
    )


@dataclass
class VariantReference:
    """Per-variant median and scale for every feature, fitted on the train split.

    A note on contamination, because the handoff describes the train split as a
    'normal-reference split' and it is not: the hidden ground truth records 180
    anomalies among its 3,151 components, about 5.7%. Median and MAD have a
    breakdown point of 50%, so a 5.7% contamination does not move them materially,
    and this reference is fitted without labels in any case. The point is that the
    contamination is disclosed and bounded, not that it is absent.
    """

    median: dict[str, pd.Series] = field(default_factory=dict)
    scale: dict[str, pd.Series] = field(default_factory=dict)
    method: dict[str, pd.Series] = field(default_factory=dict)

    @classmethod
    def fit(cls, frame: pd.DataFrame, features: pd.DataFrame) -> "VariantReference":
        ref = cls()
        for variant, idx in frame.groupby("device_variant").groups.items():
            block = features.loc[idx]
            medians, scales, methods = {}, {}, {}
            for column in block.columns:
                medians[column], scales[column], methods[column] = robust_scale(
                    block[column].to_numpy(float))
            ref.median[variant] = pd.Series(medians)
            ref.scale[variant] = pd.Series(scales)
            ref.method[variant] = pd.Series(methods)
        return ref

    @property
    def variants(self) -> list[str]:
        return sorted(self.median)

    def z(self, frame: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        unknown = sorted(set(frame["device_variant"]) - set(self.median))
        if unknown:
            raise ValueError(
                f"unknown device_variant {unknown}: there is no fitted reference for it, "
                "and scoring it against another variant's reference would be a guess"
            )
        out = pd.DataFrame(np.nan, index=features.index, columns=features.columns)
        for variant, idx in frame.groupby("device_variant").groups.items():
            out.loc[idx] = (
                (features.loc[idx] - self.median[variant])
                .abs()
                .div(self.scale[variant])
                .to_numpy()
            )
        if not np.isfinite(out.to_numpy()).all():
            raise ValueError("non-finite z value produced; refusing to continue")
        return out

    def fallback_summary(self) -> pd.DataFrame:
        rows = []
        for variant in self.variants:
            counts = self.method[variant].value_counts()
            rows.append({"device_variant": variant,
                         "features": int(len(self.method[variant])),
                         "MAD": int(counts.get("MAD", 0)),
                         "IQR": int(counts.get("IQR", 0)),
                         "STD": int(counts.get("STD", 0))})
        return pd.DataFrame(rows)


def lot_relative_z(frame: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    """|z| of each feature against the component's own lot.

    Unsupervised and computed on the arriving batch, which is permitted only when
    the lot is complete — `guards.require_complete_lots` enforces that separately.
    A lot whose feature is constant falls down the same ladder; if every rung is
    degenerate the feature contributes zero *for that lot only*, and that is
    recorded rather than silent.
    """
    out = pd.DataFrame(0.0, index=features.index, columns=features.columns)
    for _, idx in frame.groupby(["device_variant", "lot_id"]).groups.items():
        block = features.loc[idx]
        for column in block.columns:
            values = block[column].to_numpy(float)
            try:
                median, scale, _ = robust_scale(values)
            except DegenerateScaleError:
                # Every component in this lot has the same value for this feature.
                # No component is deviant relative to the others, so zero is the
                # correct answer here — unlike the variant reference, where zero
                # would have meant 'cannot tell'.
                continue
            out.loc[idx, column] = np.abs((values - median) / scale)
    return out
