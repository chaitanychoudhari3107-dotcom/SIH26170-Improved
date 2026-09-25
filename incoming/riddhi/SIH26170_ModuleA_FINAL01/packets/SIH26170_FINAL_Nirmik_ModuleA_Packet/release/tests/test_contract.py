import numpy as np
import pandas as pd
import pytest

from modulea import contract, tiers
from modulea.constants import CONTRACT_FIELDS


def _frame(n=50, seed=0, threshold=0.9):
    rng = np.random.default_rng(seed)
    statistical = rng.random(n)
    violated = rng.random(n) < 0.05
    ratio = np.where(violated, 1 + rng.random(n) * 0.4, np.nan)
    score = tiers.compose_score(statistical, violated, np.nan_to_num(ratio))
    disposition, tier = tiers.assign(score, violated, threshold)
    return contract.build_output(
        [f"C{i:05d}" for i in range(n)], score, disposition,
        np.where(disposition == "MONITOR", "IDDQ", ""), np.array(["A_OK"] * n),
        tier, np.zeros(n), statistical, ratio, 168, "COMPLETE_4_EPOCH",
        "ModuleA-FINAL01", "SIH26170-FINAL-01")


def test_contract_fields_come_first_and_in_order():
    frame = _frame()
    assert list(frame.columns[:5]) == CONTRACT_FIELDS
    contract.validate_output(frame, 0.9)


def test_reject_is_refused():
    frame = _frame()
    frame.loc[0, "module_a_disposition"] = "REJECT"
    with pytest.raises(AssertionError, match="belongs to fusion"):
        contract.validate_output(frame, 0.9)


def test_duplicate_ids_are_refused():
    frame = _frame()
    frame.loc[1, "component_id"] = frame.loc[0, "component_id"]
    with pytest.raises(AssertionError, match="duplicate"):
        contract.validate_output(frame, 0.9)


def test_score_outside_the_unit_interval_is_refused():
    frame = _frame()
    frame.loc[0, "module_a_score"] = 1.4
    with pytest.raises(AssertionError):
        contract.validate_output(frame, 0.9)


def test_a_confirmed_row_must_be_monitor():
    frame = _frame()
    idx = frame.index[frame["module_a_evidence_tier"].eq("CONFIRMED")]
    if len(idx):
        frame.loc[idx[0], "module_a_disposition"] = "PASS"
        with pytest.raises(AssertionError):
            contract.validate_output(frame, 0.9)
