"""Stage 4 — the performance claim, with nothing selected on the data it is scored on.

Intake defect C6: the inherited component weights and cutoff were grid-searched
over the FULL calibration set. RC2 grouped only its residual classifier; RC3
refitted the rank reference per fold but kept those legacy weights frozen. Both
disclosed it. Neither removed it, so neither could say what the whole procedure
scores out of sample.

This does. Leave-one-lot-out over the 12 calibration lots, and inside each fold
the weights AND the threshold are selected from the training lots only, by an
inner leave-one-lot-out. The held-out lot sees a configuration chosen without it.

Three arms, so the cost of each layer is visible:

  frozen     inherited weights, inherited cutoff          (what shipped before)
  threshold  inherited weights, threshold selected in-fold
  full       weights AND threshold both selected in-fold  (the honest estimate)

Writes results/04_nested_validation.{csv,json} and the per-fold detail.
"""
from __future__ import annotations

import argparse
import itertools
import json

import numpy as np
import pandas as pd

from _common import RESULTS, release_arg
from modulea import config
from modulea.cv import forbid_row_split, leave_one_lot_out
from modulea.dataio import Release
from modulea.metrics import confusion
from modulea.scoring import COMPONENT_NAMES, StatisticalCore

STEP = 0.1


def weight_grid(step: float = STEP) -> list[dict]:
    """The same small interpretable grid the original search used: five
    non-negative weights on a 0.1 lattice summing to 1."""
    levels = [round(x * step, 10) for x in range(int(1 / step) + 1)]
    grid = []
    for combo in itertools.product(levels, repeat=len(COMPONENT_NAMES) - 1):
        last = round(1.0 - sum(combo), 10)
        if last < -1e-9 or last > 1 + 1e-9:
            continue
        weights = dict(zip(COMPONENT_NAMES[:-1], combo))
        weights[COMPONENT_NAMES[-1]] = max(last, 0.0)
        total = sum(weights.values())
        if abs(total - 1.0) > 1e-9:
            continue
        grid.append(weights)
    return grid


def loosest_threshold(y: np.ndarray, score: np.ndarray, cap: float) -> float:
    normals = np.sort(score[y == 0])
    allowed = int(np.floor(cap * len(normals)))
    if allowed <= 0:
        return float(np.nextafter(normals[-1], np.inf))
    return float(np.nextafter(normals[-allowed - 1], np.inf))


def inner_oof_ranks(train, cal, idx) -> tuple[pd.DataFrame, np.ndarray]:
    """Rank components for the training lots, each scored by a core that did not
    see its own lot. Returns (ranks, positional index into cal)."""
    sub = cal.iloc[idx].reset_index(drop=True)
    ranks = pd.DataFrame(index=sub.index, columns=COMPONENT_NAMES, dtype=float)
    for _, inner_tr, inner_va in leave_one_lot_out(sub):
        core = StatisticalCore(config.DEPTHS).fit(train, sub.iloc[inner_tr])
        ranks.iloc[inner_va] = core.ranks(sub.iloc[inner_va]).to_numpy()
    return ranks, idx


def score_from_ranks(ranks: pd.DataFrame, weights: dict) -> np.ndarray:
    return sum(weights[c] * ranks[c].to_numpy(float) for c in COMPONENT_NAMES)


