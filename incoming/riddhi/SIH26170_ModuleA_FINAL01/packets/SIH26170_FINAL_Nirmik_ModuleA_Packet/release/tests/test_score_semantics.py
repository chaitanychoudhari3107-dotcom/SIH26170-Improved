"""Properties of module_a_score that the integration note states."""
import numpy as np
import pytest

from modulea import tiers
from modulea.constants import CONFIRMED_BAND, STATISTICAL_BAND


def test_the_two_bands_do_not_overlap():
    assert STATISTICAL_BAND[1] == CONFIRMED_BAND[0]
    assert CONFIRMED_BAND[1] == 1.0


def test_the_statistical_band_can_never_reach_the_confirmed_floor():
    """Even a perfect statistical score stays below an out-of-spec part."""
    score = tiers.compose_score(np.array([1.0]), np.array([False]), np.array([0.0]))
    assert score[0] < tiers.CONFIRMED_FLOOR


def test_score_is_monotone_in_the_statistical_input():
    statistical = np.linspace(0, 1, 200)
    score = tiers.compose_score(statistical, np.zeros(200, bool), np.zeros(200))
    assert np.all(np.diff(score) >= 0)


def test_confirmed_score_rises_with_exceedance():
    ratio = np.array([1.001, 1.1, 1.25, 1.5, 3.0])
    score = tiers.compose_score(np.zeros(5), np.ones(5, bool), ratio)
    assert np.all(np.diff(score) >= 0)
    assert score[-1] == 1.0                      # saturates, never exceeds 1


def test_monitor_floor_scales_with_the_threshold():
    assert tiers.monitor_floor(1.0) == STATISTICAL_BAND[1]
    assert tiers.monitor_floor(0.5) == STATISTICAL_BAND[1] * 0.5


@pytest.mark.parametrize("bad", [0.0, -0.1, 1.5])
def test_an_impossible_operating_threshold_is_refused(bad):
    with pytest.raises(ValueError):
        tiers.monitor_floor(bad)


def test_check_monotone_accepts_a_well_formed_frame():
    score = np.array([0.1, 0.5, 0.9, 0.95])
    disposition = np.array(["PASS", "PASS", "MONITOR", "MONITOR"])
    tiers.check_monotone(score, disposition, 0.9)


def test_check_monotone_catches_a_floor_that_does_not_reproduce_the_decision():
    score = np.array([0.1, 0.89, 0.91])
    disposition = np.array(["PASS", "MONITOR", "MONITOR"])
    with pytest.raises(AssertionError, match="does not reproduce"):
        tiers.check_monotone(score, disposition, 0.99)
