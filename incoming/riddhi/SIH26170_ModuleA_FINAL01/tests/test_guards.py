import numpy as np
import pandas as pd
import pytest

from modulea import guards


def test_accepts_a_clean_frame(synthetic, lot_sizes):
    frame = synthetic()
    clean = guards.validate_scoring_frame(frame, 168, "t", ["CMOS_A", "CMOS_B", "CMOS_C"],
                                          lot_sizes(frame))
    assert len(clean) == len(frame)


def test_future_columns_are_dropped_not_trusted(synthetic, lot_sizes):
    frame = synthetic()
    clean = guards.validate_scoring_frame(frame, 24, "t", ["CMOS_A", "CMOS_B", "CMOS_C"],
                                          lot_sizes(frame))
    assert not [c for c in clean.columns if c.endswith(("_96h", "_168h"))]
    with pytest.raises(guards.GuardError):
        guards.forbid_future_columns(frame, 24, "t")


def test_partial_lot_is_refused(synthetic, lot_sizes):
    frame = synthetic()
    sizes = lot_sizes(frame)
    with pytest.raises(guards.GuardError, match="incomplete"):
        guards.require_complete_lots(frame.iloc[:100], sizes, "t")


def test_counts_from_the_batch_itself_are_not_a_proof(synthetic):
    """A half-delivered lot counts itself as whole; only external sizes catch it."""
    frame = synthetic().iloc[:110]          # L02 arrives 30 of 40, above MIN_LOT_SIZE
    self_counted = frame.groupby("lot_id").size().to_dict()
    guards.require_complete_lots(frame, self_counted, "t")      # passes, wrongly
    with pytest.raises(guards.GuardError, match="incomplete"):
        guards.require_complete_lots(frame, {"L00": 40, "L01": 40, "L02": 40, "L03": 40}, "t")


def test_no_manifest_is_refused(synthetic):
    with pytest.raises(guards.GuardError, match="no external lot sizes"):
        guards.require_complete_lots(synthetic(), {}, "t")


def test_unknown_variant_is_refused(synthetic, lot_sizes):
    frame = synthetic()
    frame.loc[0, "device_variant"] = "CMOS_Z"
    with pytest.raises(guards.GuardError, match="unknown device_variant"):
        guards.require_known_variants(frame, ["CMOS_A", "CMOS_B", "CMOS_C"], "t")


def test_duplicate_ids_are_refused(synthetic):
    frame = pd.concat([synthetic().iloc[:2]] * 2, ignore_index=True)
    with pytest.raises(guards.GuardError, match="duplicate"):
        guards.require_unique_ids(frame, "t")


def test_non_positive_measurement_is_refused(synthetic):
    frame = synthetic()
    frame.loc[0, "IDDQ_0h"] = 0.0
    with pytest.raises(guards.GuardError, match="non-positive"):
        guards.require_measurements(frame, 168, "t")


def test_label_columns_never_reach_scoring(synthetic, lot_sizes):
    frame = synthetic()
    frame["is_anomalous"] = 0
    frame["defect_behavior"] = "STATIC_OUTLIER"
    clean = guards.validate_scoring_frame(frame, 168, "t", ["CMOS_A", "CMOS_B", "CMOS_C"],
                                          lot_sizes(frame))
    assert "is_anomalous" not in clean.columns
    assert "defect_behavior" not in clean.columns


def test_mixed_variant_lot_is_refused(synthetic):
    frame = synthetic()
    frame.loc[0, "device_variant"] = "CMOS_B" if frame.loc[0, "device_variant"] == "CMOS_A" else "CMOS_A"
    with pytest.raises(guards.GuardError, match="more than one device_variant"):
        guards.require_lot_variant_purity(frame, "t")