def main() -> None:
    parser = release_arg(argparse.ArgumentParser())
    parser.add_argument("--cap", type=float, default=config.OPERATING_FPR_BUDGET)
    args = parser.parse_args()

    release = Release(args.release)
    train, cal = release.split("train"), release.split("calibration")
    y = cal["is_anomalous"].astype(int).to_numpy()
    lots = cal["lot_id"].to_numpy()
    grid = weight_grid()

    arms = {"inherited": np.zeros(len(cal), bool),
            "threshold": np.zeros(len(cal), bool),
            "full": np.zeros(len(cal), bool),
            "shipped": np.zeros(len(cal), bool)}
    folds, chosen = [], []

    for lot, tr_idx, va_idx in leave_one_lot_out(cal):
        forbid_row_split(tr_idx, va_idx, lots)
        outer = StatisticalCore(config.DEPTHS).fit(train, cal.iloc[tr_idx])
        held_ranks = outer.ranks(cal.iloc[va_idx])

        inner_ranks, _ = inner_oof_ranks(train, cal, tr_idx)
        y_inner = y[tr_idx]

        # arm 1 — everything inherited: the weights AND the cutoff Better Potential
        # shipped with. This is the before-state, and it must use LEGACY_WEIGHTS —
        # using config.WEIGHTS here would silently mix the new weights with the old
        # threshold and label the result "inherited".
        legacy_score = score_from_ranks(held_ranks, config.LEGACY_WEIGHTS)
        arms["inherited"][va_idx] = legacy_score >= config.LEGACY_THRESHOLD

        # arm 2 — inherited weights, threshold selected on the training lots
        thr = loosest_threshold(
            y_inner, score_from_ranks(inner_ranks, config.LEGACY_WEIGHTS), args.cap)
        arms["threshold"][va_idx] = legacy_score >= thr

        # arm 4 — the configuration this release actually ships: the selected weights,
        # with the threshold chosen in-fold at the shipped budget.
        shipped_score = score_from_ranks(held_ranks, config.WEIGHTS)
        shipped_thr = loosest_threshold(
            y_inner, score_from_ranks(inner_ranks, config.WEIGHTS), args.cap)
        arms["shipped"][va_idx] = shipped_score >= shipped_thr

        # arm 3 — weights and threshold both selected on the training lots
        best = None
        for weights in grid:
            inner_score = score_from_ranks(inner_ranks, weights)
            t = loosest_threshold(y_inner, inner_score, args.cap)
            m = confusion(y_inner, inner_score >= t)
            key = (m["recall"], m["precision"])
            if best is None or key > best[0]:
                best = (key, weights, t)
        _, best_weights, best_threshold = best
        arms["full"][va_idx] = score_from_ranks(held_ranks, best_weights) >= best_threshold
        chosen.append({"held_out_lot": lot, "threshold": best_threshold, **best_weights})

        folds.append({"held_out_lot": lot, "components": int(len(va_idx)),
                      "anomalies": int(y[va_idx].sum()),
                      "inherited_threshold": thr, "selected_threshold": best_threshold,
                      **{f"inherited_{k}": v for k, v in
                         confusion(y[va_idx], arms["inherited"][va_idx]).items()},
                      **{f"shipped_{k}": v for k, v in
                         confusion(y[va_idx], arms["shipped"][va_idx]).items()},
                      **{f"threshold_{k}": v for k, v in
                         confusion(y[va_idx], arms["threshold"][va_idx]).items()},
                      **{f"full_{k}": v for k, v in
                         confusion(y[va_idx], arms["full"][va_idx]).items()}})

    table = pd.DataFrame([{"arm": name, "selection": desc, **confusion(y, flag)}
                          for (name, flag), desc in zip(arms.items(), [
                              "inherited weights (0.90/0.10) and the inherited 0.936978 "
                              "cutoff — the before-state",
                              "inherited weights; threshold selected inside each fold",
                              "weights AND threshold both selected inside each fold",
                              "THE SHIPPED CONFIGURATION: selected weights, threshold "
                              "chosen in-fold at the shipped budget"])])
    table.to_csv(RESULTS / "04_nested_validation.csv", index=False)
    pd.DataFrame(folds).to_csv(RESULTS / "04_nested_per_lot.csv", index=False)
    picked = pd.DataFrame(chosen)
    picked.to_csv(RESULTS / "04_selected_weights_per_fold.csv", index=False)

    stability = {c: picked[c].value_counts().to_dict() for c in COMPONENT_NAMES}
    summary = {
        "protocol": "leave-one-lot-out over 12 calibration lots; inner leave-one-lot-out "
                    "over the training lots selects weights and threshold",
        "fpr_cap": args.cap,
        "weight_grid_size": len(grid),
        "arms": table.to_dict("records"),
        "selected_weight_stability": stability,
        "reading": "The 'shipped' arm is the headline: it is what this release does, "
                   "estimated out of sample. 'full' is what an unconstrained in-fold "
                   "search achieves. 'inherited' is the before-state. Every arm must "
                   "be read at the SAME fpr_cap, and the cap that matters is the one "
                   "the release ships at — reporting an arm at a different budget from "
                   "the shipped configuration is not a comparison.",
        "warning": "fold unanimity in the weight search is budget-dependent. Do not "
                   "quote it without naming the cap it was measured at.",
    }
    (RESULTS / "04_nested_validation.json").write_text(json.dumps(summary, indent=2, default=float))
    print(table.to_string(index=False))
    print("\nweights chosen per fold (stability of the search):")
    print(picked.to_string(index=False))


if __name__ == "__main__":
    main()
