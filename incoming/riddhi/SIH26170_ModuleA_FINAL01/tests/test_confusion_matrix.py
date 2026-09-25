"""The four confusion-matrix outcomes, checked against an independent reference.

`modulea.metrics.confusion` is hand-rolled, and every headline number in this release
is derived from it. Hand-rolled code that nothing checks is how a transposed cell ships:
swap FP and FN and the arithmetic still balances, every rate still lands in [0, 1], and
the table still looks right — while the release claims it misses defects it catches and
catches defects it misses.

So these tests do three things:

  1. compare every cell against sklearn's confusion_matrix on randomised inputs,
  2. assert the algebraic identities that relate the cells to the rates,
  3. pin the domain orientation with hand-written cases, so a transposition is caught
     by meaning and not only by arithmetic.
"""
import numpy as np
import pytest
from sklearn.metrics import (confusion_matrix, f1_score, precision_score,
                             recall_score)

from modulea.metrics import check_identities, confusion


# ---------------------------------------------------------------- orientation
def test_a_caught_defect_is_a_true_positive():
    m = confusion(np.array([1]), np.array([True]))
    assert (m["tp"], m["tn"], m["fp"], m["fn"]) == (1, 0, 0, 0)


def test_a_missed_defect_is_a_false_negative():
    """The expensive error: a real defect Module A passed."""
    m = confusion(np.array([1]), np.array([False]))
    assert (m["tp"], m["tn"], m["fp"], m["fn"]) == (0, 0, 0, 1)
    assert m["fnr"] == 1.0 and m["recall"] == 0.0


def test_a_flagged_healthy_part_is_a_false_positive():
    """The cheap error: review time spent on a good component."""
    m = confusion(np.array([0]), np.array([True]))
    assert (m["tp"], m["tn"], m["fp"], m["fn"]) == (0, 1, 0, 0) or \
           (m["tp"], m["tn"], m["fp"], m["fn"]) == (0, 0, 1, 0)
    assert m["fp"] == 1 and m["fpr"] == 1.0


def test_a_passed_healthy_part_is_a_true_negative():
    m = confusion(np.array([0]), np.array([False]))
    assert (m["tp"], m["tn"], m["fp"], m["fn"]) == (0, 1, 0, 0)
    assert m["specificity"] == 1.0


def test_the_four_cells_are_not_transposed():
    """Two defects, one caught; two healthy, one flagged. Every cell distinct."""
    y = np.array([1, 1, 0, 0])
    flag = np.array([True, False, True, False])
    m = confusion(y, flag)
    assert m["tp"] == 1, "one defect was caught"
    assert m["fn"] == 1, "one defect was missed"
    assert m["fp"] == 1, "one healthy part was flagged"
    assert m["tn"] == 1, "one healthy part was passed"


# ------------------------------------------------------- against the reference
@pytest.mark.parametrize("seed", range(25))
def test_every_cell_matches_sklearn(seed):
    rng = np.random.default_rng(seed)
    n = int(rng.integers(1, 400))
    y = rng.integers(0, 2, n)
    flag = rng.random(n) < rng.random()
    tn, fp, fn, tp = confusion_matrix(y, flag.astype(int), labels=[0, 1]).ravel()
    m = confusion(y, flag)
    assert (m["tp"], m["tn"], m["fp"], m["fn"]) == (int(tp), int(tn), int(fp), int(fn))


@pytest.mark.parametrize("seed", range(15))
def test_derived_rates_match_sklearn(seed):
    rng = np.random.default_rng(1000 + seed)
    n = int(rng.integers(20, 400))
    y = rng.integers(0, 2, n)
    flag = rng.random(n) < 0.4
    m = confusion(y, flag)
    pred = flag.astype(int)
    assert m["recall"] == pytest.approx(recall_score(y, pred, zero_division=np.nan),
                                        nan_ok=True)
    assert m["precision"] == pytest.approx(precision_score(y, pred, zero_division=np.nan),
                                           nan_ok=True)
    assert m["f1"] == pytest.approx(f1_score(y, pred, zero_division=np.nan), nan_ok=True)


@pytest.mark.parametrize("seed", range(20))
def test_identities_hold_on_random_inputs(seed):
    rng = np.random.default_rng(2000 + seed)
    n = int(rng.integers(1, 300))
    y = rng.integers(0, 2, n)
    flag = rng.random(n) < rng.random()
    check_identities(confusion(y, flag))


# --------------------------------------------------------------- degeneracies
def test_a_lot_with_no_anomalies_has_no_recall():
    """NaN, not 0.0. A lot with nothing to catch cannot have failed to catch it, and
    a table printing 0.0 there will be read as a failure that never happened."""
    m = confusion(np.zeros(50, int), np.zeros(50, bool))
    assert np.isnan(m["recall"]) and np.isnan(m["precision"])
    assert m["specificity"] == 1.0 and m["fpr"] == 0.0


def test_a_batch_of_only_anomalies_has_no_specificity():
    m = confusion(np.ones(30, int), np.ones(30, bool))
    assert m["recall"] == 1.0
    assert np.isnan(m["specificity"]) and np.isnan(m["fpr"])


def test_flagging_nothing_is_reported_honestly():
    y = np.array([1, 1, 0, 0, 0])
    m = confusion(y, np.zeros(5, bool))
    assert (m["tp"], m["fp"]) == (0, 0)
    assert m["recall"] == 0.0
    assert np.isnan(m["precision"]), "precision of an empty flag set is undefined"
    assert m["f1"] == 0.0


def test_flagging_everything_is_reported_honestly():
    y = np.array([1, 1, 0, 0, 0])
    m = confusion(y, np.ones(5, bool))
    assert m["recall"] == 1.0 and m["fpr"] == 1.0
    assert m["precision"] == pytest.approx(2 / 5)


# ----------------------------------------------------------------- input guard
def test_a_non_binary_truth_is_refused():
    with pytest.raises(ValueError, match="must be 0 or 1"):
        confusion(np.array([0, 1, 2]), np.array([True, True, True]))


def test_mismatched_lengths_are_refused():
    with pytest.raises(ValueError, match="differ in shape"):
        confusion(np.array([0, 1]), np.array([True]))


def test_a_transposed_implementation_would_fail_these_tests():
    """Guard on the guard: if someone swaps the FP and FN expressions, the identities
    still balance, so orientation has to be pinned by meaning. This asserts the
    asymmetric case that a transposition would break."""
    y = np.array([1, 1, 1, 0])
    flag = np.array([True, False, False, False])
    m = confusion(y, flag)
    assert m["fn"] == 2 and m["fp"] == 0
    assert m["recall"] == pytest.approx(1 / 3)
    assert m["fpr"] == 0.0
