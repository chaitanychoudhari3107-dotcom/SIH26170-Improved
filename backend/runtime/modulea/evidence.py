"""Per-parameter evidence, shared by attribution and by the early-epoch path.

For each parameter, the strongest robust deviation observed so far — against the
component's own lot and against the variant's historical reference. This is the
quantity a reviewer can act on: 'Input_Leakage_Current is 4.2 robust deviations
above its lot', not 'the score was 0.94'.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from modulea.constants import EPOCHS, PARAMETERS
from modulea.reference import DegenerateScaleError, robust_scale


def _lot_z(frame: pd.DataFrame, column: str) -> np.ndarray:
    out = np.zeros(len(frame))
    for _, idx in frame.groupby("lot_id").groups.items():
        pos = frame.index.get_indexer(idx)
        values = pd.to_numeric(frame.loc[idx, column], errors="raise").to_numpy(float)
        try:
            median, scale, _ = robust_scale(values)
        except DegenerateScaleError:
            continue                      # every part identical: nobody deviates
        out[pos] = np.abs((values - median) / scale)
    return out


def per_parameter(frame: pd.DataFrame, epoch: int,
                  variant_reference=None) -> pd.DataFrame:
    """Largest |z| per parameter across the epochs observed so far."""
    frame = frame.reset_index(drop=True)
    observed = [e for e in EPOCHS if e <= epoch]
    out = pd.DataFrame(index=frame.index, columns=PARAMETERS, dtype=float)
    for parameter in PARAMETERS:
        stack = []
        for e in observed:
            column = f"{parameter}_{e}h"
            stack.append(_lot_z(frame, column))
            if variant_reference is not None and column in next(
                    iter(variant_reference.median.values())).index:
                vz = np.zeros(len(frame))
                for variant, idx in frame.groupby("device_variant").groups.items():
                    pos = frame.index.get_indexer(idx)
                    median = variant_reference.median[variant][column]
                    scale = variant_reference.scale[variant][column]
                    values = frame.loc[idx, column].to_numpy(float)
                    vz[pos] = np.abs((values - median) / scale)
                stack.append(vz)
        out[parameter] = np.max(np.column_stack(stack), axis=1)
    return out


def observed_evidence_score(evidence: pd.DataFrame) -> np.ndarray:
    """A bounded ranking statistic for the early epochs.

    Deliberately not a probability. It orders components by how strong their
    strongest observed deviation is; the mapping through 1 - exp(-z/3) only puts
    it on [0, 1) so the same tier machinery can consume it.
    """
    strongest = evidence.to_numpy(float).max(axis=1)
    return 1.0 - np.exp(-strongest / 3.0)
