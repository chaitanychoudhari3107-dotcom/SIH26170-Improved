"""Per-parameter evidence and the attribution built on it."""
import numpy as np
import pandas as pd
import pytest

from modulea import evidence
from modulea.constants import EPOCHS, PARAMETERS
from modulea.reason_codes import primary_parameter


def _lot(n=60, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        row = {"component_id": f"C{i:04d}", "lot_id": "L1",
               "device_family": "DIGITAL_CMOS", "device_variant": "CMOS_A"}
        for j, p in enumerate(PARAMETERS):
            for e in EPOCHS:
                row[f"{p}_{e}h"] = 1.0 + 0.1 * j + rng.normal(0, 0.01)
        rows.append(row)
    return pd.DataFrame(rows)


def test_a_planted_deviation_is_found_on_the_right_parameter():
    frame = _lot()
    frame.loc[0, "Output_Rise_Time_168h"] *= 1.5
    per_parameter = evidence.per_parameter(frame, 168)
    primary, margin = primary_parameter(per_parameter)
    assert primary[0] == "Output_Rise_Time"
    assert margin[0] > 0


def test_evidence_only_reads_epochs_that_have_happened():
    frame = _lot()
    poisoned = frame.copy()
    poisoned["IDDQ_168h"] *= 50
    a = evidence.per_parameter(frame, 24)
    b = evidence.per_parameter(poisoned, 24)
    pd.testing.assert_frame_equal(a, b)


def test_a_constant_lot_produces_no_deviation_rather_than_raising():
    """Unlike the variant reference, a constant lot genuinely means nobody deviates."""
    frame = _lot()
    for e in EPOCHS:
        frame[f"IDDQ_{e}h"] = 1.0
    per_parameter = evidence.per_parameter(frame, 168)
    assert (per_parameter["IDDQ"] == 0).all()


def test_observed_evidence_score_is_bounded_and_monotone():
    frame = pd.DataFrame({p: [0.0, 1.0, 3.0, 10.0, 40.0] for p in PARAMETERS})
    score = evidence.observed_evidence_score(frame)
    assert np.all((score >= 0) & (score < 1))
    assert np.all(np.diff(score) >= 0)


def test_attribution_margin_is_zero_on_a_tie():
    frame = pd.DataFrame([[3.0] * 6], columns=PARAMETERS)
    _, margin = primary_parameter(frame)
    assert margin[0] == 0.0


def test_primary_parameter_refuses_a_wrongly_shaped_frame():
    with pytest.raises(ValueError):
        primary_parameter(pd.DataFrame([[1.0, 2.0]], columns=["a", "b"]))
