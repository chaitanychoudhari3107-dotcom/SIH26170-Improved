"""
Stage 6 — execute the ONE pre-declared calibration decision.

The rule, written down on 14 Sep 2026 before ModuleB_Calibration.csv existed and
carried forward unexecuted through the V1 freeze:

    Move Output_Fall_Time from the timing feature set (own+lot+cross) to the
    current-group feature set (own) if and only if BOTH hold on the calibration
    lots:
        (a) `own` beats `own+lot+cross` by more than 3% MAE, AND
        (b) `own` wins on more than half the calibration lots.

Condition (b) was originally written as ">= 4 of 6" because the Candidate V1
calibration file had six lots. FINAL-01 ships twelve. Applying "4 lots" literally
would silently weaken the rule from two-thirds of lots to one-third, so it is
applied as the proportion it was written to express: more than half, i.e. >= 7
of 12. That re-reading is recorded here rather than made quietly.

This is the only configuration change the calibration stage is allowed to make.
Anything else the calibration data suggests is evidence for a team decision, not
a licence to edit the frozen block — see stage 7.
"""
from _common import Stage, header, show, written

import numpy as np
import pandas as pd

from moduleb import config, dataio, metrics, models
from moduleb.features import add_features

RULE = config.PREDECLARED_FALLTIME_RULE


def main() -> int:
    with Stage("STAGE 6 — pre-declared Output_Fall_Time feature-set decision"):
        p = RULE["param"]
        tr = dataio.load_split("train")
        ca = dataio.load_split("calibration")
        base, _ = dataio.load_specs()
        ftr = add_features(tr.frame, base)
        fca = add_features(ca.frame, base)

        header("6.0 the rule as declared")
        for k, v in RULE.items():
            print(f"  {k:18s} {v}")

        n_lots = int(fca.lot_id.nunique())
        min_lots = int(np.floor(n_lots / 2) + 1)
        print(f"\n  calibration lots available : {n_lots}")
        print(f"  condition (b) applied as   : >= {min_lots} of {n_lots} lots "
              f"(more than half, as declared)")

        header("6.1 both candidate feature sets, scored on the calibration lots")
        y = fca[f"{p}_168h"].to_numpy(float)
        lots = fca.lot_id.to_numpy()
        preds = {}
        rows = []
        for fs in (RULE["from_set"], RULE["move_to"]):
            cfg = dict(structure="pooled", model="Huber", features=fs)
            obj = models.fit_one(ftr, p, cfg)
            preds[fs] = models.predict_one(obj, fca, p)
            rows.append(dict(feature_set=fs, **metrics.metrics(y, preds[fs], lots)))
        show(pd.DataFrame(rows), "{:,.6f}")

        header("6.2 the two conditions")
        mae_from = float(np.abs(preds[RULE["from_set"]] - y).mean())
        mae_to = float(np.abs(preds[RULE["move_to"]] - y).mean())
        gain_pct = 100 * (mae_from - mae_to) / mae_from

        per_from = metrics.per_lot_mae(y, preds[RULE["from_set"]], lots)
        per_to = metrics.per_lot_mae(y, preds[RULE["move_to"]], lots)
        lots_won = int((per_to < per_from).sum())

        cond_a = gain_pct > RULE["min_mae_gain_pct"]
        cond_b = lots_won >= min_lots

        print(f"  (a) '{RULE['move_to']}' MAE gain over '{RULE['from_set']}' : "
              f"{gain_pct:+.3f}%   threshold > {RULE['min_mae_gain_pct']}%   -> "
              f"{'MET' if cond_a else 'NOT MET'}")
        print(f"  (b) lots won by '{RULE['move_to']}'                 : "
              f"{lots_won} of {n_lots}      threshold >= {min_lots}      -> "
              f"{'MET' if cond_b else 'NOT MET'}")

        detail = pd.DataFrame({
            "lot_id": per_from.index,
            f"MAE_{RULE['from_set']}": per_from.to_numpy(),
            f"MAE_{RULE['move_to']}": per_to.to_numpy(),
        })
        detail["winner"] = np.where(detail.iloc[:, 2] < detail.iloc[:, 1],
                                    RULE["move_to"], RULE["from_set"])
        show(detail, "{:,.6f}")

        header("6.3 DECISION")
        fires = cond_a and cond_b
        if fires:
            print(f"  BOTH conditions met. Per the pre-declared rule, {p} moves to the")
            print(f"  '{RULE['move_to']}' feature set. Apply this to moduleb.config.RECOMMENDED")
            print("  BEFORE freezing, and record it in docs/DECISION_LOG.md.")
        else:
            unmet = [n for n, c in (("a", cond_a), ("b", cond_b)) if not c]
            print(f"  Condition(s) {', '.join(unmet)} NOT met. The rule does not fire.")
            print(f"  {p} KEEPS the frozen '{RULE['from_set']}' feature set.")
            print("  No configuration change. This is the rule working as intended: it was")
            print("  written to license exactly one change on strong evidence, and the")
            print("  evidence is not there.")
        print("\n  Either way, the rule is now EXECUTED and is spent. It cannot be re-run")
        print("  on the holdout, and no second pre-declared decision exists.")

        out = pd.DataFrame([dict(
            param=p, from_set=RULE["from_set"], move_to=RULE["move_to"],
            mae_from=mae_from, mae_to=mae_to, gain_pct=gain_pct,
            threshold_gain_pct=RULE["min_mae_gain_pct"], condition_a_met=cond_a,
            lots_won=lots_won, n_lots=n_lots, min_lots_required=min_lots,
            condition_b_met=cond_b, rule_fires=fires,
            decision=f"move to {RULE['move_to']}" if fires else f"keep {RULE['from_set']}")])
        written(dataio.write_result(out, "06_predeclared_falltime_decision.csv"))
        written(dataio.write_result(detail, "06_predeclared_falltime_per_lot.csv"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
