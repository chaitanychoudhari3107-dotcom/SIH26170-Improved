"""End-to-end behaviour: determinism, the output contract, and the clip guards."""
import numpy as np
import pandas as pd
import pytest

from conftest import expected_sizes

from moduleb import config, contract, cv, guards, models, predict, reason_codes
from moduleb.constants import PARAMS, TARGET_COLS
from moduleb.envelope import conformal_quantile, fit_envelope, predict_envelope


def _fitted(synth_feat, specs):
    base, lim = specs
    fitted = {p: models.fit_one(synth_feat, p, config.RECOMMENDED[p]) for p in PARAMS}
    envs = {p: fit_envelope(synth_feat, p, config.RECOMMENDED[p]) for p in PARAMS}
    return dict(models=fitted, envelopes=envs, limits=lim, base=base,
                manifest=dict(frozen_config_digest=config.frozen_config_digest(),
                              dataset="SIH26170-FINAL-01"))


def test_fit_predict_is_deterministic(synth_feat, specs):
    a = _fitted(synth_feat, specs)
    b = _fitted(synth_feat, specs)
    for p in PARAMS:
        ya = models.predict_one(a["models"][p], synth_feat, p)
        yb = models.predict_one(b["models"][p], synth_feat, p)
        np.testing.assert_allclose(ya, yb, rtol=0, atol=0)
        ea = predict_envelope(a["envelopes"][p], synth_feat, p)
        eb = predict_envelope(b["envelopes"][p], synth_feat, p)
        np.testing.assert_allclose(ea, eb, rtol=0, atol=0)


def test_prediction_is_row_order_invariant(synth_feat, specs):
    art = _fitted(synth_feat, specs)
    shuffled = synth_feat.sample(frac=1, random_state=11).reset_index(drop=True)
    for p in PARAMS:
        y1 = pd.Series(models.predict_one(art["models"][p], synth_feat, p),
                       index=synth_feat.component_id)
        y2 = pd.Series(models.predict_one(art["models"][p], shuffled, p),
                       index=shuffled.component_id)
        pd.testing.assert_series_equal(y1.sort_index(), y2.sort_index(), rtol=1e-12)


def test_estimator_is_insensitive_to_chunking_a_built_design_matrix(synth_feat, specs):
    """NARROW, and named for exactly what it proves.

    This splits an ALREADY FEATURE-ENGINEERED frame and calls the estimator on
    the pieces, so the lot medians were computed once, before the split. It shows
    the fitted estimator does not care how its rows are chunked. It does NOT show
    that `predict.predict_frame` is invariant to raw-request composition — it is
    not, and `test_raw_request_composition_changes_timing_forecasts` below
    measures by how much.

    Until 19 Sep 2026 this test was called `test_prediction_is_batch_size_invariant`
    and was cited as evidence for a single-component serving contract. That was
    review finding F1: the test never exercised the path the claim was about.
    """
    art = _fitted(synth_feat, specs)
    head, tail = synth_feat.iloc[:40], synth_feat.iloc[40:]
    for p in PARAMS:
        full = models.predict_one(art["models"][p], synth_feat, p)
        part = np.concatenate([models.predict_one(art["models"][p], head, p),
                               models.predict_one(art["models"][p], tail, p)])
        np.testing.assert_allclose(full, part, rtol=1e-10)


def test_output_contract_shape(synth_feat, specs):
    art = _fitted(synth_feat, specs)
    preds = {p: models.predict_one(art["models"][p], synth_feat, p) for p in PARAMS}
    env = {p: np.maximum(predict_envelope(art["envelopes"][p], synth_feat, p), preds[p])
           for p in PARAMS}
    out = contract.build_output(synth_feat, preds, art["limits"], env)
    for c in contract.CONTRACT_COLS:
        assert c in out.columns
    assert list(out.columns[:len(contract.CONTRACT_COLS)]) == contract.CONTRACT_COLS
    assert "module_b_disposition" not in out.columns
    assert list(out.component_id) == list(synth_feat.component_id)
    assert out.module_b_primary_parameter.isin(PARAMS).all()


