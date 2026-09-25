"""Edge cases, worked deliberately along the axes that matter for this pipeline:
empty / one / boundary, wrong shape, extremes, and human misuse at the API."""
import numpy as np
import pandas as pd
import pytest

from conftest import expected_sizes

from moduleb import config, guards, models, predict
from moduleb.constants import PARAMS, TARGET_COLS
from moduleb.features import add_features, make_folds
from moduleb.metrics import metrics, paired_lot_test, verdict


def _artifact(synth_feat, specs):
    from moduleb.envelope import fit_envelope
    base, lim = specs
    return dict(models={p: models.fit_one(synth_feat, p, config.RECOMMENDED[p]) for p in PARAMS},
                envelopes={p: fit_envelope(synth_feat, p, config.RECOMMENDED[p]) for p in PARAMS},
                limits=lim, base=base, manifest={})


def test_empty_input_is_rejected(synth, specs):
    art = _artifact(add_features(synth, specs[0]), specs)
    empty = synth.iloc[0:0].drop(columns=TARGET_COLS)
    with pytest.raises(guards.DataQualityError, match="empty"):
        predict.predict_frame(art, empty, name="empty")


def test_single_component_is_refused_then_works_under_override(synth, specs):
    """Changed 19 Sep 2026 (review finding F1). This used to assert that a
    one-row request is a supported call. It is not: the timing models read
    own-lot medians and the evidence layer ranks against the request cohort, so
    a one-row answer is computed from a lot of size one. The contract is now
    cohort-level, and the deliberate override still has to produce a well-formed
    frame rather than crashing."""
    art = _artifact(add_features(synth, specs[0]), specs)
    one = synth.iloc[[0]].drop(columns=TARGET_COLS).reset_index(drop=True)

    with pytest.raises(guards.DataQualityError, match="whole lots"):
        predict.predict_frame(art, one, name="one")

    out, rep = predict.predict_frame(art, one, allow_partial_lot=True, name="one")
    assert len(out) == 1 and rep.n_rows == 1 and rep.partial_lot_override
    assert out.module_b_primary_parameter.iloc[0] in PARAMS


def test_single_component_lot_median_is_itself(synth, specs):
    """A one-row lot makes every lot-deviation feature exactly zero. That is the
    right answer, not a bug — but it must not become NaN or inf."""
    base, _ = specs
    one = synth.iloc[[0]].reset_index(drop=True)
    f = add_features(one, base)
    for p in PARAMS:
        assert f[f"reldev_{p}_0h"].iloc[0] == pytest.approx(0.0)
        assert np.isfinite(f[f"lotdrift_{p}"].iloc[0])


def test_unseen_variant_is_rejected_at_predict(synth, specs):
    art = _artifact(add_features(synth, specs[0]), specs)
    bad = synth.drop(columns=TARGET_COLS).copy()
    bad.loc[0, "device_variant"] = "CMOS_Z"
    with pytest.raises(guards.DataQualityError, match="unknown device_variant"):
        predict.predict_frame(art, bad, name="unseen")


def test_fewer_lots_than_folds(synth, specs):
    base, _ = specs
    small = synth[synth.lot_id.isin(["CMOS_A_LOT00", "CMOS_B_LOT00"])].reset_index(drop=True)
    f = add_features(small, base)
    folds = make_folds(f, 7)
    guards.assert_folds_are_whole_lots(f, folds)
    assert folds.nunique() <= 2      # cannot manufacture folds out of two lots


def test_envelope_refuses_too_few_lots(synth, specs):
    from moduleb.envelope import fit_envelope
    base, _ = specs
    few = synth[synth.lot_id.str.endswith(("LOT00", "LOT01"))].reset_index(drop=True)
    f = add_features(few, base)
    with pytest.raises(guards.DataQualityError, match="more than"):
        fit_envelope(f, "IDDQ", config.RECOMMENDED["IDDQ"])


def test_extreme_values_do_not_produce_nan(synth, specs):
    art = _artifact(add_features(synth, specs[0]), specs)
    wild = synth.drop(columns=TARGET_COLS).copy()
    for p in PARAMS:
        wild.loc[0, f"{p}_24h"] = wild.loc[0, f"{p}_0h"] * 50.0
    out, rep = predict.predict_frame(art, wild, name="wild",
                                     expected_lot_sizes=expected_sizes(wild))
    assert np.isfinite(out.select_dtypes(np.number).to_numpy()).all() or \
        out.filter(like="evidence_").isna().to_numpy().any()
    tau = int(round(config.ENVELOPE_TAU * 100))
    for p in PARAMS:
        assert np.isfinite(out[f"predicted_{p}_168h"]).all()
        assert np.isfinite(out[f"module_b_p{tau}_{p}_168h"]).all()


def test_component_id_order_is_preserved(synth, specs):
    art = _artifact(add_features(synth, specs[0]), specs)
    shuffled = synth.drop(columns=TARGET_COLS).sample(frac=1, random_state=5).reset_index(drop=True)
    out, _ = predict.predict_frame(art, shuffled, name="shuffled",
                                   expected_lot_sizes=expected_sizes(shuffled))
    assert list(out.component_id) == list(shuffled.component_id)


def test_metrics_reject_mismatched_shapes():
    with pytest.raises(ValueError):
        metrics([1, 2, 3], [1, 2], ["a", "a", "b"])
    with pytest.raises(ValueError):
        metrics([], [], [])


def test_verdict_calls_small_gains_ties():
    t = dict(gain_pct=1.2, wilcoxon_p=1e-9)
    assert verdict(t, config.TIE_THRESHOLD_PCT, config.PAIRED_TEST_ALPHA) == "TIE"
    t = dict(gain_pct=9.0, wilcoxon_p=1e-4)
    assert verdict(t, config.TIE_THRESHOLD_PCT, config.PAIRED_TEST_ALPHA) == "BETTER"
    t = dict(gain_pct=9.0, wilcoxon_p=0.4)
    assert verdict(t, config.TIE_THRESHOLD_PCT, config.PAIRED_TEST_ALPHA) == "TIE"
    t = dict(gain_pct=-9.0, wilcoxon_p=1e-4)
    assert verdict(t, config.TIE_THRESHOLD_PCT, config.PAIRED_TEST_ALPHA) == "WORSE"


def test_paired_test_counts_lots_not_rows():
    lots = np.repeat([f"L{i}" for i in range(10)], 50)
    y = np.ones(500)
    a = y + 0.1
    b = y + 0.2
    t = paired_lot_test(y, a, b, lots)
    assert t["n_lots"] == 10            # not 500
    assert t["lots_won"] == 10
