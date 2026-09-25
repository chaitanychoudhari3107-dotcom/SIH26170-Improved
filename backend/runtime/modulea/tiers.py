"""One monotone score, and the tier bands carved out of it.

Intake defect C1: RC2 emitted `module_a_score = max(core_score, residual_score)`,
mixing a weighted rank with a logistic probability while the decision used two
separate thresholds. In its shipped holdout file, 54 rows dispositioned PASS scored
*above* the weakest REVIEW row and 24 REVIEW rows scored above the weakest
HIGH_CONFIDENCE row. Fusion thresholding that score would not have reproduced
Module A's own decisions.

Here the score is one number with a reserved band:

    [0.00, 0.90)   statistical evidence          0.90 * statistical rank score
    [0.90, 1.00]   a datasheet limit is exceeded 0.90 + 0.10 * how far past it

So `module_a_score >= CONFIRMED_FLOOR` means out of specification, and
`module_a_score >= 0.90 * operating_threshold` means MONITOR — one threshold on
one column, reproducing Module A's decision exactly. `tests/test_tiers.py`
asserts the monotonicity rather than trusting this docstring.
"""
from __future__ import annotations

import numpy as np

from modulea.constants import CONFIRMED_BAND, STATISTICAL_BAND

CONFIRMED_FLOOR = CONFIRMED_BAND[0]
STATISTICAL_CEILING = STATISTICAL_BAND[1]
# A part 50% past its datasheet maximum saturates the confirmed band. The exact
# shape inside [0.90, 1.00] carries no decision — everything in the band is already
# out of specification — it only orders the confirmed parts for a reviewer's queue.
FULL_EXCEEDANCE = 0.5


# The highest-ranked component in a batch has an empirical rank of exactly 1.0, which
# maps to exactly CONFIRMED_FLOOR. That would put a component into the reserved
# out-of-specification band on statistical evidence alone, and `validate_output` would
# correctly refuse to emit the frame — turning the top-ranked part of any batch into a
# serving failure. The statistical band is therefore closed just below the floor.
# Found by tests/test_score_semantics.py during pre-integration hardening; it changed
# no emitted value on this release, because all eight holdout components at rank 1.0
# are also datasheet violations and score from the confirmed branch. See
# PROVENANCE_ADDENDUM.json.
STATISTICAL_MAX = float(np.nextafter(CONFIRMED_BAND[0], 0.0))


def compose_score(statistical: np.ndarray, violated: np.ndarray,
                  exceedance_ratio: np.ndarray) -> np.ndarray:
    statistical = np.asarray(statistical, dtype=float)
    if statistical.min() < 0 or statistical.max() > 1:
        raise ValueError("statistical score must lie in [0, 1]")
    score = np.minimum(STATISTICAL_CEILING * statistical, STATISTICAL_MAX)
    over = np.clip((np.asarray(exceedance_ratio, float) - 1.0) / FULL_EXCEEDANCE, 0.0, 1.0)
    confirmed = CONFIRMED_FLOOR + (1.0 - CONFIRMED_FLOOR) * over
    return np.where(np.asarray(violated, bool), confirmed, score)


def monitor_floor(operating_threshold: float) -> float:
    """The single value a downstream consumer thresholds `module_a_score` at."""
    if not 0.0 < operating_threshold <= 1.0:
        raise ValueError("operating threshold must lie in (0, 1]")
    return STATISTICAL_CEILING * operating_threshold


def assign(score: np.ndarray, violated: np.ndarray,
           operating_threshold: float) -> tuple[np.ndarray, np.ndarray]:
    """Returns (disposition, evidence_tier)."""
    score = np.asarray(score, dtype=float)
    violated = np.asarray(violated, dtype=bool)
    floor = monitor_floor(operating_threshold)
    monitor = violated | (score >= floor)
    disposition = np.where(monitor, "MONITOR", "PASS")
    tier = np.where(violated, "CONFIRMED", np.where(monitor, "MONITOR", "PASS"))
    return disposition, tier


def check_monotone(score: np.ndarray, disposition: np.ndarray,
                   operating_threshold: float) -> None:
    """Refuse to emit a frame whose score disagrees with its own disposition."""
    score = np.asarray(score, dtype=float)
    monitor = np.asarray(disposition) == "MONITOR"
    if monitor.any() and (~monitor).any():
        worst_monitor = score[monitor].min()
        best_pass = score[~monitor].max()
        if best_pass >= worst_monitor:
            raise AssertionError(
                f"score is not monotone with disposition: a PASS row scores "
                f"{best_pass:.6f} while the weakest MONITOR scores {worst_monitor:.6f}")
    floor = monitor_floor(operating_threshold)
    implied = score >= floor
    if not np.array_equal(implied, monitor):
        raise AssertionError(
            "thresholding module_a_score at the published floor does not reproduce "
            "module_a_disposition")
