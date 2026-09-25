"""End-to-end tests against the real release, skipped when it is not present."""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from modulea import config, contract, tiers
from modulea.dataio import Release
from modulea.freeze import FreezeRefused, freeze, load
from modulea.predict import ModuleA
from modulea.scoring import StatisticalCore
from modulea.specs import SpecLimits

RELEASE = os.environ.get("SIH26170_RELEASE")
needs_release = pytest.mark.skipif(not RELEASE or not Path(RELEASE).exists(),
                                   reason="set SIH26170_RELEASE to the release root")

SIGNOFF = "Test sign-off — not a release sign-off, used only by the unit suite."


@pytest.fixture(scope="module")
def fitted():
    release = Release(RELEASE)
    train, cal = release.split("train"), release.split("calibration")
    core = StatisticalCore(config.DEPTHS).fit(train, cal)
    specs = SpecLimits.load(release.specs_path())
    return ModuleA(core, specs, config.WEIGHTS, config.OPERATING_THRESHOLD,
                   {0: 0.667, 24: 0.678, 96: 0.693}, release.expected_lot_sizes(),
                   config.MODEL_VERSION, config.DATASET_ID), release


@needs_release
def test_predicts_and_satisfies_the_contract(fitted):
    model, release = fitted
    out = model.predict(release.split("holdout"), 168)
    assert len(out) == 1343
    contract.validate_output(out, model.operating_threshold)


@needs_release
def test_one_threshold_reproduces_the_decision(fitted):
    model, release = fitted
    out = model.predict(release.split("holdout"), 168)
    implied = out["module_a_score"].to_numpy() >= model.monitor_floor
    assert np.array_equal(implied, out["module_a_disposition"].eq("MONITOR").to_numpy())


@needs_release
def test_every_epoch_scores(fitted):
    model, release = fitted
    for epoch in [0, 24, 96, 168]:
        out = model.predict(release.split("holdout"), epoch)
        assert out["scored_epoch_h"].eq(epoch).all()
        assert out["analysis_status"].nunique() == 1


@needs_release
def test_scoring_at_an_early_epoch_cannot_see_later_columns(fitted, monkeypatch):
    model, release = fitted
    frame = release.split("holdout")
    poisoned = frame.copy()
    poisoned.loc[:, "IDDQ_168h"] = 1e6            # would dominate any score that read it
    a = model.predict(frame, 24)["module_a_score"].to_numpy()
    b = model.predict(poisoned, 24)["module_a_score"].to_numpy()
    assert np.array_equal(a, b), "a 168 h column changed a 24 h score"


@needs_release
def test_partial_batch_is_refused(fitted):
    model, release = fitted
    with pytest.raises(Exception, match="incomplete|absent"):
        model.predict(release.split("holdout").iloc[:400], 168)


@needs_release
def test_artifact_round_trips(fitted, tmp_path):
    model, release = fitted
    before = model.predict(release.split("holdout"), 168)
    receipt = freeze(model, tmp_path / "a.joblib", SIGNOFF,
                     {"train": "x" * 64, "calibration": "y" * 64})
    reloaded, payload = load(tmp_path / "a.joblib")
    after = reloaded.predict(release.split("holdout"), 168)
    pd.testing.assert_frame_equal(before, after)
    assert payload["config_digest"] == config.config_digest()
    assert receipt["artifact_sha256"]


@needs_release
def test_freeze_refuses_a_placeholder_signoff(fitted, tmp_path):
    model, _ = fitted
    with pytest.raises(FreezeRefused, match="sign-off"):
        freeze(model, tmp_path / "b.joblib", "ok", {"train": "x", "calibration": "y"})


@needs_release
def test_freeze_refuses_without_a_lot_manifest(fitted, tmp_path):
    model, release = fitted
    stripped = ModuleA(model.core, model.specs, model.weights, model.operating_threshold,
                       model.early_thresholds, {}, model.model_version, model.dataset_id)
    with pytest.raises(FreezeRefused, match="lot manifest"):
        freeze(stripped, tmp_path / "c.joblib", SIGNOFF,
               {"train": "x" * 64, "calibration": "y" * 64})


@needs_release
def test_scoring_is_deterministic(fitted):
    model, release = fitted
    a = model.predict(release.split("holdout"), 168)
    b = model.predict(release.split("holdout"), 168)
    pd.testing.assert_frame_equal(a, b)


@needs_release
def test_unknown_variant_is_refused(fitted):
    model, release = fitted
    frame = release.split("holdout").copy()
    # A whole lot, so the mixed-variant guard does not fire first.
    lot = frame.loc[0, "lot_id"]
    frame.loc[frame["lot_id"].eq(lot), "device_variant"] = "CMOS_Z"
    with pytest.raises(Exception, match="unknown device_variant"):
        model.predict(frame, 168)