def test_predict_rejects_a_frame_carrying_targets(synth, specs):
    from moduleb.features import add_features
    base, _ = specs
    feat = add_features(synth, base)
    art = _fitted(feat.assign(fold=0), specs)
    with pytest.raises(guards.LeakageError, match="must not receive 168h"):
        predict.predict_frame(art, synth, allow_target=False, name="pseudo-holdout")


def test_predict_accepts_a_holdout_shaped_frame(synth, specs):
    from moduleb.features import add_features
    base, _ = specs
    feat = add_features(synth, base)
    art = _fitted(feat.assign(fold=0), specs)
    holdout_like = synth.drop(columns=TARGET_COLS)
    out, rep = predict.predict_frame(art, holdout_like, name="pseudo-holdout",
                                     expected_lot_sizes=expected_sizes(holdout_like))
    assert len(out) == len(holdout_like)
    assert rep.n_rows == len(holdout_like)
    for c in contract.CONTRACT_COLS:
        assert c in out.columns


def test_envelope_never_sits_below_the_point_forecast(synth, specs):
    from moduleb.features import add_features
    base, _ = specs
    feat = add_features(synth, base)
    art = _fitted(feat.assign(fold=0), specs)
    raw = synth.drop(columns=TARGET_COLS)
    out, _ = predict.predict_frame(art, raw, name="t",
                                   expected_lot_sizes=expected_sizes(raw))
    tau = int(round(config.ENVELOPE_TAU * 100))
    for p in PARAMS:
        assert (out[f"module_b_p{tau}_{p}_168h"] >= out[f"predicted_{p}_168h"] - 1e-12).all()


def test_conformal_quantile_edges():
    s = np.arange(10, dtype=float)
    assert conformal_quantile(s, 0.05) == 9.0          # cannot certify 95% from 10 points
    assert conformal_quantile(np.arange(100, dtype=float), 0.05) == 95.0
    with pytest.raises(ValueError):
        conformal_quantile(np.array([]), 0.05)


def test_cv_uses_whole_lot_folds_only(synth_feat):
    res, oof = cv.cross_validate(synth_feat, config.RECOMMENDED,
                                 with_baselines=True, params=["IDDQ"])
    assert set(res.model) == {"MODULE_B", "Persistence", "LinExtrap", "MedianRatio_24h"}
    assert "ALL" in set(res.variant)
    assert np.isfinite(oof["IDDQ"]).all()


def test_cv_beats_persistence_on_a_signal_bearing_synthetic(synth_feat):
    """A sanity floor, not a benchmark: the synthetic frame has real drift, so a
    model that cannot beat 'no drift at all' is broken."""
    res, _ = cv.cross_validate(synth_feat, config.RECOMMENDED, params=["IDDQ"])
    r = res[(res.variant == "ALL") & (res.param == "IDDQ")].set_index("model").MAE
    assert r["MODULE_B"] < r["Persistence"]


# ---------------------------------------------------------------- F3 regression
def test_tail_is_ranked_by_true_drift_not_by_forecast_residual():
    """Review finding F3. The tail subset must be a property of the truth, not of
    the model: moving the point forecast must not change which components are
    called the worst drifters."""
    from moduleb.envelope import coverage_report
    rng = np.random.default_rng(3)
    n = 400
    x24 = rng.uniform(1.0, 5.0, n)
    y = x24 * (1 + rng.exponential(0.05, n))       # true drift, heavy right tail
    upper = y * 1.05

    good = x24 * (1 + 0.05)                        # a decent forecast
    awful = x24 * (1 + rng.uniform(-0.2, 0.2, n))  # a scrambled one

    a = coverage_report(y, upper, good, x24)
    b = coverage_report(y, upper, awful, x24)
    assert a["n_tail"] == b["n_tail"]
    assert a["tail_cut_rel_drift"] == pytest.approx(b["tail_cut_rel_drift"])
    assert a["tail_coverage"] == pytest.approx(b["tail_coverage"])
    assert a["tail_rank_basis"] == "true_relative_drift_from_24h"


def test_coverage_report_requires_x24():
    from moduleb.envelope import coverage_report
    with pytest.raises(TypeError):
        coverage_report(np.ones(3), np.ones(3), np.ones(3))          # x24 omitted
    with pytest.raises(ValueError):
        coverage_report(np.ones(3), np.ones(3), np.ones(3), np.ones(2))


