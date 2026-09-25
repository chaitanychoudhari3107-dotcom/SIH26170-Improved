"""The feature block. Inherited from Better Potential, unchanged in substance.

Six parameters x (4 raw epochs + 6 derived temporal) = 60 features at 168 h.
The derived six are deliberately redundant with each other; that redundancy is a
known property of the score's aggregation and is measured in
`results/04_nested_validation.csv`, not quietly engineered away here.

`build` refuses to read a column later than the epoch it was asked for. That is
the future-data guard at its narrowest point: not a review convention, a raise.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from modulea.constants import EPOCHS, PARAMETERS, future_columns

GROUPS = {
    "IDDQ": "IDDQ",
    "Leakage": "Input_Leakage_Current",
    "ActiveSupply": "Active_Supply_Current",
    "Delay": "Propagation_Delay",
    "Rise": "Output_Rise_Time",
    "Fall": "Output_Fall_Time",
}
TEMPORAL_SUFFIXES = ["abs_0_24", "abs_0_96", "abs_0_168", "abs_24_168",
                     "pct_0_168", "max_step"]


def group_columns(epoch: int = 168) -> dict[str, list[str]]:
    out = {}
    for group, parameter in GROUPS.items():
        raw = [f"{parameter}_{e}h" for e in EPOCHS if e <= epoch]
        out[group] = raw + [f"{group}_{s}" for s in TEMPORAL_SUFFIXES]
    return out


def build(frame: pd.DataFrame, epoch: int = 168) -> pd.DataFrame:
    if epoch != 168:
        raise NotImplementedError(
            "the frozen 168 h feature block needs all four epochs; earlier epochs are "
            "served by modulea.early, which uses its own observed-evidence features"
        )
    forbidden = set(future_columns(epoch))
    out = pd.DataFrame(index=frame.index)
    for group, parameter in GROUPS.items():
        cols = [f"{parameter}_{e}h" for e in EPOCHS]
        if forbidden & set(cols):
            raise AssertionError(f"future column requested at epoch {epoch}: {cols}")
        x0, x24, x96, x168 = (pd.to_numeric(frame[c], errors="raise").astype(float)
                              for c in cols)
        out[cols] = frame[cols].astype(float)
        out[f"{group}_abs_0_24"] = (x24 - x0).abs()
        out[f"{group}_abs_0_96"] = (x96 - x0).abs()
        out[f"{group}_abs_0_168"] = (x168 - x0).abs()
        out[f"{group}_abs_24_168"] = (x168 - x24).abs()
        out[f"{group}_pct_0_168"] = (x168 - x0).abs() / x0.abs().replace(0, np.nan)
        out[f"{group}_max_step"] = pd.concat(
            [(x24 - x0).abs(), (x96 - x24).abs(), (x168 - x96).abs()], axis=1).max(axis=1)

    nonfinite = ~np.isfinite(out.to_numpy(float))
    if nonfinite.any():
        # The only route here is pct_0_168 with a zero 0 h reading, which guards.py
        # already refuses upstream. Reaching this line means a guard was bypassed.
        bad = out.columns[nonfinite.any(axis=0)].tolist()
        raise ValueError(f"non-finite feature values in {bad}; guards were bypassed")
    return out


def feature_names(epoch: int = 168) -> list[str]:
    """The 60 column names, in build order."""
    names: list[str] = []
    for group, parameter in GROUPS.items():
        names += [f"{parameter}_{e}h" for e in EPOCHS]
        names += [f"{group}_{s}" for s in TEMPORAL_SUFFIXES]
    return names
