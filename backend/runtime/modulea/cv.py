"""Validation protocol. Whole lots, always.

Leave-one-lot-out rather than repeated k-fold, for a measured reason: calibration
has 12 lots, and `StratifiedGroupKFold` returns the same partition for every seed
at that size — 4 of 5 seeds gave a byte-identical assignment when this was checked.
Repeats would report a spread of zero and imply a stability nobody measured.
Leave-one-lot-out uses each lot as a test lot once; the uncertainty comes from a
bootstrap over lots instead.
"""
from __future__ import annotations

from typing import Iterator

import numpy as np
import pandas as pd


def leave_one_lot_out(frame: pd.DataFrame) -> Iterator[tuple[str, np.ndarray, np.ndarray]]:
    lots = frame["lot_id"].to_numpy()
    for lot in pd.unique(lots):
        held = lots == lot
        yield str(lot), np.flatnonzero(~held), np.flatnonzero(held)


def forbid_row_split(train_idx: np.ndarray, valid_idx: np.ndarray,
                     lots: np.ndarray) -> None:
    shared = set(lots[train_idx]) & set(lots[valid_idx])
    if shared:
        raise AssertionError(f"a lot appears on both sides of the split: {sorted(shared)[:3]}")
