import numpy as np
import pytest

from modulea import tiers


def test_confirmed_always_outranks_statistical():
    score = tiers.compose_score(np.array([0.999999, 0.5]), np.array([False, True]),
                                np.array([0.0, 1.0001]))
    assert score[1] > score[0]
    assert score[1] >= tiers.CONFIRMED_FLOOR
    assert score[0] < tiers.CONFIRMED_FLOOR


def test_one_threshold_reproduces_the_disposition():
    rng = np.random.default_rng(0)
    statistical = rng.random(500)
    violated = rng.random(500) < 0.02
    ratio = np.where(violated, 1 + rng.random(500), 0.0)
    score = tiers.compose_score(statistical, violated, ratio)
    disposition, _ = tiers.assign(score, violated, 0.9)
    tiers.check_monotone(score, disposition, 0.9)
    floor = tiers.monitor_floor(0.9)
    assert np.array_equal(score >= floor, disposition == "MONITOR")


def test_the_rc2_defect_is_caught():
    """RC2 shipped a score where 54 PASS rows outranked the weakest REVIEW row.
    check_monotone must refuse a frame like that."""
    score = np.array([0.95, 0.80, 0.99])
    disposition = np.array(["MONITOR", "MONITOR", "PASS"])
    with pytest.raises(AssertionError, match="not monotone"):
        tiers.check_monotone(score, disposition, 0.5)


def test_statistical_score_out_of_range_is_refused():
    with pytest.raises(ValueError):
        tiers.compose_score(np.array([1.5]), np.array([False]), np.array([0.0]))
