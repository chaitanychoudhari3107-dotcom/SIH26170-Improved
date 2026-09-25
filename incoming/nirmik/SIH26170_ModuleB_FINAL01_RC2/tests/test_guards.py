"""The guards are the fail-safe. Every one of them gets a test that proves it
fires, because a guard nobody has seen fail is a comment."""
import numpy as np
import pandas as pd
import pytest

from moduleb import guards
from moduleb.constants import PARAMS


def test_96h_column_is_rejected(synth):
    bad = synth.copy()
    bad["IDDQ_96h"] = 1.0
    with pytest.raises(guards.LeakageError, match="96h"):
        guards.assert_input_clean(bad, allow_target=True, name="t")


@pytest.mark.parametrize("col", [
    "is_anomalous", "defect_mode", "generator_ground_truth", "severity",
    "trajectory_pattern", "onset_epoch_h", "spec_pass_168h", "module_b_disposition",
])
def test_hidden_label_columns_are_rejected(synth, col):
    bad = synth.copy()
    bad[col] = 0
    with pytest.raises(guards.LeakageError, match="hidden generator-truth"):
        guards.assert_input_clean(bad, allow_target=True, name="t")


def test_targets_rejected_when_not_allowed(synth):
    with pytest.raises(guards.LeakageError, match="must not receive 168h"):
        guards.assert_input_clean(synth, allow_target=False, name="holdout")


def test_partial_targets_rejected(synth):
    bad = synth.drop(columns=["IDDQ_168h"])
    with pytest.raises(guards.LeakageError, match="expected all six"):
        guards.assert_input_clean(bad, allow_target=True, name="t")


def test_missing_predictor_rejected(synth):
    bad = synth.drop(columns=["Output_Fall_Time_24h"])
    with pytest.raises(guards.LeakageError, match="missing required 0h/24h"):
        guards.assert_input_clean(bad, allow_target=True, name="t")


def test_duplicate_component_id_rejected(synth):
    bad = pd.concat([synth, synth.iloc[[0]]], ignore_index=True)
    with pytest.raises(guards.DataQualityError, match="duplicate"):
        guards.assert_data_quality(bad, name="t", expect_targets=True)


def test_nulls_rejected(synth):
    bad = synth.copy()
    bad.loc[0, "IDDQ_0h"] = np.nan
    with pytest.raises(guards.DataQualityError, match="null"):
        guards.assert_data_quality(bad, name="t", expect_targets=True)


def test_nonpositive_rejected(synth):
    bad = synth.copy()
    bad.loc[0, "IDDQ_24h"] = 0.0
    with pytest.raises(guards.DataQualityError, match="non-positive"):
        guards.assert_data_quality(bad, name="t", expect_targets=True)


def test_unknown_variant_rejected(synth):
    bad = synth.copy()
    bad.loc[0, "device_variant"] = "CMOS_D"
    with pytest.raises(guards.DataQualityError, match="unknown device_variant"):
        guards.assert_data_quality(bad, name="t", expect_targets=True)


def test_lot_overlap_rejected(synth):
    a = synth[synth.lot_id != "CMOS_A_LOT00"]
    b = synth[synth.lot_id.isin(["CMOS_A_LOT00", "CMOS_A_LOT01"])]
    with pytest.raises(guards.LeakageError, match="both"):
        guards.assert_lots_disjoint(a, b, name_a="train", name_b="calibration")


def test_row_level_split_is_rejected(synth_feat):
    rng = np.random.default_rng(0)
    folds = rng.integers(0, 4, len(synth_feat))     # deliberately random by ROW
    with pytest.raises(guards.LeakageError, match="split across folds"):
        guards.assert_folds_are_whole_lots(synth_feat, folds)


def test_feature_matrix_guard_catches_target(synth_feat):
    X = synth_feat[["IDDQ_0h", "IDDQ_24h"]].copy()
    X["IDDQ_168h"] = synth_feat["IDDQ_168h"].to_numpy()
    with pytest.raises(guards.LeakageError, match="168h"):
        guards.assert_feature_matrix_clean(X, name="t")


def test_feature_matrix_guard_catches_nan(synth_feat):
    X = synth_feat[["IDDQ_0h", "IDDQ_24h"]].copy()
    X.loc[0, "IDDQ_0h"] = np.nan
    with pytest.raises(guards.DataQualityError, match="non-finite"):
        guards.assert_feature_matrix_clean(X, name="t")


def test_predictions_sane_rejects_nan_and_negative():
    n = 5
    ok = {p: np.ones(n) for p in PARAMS}
    guards.assert_predictions_sane(ok, n, name="t")
    bad = {p: np.ones(n) for p in PARAMS}
    bad["IDDQ"] = np.array([1, 1, np.nan, 1, 1], float)
    with pytest.raises(guards.DataQualityError, match="non-finite"):
        guards.assert_predictions_sane(bad, n, name="t")
    bad2 = {p: np.ones(n) for p in PARAMS}
    bad2["IDDQ"] = np.array([1, -1, 1, 1, 1], float)
    with pytest.raises(guards.DataQualityError, match="non-positive"):
        guards.assert_predictions_sane(bad2, n, name="t")
