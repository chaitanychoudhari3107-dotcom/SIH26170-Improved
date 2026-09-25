"""The datasheet witness. The one tier described as having no false positives."""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from modulea.constants import PARAMETERS
from modulea.metrics import rule_of_three_upper_bound
from modulea.specs import SpecLimits

RELEASE = os.environ.get("SIH26170_RELEASE")
needs_release = pytest.mark.skipif(not RELEASE or not Path(RELEASE).exists(),
                                   reason="set SIH26170_RELEASE")


@pytest.fixture(scope="module")
def specs():
    return SpecLimits.load(Path(RELEASE) / "integration_safe/Device_Specs.csv")


@needs_release
def test_seven_cells_have_no_limit_and_stay_empty(specs):
    coverage = specs.coverage().iloc[0]
    assert int(coverage["cells_total"]) == 18
    assert int(coverage["cells_without_limit"]) == 7


@needs_release
def test_a_missing_limit_is_nan_never_zero(specs):
    """A zero limit would make every component a violation. NaN means 'no
    source-backed limit', and the rule must not fire."""
    for variant in ["CMOS_A", "CMOS_B", "CMOS_C"]:
        assert np.isnan(specs.limit(variant, "Active_Supply_Current"))


@needs_release
def test_the_rule_never_fires_where_there_is_no_limit(specs):
    frame = pd.read_csv(Path(RELEASE) / "module_a/ModuleA_Holdout.csv")
    ratios = specs.exceedance(frame, 168)
    assert ratios["Active_Supply_Current"].isna().all()


@needs_release
def test_an_unknown_variant_raises_rather_than_defaulting(specs):
    with pytest.raises(ValueError, match="no Device_Specs row"):
        specs.limit("CMOS_Z", "IDDQ")


@needs_release
@pytest.mark.parametrize("split", ["Train", "Calibration", "Holdout"])
def test_no_normal_component_violates_a_datasheet_limit(split):
    """The claim the CONFIRMED tier rests on, asserted per split."""
    root = Path(RELEASE)
    specs = SpecLimits.load(root / "integration_safe/Device_Specs.csv")
    frame = pd.read_csv(root / f"module_a/ModuleA_{split}.csv")
    truth = pd.read_csv(root / "hidden/Hidden_Ground_Truth.csv")
    truth = truth[truth["split"].str.upper().eq(split.upper())]
    merged = frame[["component_id"]].merge(truth, on="component_id", validate="one_to_one")
    violated, _, _ = specs.violation(frame, 168)
    y = merged["is_anomalous"].astype(int).to_numpy()
    assert int((violated & (y == 0)).sum()) == 0


@needs_release
def test_exceedance_ratio_is_above_one_exactly_when_violated(specs):
    frame = pd.read_csv(Path(RELEASE) / "module_a/ModuleA_Holdout.csv")
    violated, ratio, _ = specs.violation(frame, 168)
    assert (ratio[violated] > 1.0).all()
    assert (ratio[~violated] <= 1.0).all()


def test_the_zero_claim_is_bounded_not_absolute():
    """Nobody may write 'never'. Rule of three, on the release's normal count."""
    bound = rule_of_three_upper_bound(5076)
    assert 0 < bound < 0.001
    assert abs(bound - 3 / 5076) < 1e-4


def test_rule_of_three_rejects_a_nonsense_denominator():
    with pytest.raises(ValueError):
        rule_of_three_upper_bound(0)
