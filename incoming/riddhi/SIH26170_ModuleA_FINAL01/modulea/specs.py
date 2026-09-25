"""Datasheet static limits — the one piece of evidence that is not statistical.

`Device_Specs.csv` gives a `static_spec_max` for 11 of 18 variant x parameter
cells. The other seven are empty and stay empty: Active_Supply_Current has no
datasheet limit for any variant, and Output_Rise_Time / Output_Fall_Time have
none for CMOS_B or CMOS_C. A limit is never interpolated, never borrowed from a
neighbouring variant, and never derived from the data. Where there is no limit,
the limit-based rule simply does not fire.

Why this matters more than it looks: a component exceeding its own datasheet
maximum is out of specification by definition. That is not a threshold anyone
fitted, so it cannot be overfitted, and it does not degrade on an unseen lot.
It is the only witness in Module A that is independent of the lot-relative
statistics, and it is what makes the CONFIRMED tier defensible.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from modulea.constants import PARAMETERS

REQUIRED_COLUMNS = {"device_variant", "parameter", "static_spec_max", "limit_provenance"}


class SpecLimits:
    def __init__(self, table: pd.DataFrame) -> None:
        self._limit = table

    @classmethod
    def load(cls, path: str | Path) -> "SpecLimits":
        raw = pd.read_csv(path)
        missing = REQUIRED_COLUMNS - set(raw.columns)
        if missing:
            raise ValueError(f"Device_Specs is missing {sorted(missing)}")
        unknown = set(raw["parameter"]) - set(PARAMETERS)
        if unknown:
            raise ValueError(f"Device_Specs names unknown parameters: {sorted(unknown)}")
        table = raw.pivot_table(index="device_variant", columns="parameter",
                                values="static_spec_max", dropna=False)
        return cls(table.reindex(columns=PARAMETERS))

    def limit(self, variant: str, parameter: str) -> float:
        if variant not in self._limit.index:
            raise ValueError(f"no Device_Specs row for variant {variant}")
        return float(self._limit.loc[variant, parameter])

    def coverage(self) -> pd.DataFrame:
        present = self._limit.notna()
        return pd.DataFrame({
            "cells_total": [int(present.size)],
            "cells_with_limit": [int(present.to_numpy().sum())],
            "cells_without_limit": [int((~present).to_numpy().sum())],
        })

    def exceedance(self, frame: pd.DataFrame, epoch: int) -> pd.DataFrame:
        """Per-parameter ratio value / limit at `epoch`. NaN where no limit exists.

        A ratio above 1.0 means the part is out of specification.
        """
        out = pd.DataFrame(index=frame.index, columns=PARAMETERS, dtype=float)
        for parameter in PARAMETERS:
            limits = frame["device_variant"].map(
                self._limit[parameter]).to_numpy(float)
            values = pd.to_numeric(frame[f"{parameter}_{epoch}h"],
                                   errors="raise").to_numpy(float)
            with np.errstate(invalid="ignore", divide="ignore"):
                ratio = np.where(np.isfinite(limits), values / limits, np.nan)
            out[parameter] = ratio
        return out

    def violation(self, frame: pd.DataFrame, epoch: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Returns (violated, worst_ratio, worst_parameter)."""
        ratios = self.exceedance(frame, epoch)
        values = ratios.to_numpy(float)
        if np.isnan(values).all():
            return (np.zeros(len(frame), bool), np.zeros(len(frame)),
                    np.array([""] * len(frame), dtype=object))
        worst_index = np.nanargmax(np.where(np.isnan(values), -np.inf, values), axis=1)
        worst_ratio = values[np.arange(len(frame)), worst_index]
        worst_ratio = np.where(np.isfinite(worst_ratio), worst_ratio, 0.0)
        worst_parameter = np.array(PARAMETERS, dtype=object)[worst_index]
        return worst_ratio > 1.0, worst_ratio, worst_parameter
