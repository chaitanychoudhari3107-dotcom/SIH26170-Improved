"""Why a component was flagged, in terms that survive being questioned.

Rules:

* a component with zero weight is never named as a reason (intake defect C4);
* the primary parameter is reported with the margin between it and the runner-up,
  because two reasonable attribution methods on the same 73 components agreed only
  81% of the time (intake defect C5) — it is evidence for a reviewer, not a root
  cause;
* a limit-based code fires only where `Device_Specs` actually gives a limit.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from modulea.constants import PARAMETERS
from modulea.scoring import COMPONENT_NAMES

CODES = {
    "A_STATIC_LIMIT_EXCEEDED": "measured value exceeds the datasheet static maximum",
    "A_LOT_RELATIVE_DEVIATION": "deviates from the other components in its own lot",
    "A_OVERALL_EXTREME": "extreme against the variant's historical reference",
    "A_ELECTRICAL": "electrical-group deviation",
    "A_TEMPORAL": "change-over-time deviation",
    "A_TIMING": "timing-group deviation",
    "A_OK": "no evidence above the operating threshold",
}
COMPONENT_TO_CODE = {
    "lot_relative": "A_LOT_RELATIVE_DEVIATION",
    "overall_extreme": "A_OVERALL_EXTREME",
    "electrical": "A_ELECTRICAL",
    "temporal": "A_TEMPORAL",
    "timing": "A_TIMING",
}
ELEVATED = 0.75


def build(ranked: pd.DataFrame, weights: dict[str, float], monitor: np.ndarray,
          violated: np.ndarray, worst_parameter: np.ndarray) -> np.ndarray:
    weighted = [c for c in COMPONENT_NAMES if weights.get(c, 0.0) > 0]
    values = ranked[weighted].to_numpy(float) if weighted else np.zeros((len(ranked), 0))
    codes = []
    for i in range(len(ranked)):
        parts = []
        if violated[i]:
            parts.append(f"A_STATIC_LIMIT_EXCEEDED:{worst_parameter[i]}")
        if monitor[i] and weighted:
            order = np.argsort(-values[i])
            elevated = [weighted[j] for j in order if values[i, j] >= ELEVATED]
            if not elevated:
                elevated = [weighted[int(order[0])]]
            parts += [COMPONENT_TO_CODE[name] for name in elevated[:2]]
        if not parts:
            parts = ["A_OK"]
        codes.append("|".join(dict.fromkeys(parts)))
    return np.array(codes, dtype=object)


def primary_parameter(evidence: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Strongest parameter and the gap to the runner-up.

    A margin near zero means the attribution is a coin toss between two parameters
    and should be shown to a reviewer as such.
    """
    if list(evidence.columns) != PARAMETERS:
        raise ValueError("evidence columns must be the six parameters in order")
    values = evidence.to_numpy(float)
    order = np.argsort(-values, axis=1)
    best = order[:, 0]
    runner_up = order[:, 1]
    rows = np.arange(len(values))
    margin = values[rows, best] - values[rows, runner_up]
    return np.array(PARAMETERS, dtype=object)[best], margin
