"""Properties the integration note promises. Measured in stage 12, asserted here."""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from modulea import config
from modulea.constants import PARAMETERS
from modulea.dataio import Release
from modulea.predict import ModuleA
from modulea.scoring import StatisticalCore
from modulea.specs import SpecLimits

RELEASE = os.environ.get("SIH26170_RELEASE")
needs_release = pytest.mark.skipif(not RELEASE or not Path(RELEASE).exists(),
                                   reason="set SIH26170_RELEASE")


@pytest.fixture(scope="module")
def model():
    release = Release(RELEASE)
    core = StatisticalCore(config.DEPTHS).fit(release.split("train"),
                                              release.split("calibration"))
    return ModuleA(core, SpecLimits.load(release.specs_path()), config.WEIGHTS,
                   config.OPERATING_THRESHOLD, {0: 0.667, 24: 0.678, 96: 0.693},
                   release.expected_lot_sizes(), config.MODEL_VERSION, config.DATASET_ID)


@pytest.fixture(scope="module")
def holdout():
    return Release(RELEASE).split("holdout")


def _sorted(model, frame, epoch=168):
    return model.predict(frame, epoch).sort_values("component_id").reset_index(drop=True)


@needs_release
@pytest.mark.parametrize("transform,name", [
    (lambda d: d.sample(frac=1.0, random_state=1), "shuffled"),
    (lambda d: d.iloc[::-1], "reversed"),
    (lambda d: d.set_index(np.arange(len(d))[::-1]), "reindexed"),
])
def test_row_order_does_not_change_any_score(model, holdout, transform, name):
    a = _sorted(model, holdout)
    b = _sorted(model, transform(holdout))
    assert (a["module_a_score"].to_numpy() == b["module_a_score"].to_numpy()).all()


@needs_release
def test_column_order_does_not_change_any_score(model, holdout):
    rng = np.random.default_rng(3)
    shuffled = holdout[list(rng.permutation(holdout.columns))]
    a, b = _sorted(model, holdout), _sorted(model, shuffled)
    assert (a["module_a_score"].to_numpy() == b["module_a_score"].to_numpy()).all()


@needs_release
def test_an_unexpected_extra_column_is_ignored(model, holdout):
    extra = holdout.copy()
    extra["some_upstream_column"] = "ignored"
    a, b = _sorted(model, holdout), _sorted(model, extra)
    assert (a["module_a_score"].to_numpy() == b["module_a_score"].to_numpy()).all()


@needs_release
def test_scoring_a_subset_of_complete_lots_gives_identical_scores(model, holdout):
    """Module A scores per lot, so a subset of whole lots must not shift anything."""
    lot = holdout["lot_id"].iloc[0]
    subset = holdout[~holdout["lot_id"].eq(lot)]
    full = _sorted(model, holdout)
    part = _sorted(model, subset)
    shared = full[full["component_id"].isin(part["component_id"])]
    assert (shared["module_a_score"].to_numpy() == part["module_a_score"].to_numpy()).all()


@needs_release
@pytest.mark.parametrize("break_it,pattern", [
    (lambda d: d.drop(index=d.index[0]), "incomplete"),
    (lambda d: pd.concat([d, d.iloc[[0]]], ignore_index=True), "duplicate"),
    (lambda d: d.assign(IDDQ_168h=d["IDDQ_168h"].mask(d.index == 0, -1.0)), "non-positive"),
    (lambda d: d.assign(IDDQ_0h=d["IDDQ_0h"].mask(d.index == 0, 0.0)), "non-positive"),
    (lambda d: d.assign(Propagation_Delay_96h=d["Propagation_Delay_96h"]
                        .mask(d.index == 0, np.nan)), "null or non-numeric"),
    (lambda d: d.drop(columns=["Output_Fall_Time_96h"]), "missing required columns"),
    (lambda d: d.assign(lot_id=d["lot_id"].mask(d.index == 0, "   ")), "blank or null"),
])
def test_malformed_input_raises_rather_than_scoring(model, holdout, break_it, pattern):
    with pytest.raises(Exception, match=pattern):
        model.predict(break_it(holdout), 168)


@needs_release
def test_a_lot_relative_score_is_scale_free(model, holdout):
    """Documented property, and a documented weakness: a global unit error is
    invisible to the statistical tier. Only the datasheet witness notices."""
    scaled = holdout.copy()
    for p in PARAMETERS:
        for e in [0, 24, 96, 168]:
            scaled[f"{p}_{e}h"] *= 1000.0
    a = _sorted(model, holdout)
    b = _sorted(model, scaled)
    statistical_drift = float(np.max(np.abs(a["statistical_score"].to_numpy()
                                            - b["statistical_score"].to_numpy())))
    assert statistical_drift < 0.05, "statistical score should be near scale-free"
    assert (b["module_a_evidence_tier"].eq("CONFIRMED").sum()
            > a["module_a_evidence_tier"].eq("CONFIRMED").sum())


@needs_release
def test_every_epoch_output_satisfies_the_contract(model, holdout):
    from modulea import contract
    for epoch in [0, 24, 96, 168]:
        out = model.predict(holdout, epoch)
        threshold = (model.operating_threshold if epoch == 168
                     else model.early_thresholds[epoch])
        contract.validate_output(out, threshold)
