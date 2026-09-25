import numpy as np
import pandas as pd

from modulea import reason_codes
from modulea.constants import PARAMETERS
from modulea.scoring import COMPONENT_NAMES, contributing_components


def test_a_zero_weight_component_is_never_a_reason():
    """Intake defect C4: the inherited code could report A_ELECTRICAL on a component
    whose electrical weight was exactly 0.0."""
    weights = {"electrical": 0.0, "temporal": 0.0, "timing": 0.0,
               "overall_extreme": 0.0, "lot_relative": 1.0}
    ranked = pd.DataFrame([{c: 0.99 for c in COMPONENT_NAMES}])
    codes = reason_codes.build(ranked, weights, np.array([True]), np.array([False]),
                               np.array([""], dtype=object))
    assert "A_ELECTRICAL" not in codes[0]
    assert "A_LOT_RELATIVE_DEVIATION" in codes[0]
    assert contributing_components(weights, ranked.iloc[0]) == ["lot_relative"]


def test_limit_code_names_the_parameter():
    weights = {c: (1.0 if c == "lot_relative" else 0.0) for c in COMPONENT_NAMES}
    ranked = pd.DataFrame([{c: 0.1 for c in COMPONENT_NAMES}])
    codes = reason_codes.build(ranked, weights, np.array([True]), np.array([True]),
                               np.array(["IDDQ"], dtype=object))
    assert codes[0].startswith("A_STATIC_LIMIT_EXCEEDED:IDDQ")


def test_pass_rows_say_so():
    weights = {c: (1.0 if c == "lot_relative" else 0.0) for c in COMPONENT_NAMES}
    ranked = pd.DataFrame([{c: 0.1 for c in COMPONENT_NAMES}])
    codes = reason_codes.build(ranked, weights, np.array([False]), np.array([False]),
                               np.array([""], dtype=object))
    assert codes[0] == "A_OK"


def test_attribution_margin_is_reported():
    evidence = pd.DataFrame([[5.0, 4.9, 1, 1, 1, 1]], columns=PARAMETERS)
    primary, margin = reason_codes.primary_parameter(evidence)
    assert primary[0] == "IDDQ"
    assert abs(margin[0] - 0.1) < 1e-9