# ---------------------------------------------------------------- F1 regression
def _raw(frame):
    return frame.drop(columns=[c for c in TARGET_COLS if c in frame.columns]).reset_index(drop=True)


def test_raw_request_composition_changes_timing_forecasts(synth, specs):
    """Review finding F1, stated as a measurement rather than a promise.

    `predict_frame` calls `add_features`, which recomputes own-lot medians from
    whatever rows are in the request. The three `own` parameters are unaffected.
    The three `own+lot+cross` parameters are not. This test pins that behaviour
    so nobody re-derives the old invariance claim from a passing suite.
    """
    from moduleb.constants import CURRENT_GROUP, TIMING_GROUP
    from moduleb.features import add_features
    base, _ = specs
    art = _fitted(add_features(synth, base).assign(fold=0), specs)

    lot = sorted(synth.lot_id.unique())[0]
    raw_lot = _raw(synth[synth.lot_id == lot])
    full, rep = predict.predict_frame(art, raw_lot, name="cohort",
                                      expected_lot_sizes=expected_sizes(raw_lot))
    assert rep.n_lots == 1 and not rep.partial_lot_override
    assert rep.completeness["proof"] == "request_metadata" and rep.clean
    full = full.set_index("component_id")

    cid = raw_lot.component_id.iloc[0]
    one = raw_lot[raw_lot.component_id == cid].reset_index(drop=True)
    single, _ = predict.predict_frame(art, one, allow_partial_lot=True, name="single")
    single = single.set_index("component_id")

    for p in CURRENT_GROUP:      # no lot terms -> genuinely identical
        assert single.loc[cid, f"predicted_{p}_168h"] == pytest.approx(
            full.loc[cid, f"predicted_{p}_168h"], rel=1e-12)

    moved = [p for p in TIMING_GROUP
             if abs(single.loc[cid, f"predicted_{p}_168h"]
                    - full.loc[cid, f"predicted_{p}_168h"]) > 1e-9]
    assert moved, ("timing forecasts were identical across request composition; if this "
                   "is now genuinely true the F1 remediation can be revisited")


def test_single_row_request_is_refused_by_default(synth, specs):
    from moduleb.features import add_features
    base, _ = specs
    art = _fitted(add_features(synth, base).assign(fold=0), specs)
    one = _raw(synth.iloc[[0]])
    with pytest.raises(guards.DataQualityError, match="whole lots"):
        predict.predict_frame(art, one, name="single")
    # ... and also when the declared size is supplied, because 1 != 35
    with pytest.raises(guards.DataQualityError):
        predict.predict_frame(art, one, name="single",
                              expected_lot_sizes=expected_sizes(synth))


def test_partial_lot_override_is_recorded(synth, specs):
    from moduleb.features import add_features
    base, _ = specs
    art = _fitted(add_features(synth, base).assign(fold=0), specs)
    one = _raw(synth.iloc[[0]])
    out, rep = predict.predict_frame(art, one, allow_partial_lot=True, name="single")
    assert len(out) == 1
    assert rep.partial_lot_override and not rep.clean
    assert any("partial-lot override" in l for l in rep.lines())


def test_evidence_layer_is_a_cohort_statistic(synth, specs):
    """The primary parameter is ranked against the other components in the
    request. On a one-row request every robust z is zero, so the ranking is
    degenerate. Pinned so the integration note cannot drift back to promising
    per-component stability."""
    from moduleb.features import add_features
    base, _ = specs
    art = _fitted(add_features(synth, base).assign(fold=0), specs)
    lot = sorted(synth.lot_id.unique())[0]
    raw_lot = _raw(synth[synth.lot_id == lot])
    full, _ = predict.predict_frame(art, raw_lot, name="cohort",
                                    expected_lot_sizes=expected_sizes(raw_lot))

    singles = []
    for cid in raw_lot.component_id.head(5):
        one = raw_lot[raw_lot.component_id == cid].reset_index(drop=True)
        s, _ = predict.predict_frame(art, one, allow_partial_lot=True, name="s")
        singles.append(s.module_b_primary_parameter.iloc[0])
    assert len(set(singles)) == 1, "degenerate single-row ranking should collapse to one label"
    assert full.module_b_primary_parameter.nunique() > 1, "cohort ranking should discriminate"
