"""The confusion matrix, and the intervals that go with it.

Every binary prediction on this problem falls into exactly one of four cells, and the
four together account for every component scored. What each one MEANS here, because the
arithmetic is the easy part and the meaning is what a reviewer acts on:

    TP  true positive   a component that IS abnormal, and Module A flagged it.
                        The screen worked.
    TN  true negative   a component that is NOT abnormal, and Module A passed it.
                        The screen stayed out of the way.
    FP  false positive  a HEALTHY component that Module A flagged.
                        Cost: review time. Nobody is harmed; someone is inconvenienced.
    FN  false negative  a component that IS abnormal, and Module A passed it.
                        Cost: a real defect reaches the next stage. This is the one
                        Chaitany asked to minimise, and the expensive error for ISRO.

The identity TP + TN + FP + FN = N holds by construction and is asserted, not assumed.
The rates are all derived from these four and nothing else:

    recall / TPR  = TP / (TP + FN)   of the truly abnormal parts, how many were caught
    specificity   = TN / (TN + FP)   of the truly healthy parts, how many were left alone
    FPR           = FP / (FP + TN)   = 1 - specificity
    FNR           = FN / (FN + TP)   = 1 - recall
    precision/PPV = TP / (TP + FP)   of the parts we flagged, how many were real
    NPV           = TN / (TN + FN)   of the parts we passed, how many were really fine
    F1            = 2TP / (2TP + FP + FN)

A denominator of zero is reported as NaN, never as 0.0. "No anomalies in this lot, so
recall is 0" is a false statement about a quantity that does not exist; a lot with no
anomalies cannot have a recall, and a table that prints 0.0 there will be read as a
failure that did not happen.
"""
from __future__ import annotations

import numpy as np


def _rate(numerator: int, denominator: int) -> float:
    """A rate, or NaN when its denominator is empty. Never a silent zero."""
    return numerator / denominator if denominator else float("nan")


def confusion(y: np.ndarray, flag: np.ndarray) -> dict:
    """All four cells and every rate derived from them.

    `y` is the truth: 1 abnormal, 0 healthy. `flag` is what Module A did: True means
    it raised the component for review (disposition MONITOR).
    """
    y = np.asarray(y)
    flag = np.asarray(flag)
    if y.shape != flag.shape:
        raise ValueError(f"truth and prediction differ in shape: {y.shape} vs {flag.shape}")
    unique = set(np.unique(y).tolist())
    if not unique <= {0, 1}:
        raise ValueError(f"truth must be 0 or 1, found {sorted(unique)}")
    y = y.astype(int)
    flag = flag.astype(bool)

    tp = int(((y == 1) & flag).sum())
    fp = int(((y == 0) & flag).sum())
    fn = int(((y == 1) & ~flag).sum())
    tn = int(((y == 0) & ~flag).sum())

    # The four cells partition the sample. If this ever fails, something upstream has
    # produced a truth value that is neither 0 nor 1, or a NaN has leaked into `flag`.
    assert tp + tn + fp + fn == y.size, (
        f"the four cells sum to {tp + tn + fp + fn}, not the {y.size} components scored")

    return {
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "n": int(y.size),
        "positives": tp + fn,          # truly abnormal
        "negatives": tn + fp,          # truly healthy
        "flagged": tp + fp,            # what a reviewer would see
        "passed": tn + fn,
        "recall": _rate(tp, tp + fn),          # TPR, sensitivity
        "specificity": _rate(tn, tn + fp),     # TNR
        "fpr": _rate(fp, fp + tn),             # 1 - specificity
        "fnr": _rate(fn, fn + tp),             # 1 - recall; the missed-defect rate
        "precision": _rate(tp, tp + fp),       # PPV
        "npv": _rate(tn, tn + fn),             # of what we passed, how much was fine
        "accuracy": _rate(tp + tn, y.size),
        "f1": _rate(2 * tp, 2 * tp + fp + fn),
    }


def check_identities(m: dict, tolerance: float = 1e-12) -> None:
    """Assert the relationships between the cells and the rates actually hold.

    Cheap, and it catches the class of bug where a rate is computed from the wrong
    denominator - which reads perfectly plausibly in a table and is wrong.
    """
    assert m["tp"] + m["tn"] + m["fp"] + m["fn"] == m["n"], "cells do not sum to n"
    assert m["positives"] + m["negatives"] == m["n"], "positives + negatives != n"
    assert m["flagged"] + m["passed"] == m["n"], "flagged + passed != n"
    for a, b in [("recall", "fnr"), ("specificity", "fpr")]:
        if not np.isnan(m[a]) and not np.isnan(m[b]):
            assert abs(m[a] + m[b] - 1.0) < tolerance, f"{a} + {b} != 1"
    if m["tp"] + m["fn"]:
        assert abs(m["recall"] - m["tp"] / (m["tp"] + m["fn"])) < tolerance
    if m["tp"] + m["fp"]:
        assert abs(m["precision"] - m["tp"] / (m["tp"] + m["fp"])) < tolerance


def rule_of_three_upper_bound(n: int, confidence: float = 0.95) -> float:
    """Upper bound on a rate after observing zero events in n trials.

    Zero false positives in n scored normals does not mean the true rate is zero.
    With no events observed, the one-sided upper bound is -ln(1-c)/n, about 3/n at
    95%. This is what lets the CONFIRMED tier be described honestly: not 'never
    wrong', but 'no error in n parts, so the rate is below this'.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    return float(-np.log(1.0 - confidence) / n)


def lot_bootstrap(y: np.ndarray, score: np.ndarray, lots: np.ndarray,
                  thresholds: np.ndarray, draws: int = 2000, seed: int = 26170):
    """Percentile bands for recall and FPR, resampling whole lots.

    Lots are the unit of correlation here, not rows: components in one lot share a
    reference and a manufacturing history. Resampling rows would report an interval
    several times too narrow.
    """
    rng = np.random.default_rng(seed)
    unique = np.unique(lots)
    index_by_lot = {lot: np.flatnonzero(lots == lot) for lot in unique}
    recalls = np.full((draws, len(thresholds)), np.nan)
    fprs = np.full((draws, len(thresholds)), np.nan)
    for d in range(draws):
        picked = rng.choice(unique, size=len(unique), replace=True)
        idx = np.concatenate([index_by_lot[lot] for lot in picked])
        yb, sb = np.asarray(y)[idx], np.asarray(score)[idx]
        pos, neg = yb == 1, yb == 0
        if not pos.any() or not neg.any():
            continue
        flags = sb[None, :] >= np.asarray(thresholds)[:, None]
        recalls[d] = flags[:, pos].sum(axis=1) / pos.sum()
        fprs[d] = flags[:, neg].sum(axis=1) / neg.sum()
    pct = lambda a, q: np.nanpercentile(a, q, axis=0)
    return {"recall_lo": pct(recalls, 2.5), "recall_hi": pct(recalls, 97.5),
            "fpr_lo": pct(fprs, 2.5), "fpr_hi": pct(fprs, 97.5)}
