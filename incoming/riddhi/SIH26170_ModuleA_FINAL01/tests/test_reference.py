import numpy as np
import pytest

from modulea.reference import DegenerateScaleError, robust_scale


def test_mad_is_preferred():
    assert robust_scale(np.array([1., 2, 3, 4, 5]))[2] == "MAD"


def test_zero_mad_falls_to_iqr_not_to_zero():
    median, scale, method = robust_scale(np.array([1., 1, 1, 1, 2, 3]))
    assert method == "IQR" and scale > 0


def test_constant_reference_raises_rather_than_scoring_as_normal():
    """Intake defect C3: the inherited code returned z = 0 here, which reads as
    'perfectly normal' for every component of that variant."""
    with pytest.raises(DegenerateScaleError):
        robust_scale(np.ones(20))


def test_no_finite_values_raises():
    with pytest.raises(DegenerateScaleError):
        robust_scale(np.array([np.nan, np.inf]))
