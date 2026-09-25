"""
Stage 7 — where does this model produce a forecast it has no business making?

The brief for Module B is explicitly fail-safe: a wrong forecast that looks
confident is worse than a wide one that looks uncertain, because the fusion
layer and the operator downstream cannot see the model's reasoning. So this
stage hunts for the specific failure mode a per-parameter regressor on a
relative-delta target has: extrapolation. If the training targets contain a
heavy tail, the fitted function can return a drift far outside anything the
model should assert, on a component whose inputs merely resemble a tail case.

Everything here is measurement plus ONE proposal. Nothing is applied: the
extrapolation cap lives in moduleb.config as FORECAST_REL_DELTA_CAP and is None,
so this package reproduces the frozen Candidate V1 model exactly. Turning it on
is a model change, changes the frozen config digest, and needs a team decision.

The holdout is NOT touched by this stage. It is not inspected, not predicted on,
and not summarised. Everything below uses out-of-fold train predictions and the
calibration lots.
"""
from _common import Stage, header, show, sub, written

import numpy as np
import pandas as pd

from moduleb import baselines, config, cv, dataio, models, reason_codes
from moduleb.constants import PARAMS
from moduleb.features import add_features, make_folds

CAPS = (0.25, 0.50, 1.00)


def main() -> int:
    with Stage("STAGE 7 — extrapolation risk and the fail-safe proposal"):
        tr = dataio.load_split("train")
        ca = dataio.load_split("calibration")
        base, limits = dataio.load_specs()
        ftr = add_features(tr.frame, base)
        ftr["fold"] = make_folds(ftr, config.N_FOLDS)
        fca = add_features(ca.frame, base)

        header("7.1 what the TRAINING targets actually look like")
        print("The model's target is the relative change from 24h. A heavy right tail")
        print("here is what makes extrapolation possible at all.")
        rows = []
        for p in PARAMS:
            t = ((ftr[f"{p}_168h"].to_numpy(float) - ftr[f"{p}_24h"].to_numpy(float))
                 / ftr[f"{p}_24h"].to_numpy(float))
            rows.append(dict(param=p, p01=np.quantile(t, .01), median=np.median(t),
                             p99=np.quantile(t, .99), p999=np.quantile(t, .999),
                             max=t.max(), max_over_p99=t.max() / np.quantile(t, .99)))
        tt = pd.DataFrame(rows)
        show(tt, "{:,.4f}")
        written(dataio.write_result(tt, "07_target_tails.csv"))
        print("\nmax_over_p99 is the headline: a parameter where the largest training")
        print("target is many times the 99th percentile is one where a single unusual")
        print("component can teach the model to produce an unusual forecast.")

        header("7.2 the predicted relative delta the frozen model actually emits")
        rows = []
        fitted = {p: models.fit_one(ftr, p, config.RECOMMENDED[p]) for p in PARAMS}
        oof = {p: cv.out_of_fold_predictions(ftr, p, config.RECOMMENDED[p]) for p in PARAMS}
        cal_pred = {p: models.predict_one(fitted[p], fca, p) for p in PARAMS}
        for p in PARAMS:
            for tag, frame, pred in (("train_oof", ftr, oof[p]), ("calibration", fca, cal_pred[p])):
                x24 = frame[f"{p}_24h"].to_numpy(float)
                rel = (pred - x24) / x24
                rows.append(dict(param=p, split=tag, n=len(rel), min=rel.min(),
                                 p99=np.quantile(rel, .99), max=rel.max(),
                                 n_abs_gt_0p25=int((np.abs(rel) > 0.25).sum()),
                                 n_abs_gt_0p50=int((np.abs(rel) > 0.50).sum()),
                                 n_abs_gt_1p00=int((np.abs(rel) > 1.00).sum())))
        pr = pd.DataFrame(rows)
        show(pr, "{:,.4f}")
        written(dataio.write_result(pr, "07_predicted_rel_delta.csv"))

        header("7.3 error concentration — is a parameter's MAE one component?")
        rows = []
        for p in PARAMS:
            y = fca[f"{p}_168h"].to_numpy(float)
            err = np.abs(cal_pred[p] - y)
            order = np.argsort(err)[::-1]
            tot = err.sum()
            rows.append(dict(param=p, calibration_MAE=err.mean(),
                             worst_row_share_pct=100 * err[order[0]] / tot,
                             top5_share_pct=100 * err[order[:5]].sum() / tot,
                             top1pct_share_pct=100 * err[order[:max(1, len(err) // 100)]].sum() / tot))
        ec = pd.DataFrame(rows)
        show(ec, "{:,.3f}")
        written(dataio.write_result(ec, "07_error_concentration.csv"))
        print("\nA parameter where one component of 906 carries a large share of the total")
        print("error does not have an accuracy problem spread across the fleet. It has one")
        print("forecast that went wrong, and that is a different thing to fix and to report.")

        header("7.4 the worst forecast, in full")
        worst_param = ec.sort_values("worst_row_share_pct", ascending=False).param.iloc[0]
        y = fca[f"{worst_param}_168h"].to_numpy(float)
        err = np.abs(cal_pred[worst_param] - y)
        i = int(err.argmax())
        x0 = float(fca[f"{worst_param}_0h"].iloc[i])
        x24 = float(fca[f"{worst_param}_24h"].iloc[i])
        lim = limits.loc[fca.device_variant.iloc[i], worst_param]
        print(f"  parameter        {worst_param}")
        print(f"  component        {fca.component_id.iloc[i]}  lot {fca.lot_id.iloc[i]}  "
              f"{fca.device_variant.iloc[i]}")
        print(f"  measured  0h     {x0:.5f}")
        print(f"  measured 24h     {x24:.5f}   (early move {100 * (x24 - x0) / x0:+.2f}%)")
        print(f"  true     168h    {y[i]:.5f}   (true drift from 24h {100 * (y[i] - x24) / x24:+.2f}%)")
        print(f"  forecast 168h    {cal_pred[worst_param][i]:.5f}   "
              f"(predicted drift {100 * (cal_pred[worst_param][i] - x24) / x24:+.2f}%)")
        print(f"  absolute error   {err[i]:.5f}  = {100 * err[i] / err.sum():.1f}% of this "
              f"parameter's total calibration error")
        print(f"  static limit     {lim if pd.notna(lim) else 'none for this cell'}")
        print("\n  Both the true value and the forecast are above the limit here, so the")
        print("  limit-based reason code is a TRUE positive on this component. The problem")
        print("  is the magnitude of the forecast, not its direction.")

        header("7.5 PROPOSAL — cap the predicted relative delta at inference")
        print("A hard cap |predicted rel delta| <= c, applied after the model and before")
        print("the contract. The fitted coefficients are untouched, but enabling it is still")
        print("a model/pipeline behaviour change with its own digest, not a bug fix")
        print("(wording corrected 19 Sep, review finding F4).")
        print("It is a statement that Module B will not assert a drift larger than c.\n")
        rows = []
        for cap in CAPS:
            for p in PARAMS:
                for tag, frame, pred in (("train_oof", ftr, oof[p]),
                                         ("calibration", fca, cal_pred[p])):
                    x24 = frame[f"{p}_24h"].to_numpy(float)
                    rel = (pred - x24) / x24
                    capped = x24 * (1 + np.clip(rel, -cap, cap))
                    yt = frame[f"{p}_168h"].to_numpy(float)
                    mae, mae_c = np.abs(pred - yt).mean(), np.abs(capped - yt).mean()
                    rows.append(dict(cap=cap, param=p, split=tag,
                                     n_capped=int((np.abs(rel) > cap).sum()),
                                     pct_capped=100 * float((np.abs(rel) > cap).mean()),
                                     MAE=mae, MAE_capped=mae_c,
                                     MAE_change_pct=100 * (mae - mae_c) / mae))
        cp = pd.DataFrame(rows)
        written(dataio.write_result(cp, "07_cap_sweep.csv"))
        sub("rows touched, and the MAE effect (positive = the cap helps)")
        show(cp[cp.n_capped > 0], "{:,.5f}")
        sub("parameters the cap never touches at any tested level")
        untouched = sorted(set(PARAMS) - set(cp.loc[cp.n_capped > 0, "param"]))
        print("  " + (", ".join(untouched) if untouched else "none"))

        header("7.6 verdict")
        print(f"  moduleb.config.FORECAST_REL_DELTA_CAP is currently "
              f"{config.FORECAST_REL_DELTA_CAP!r} (off).")
        print("  The code path exists, is unit tested, and is a one-line change to enable.")
        print("  It is NOT enabled here, because:")
        print("    - decision D5 froze the configuration so the V1 -> FINAL-01 comparison")
        print("      is attributable to the data;")
        print("    - the one pre-declared calibration change was scoped to Output_Fall_Time")
        print("      and has been executed (stage 6);")
        print("    - enabling it changes frozen_config_digest(), which is exactly how a")
        print("      model change is supposed to announce itself.")
        print("\n  This is a decision for the team, and the evidence for it is the table in")
        print("  7.5. Whatever is decided, it must be decided BEFORE the freeze, because")
        print("  after the holdout run it can no longer be decided honestly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
