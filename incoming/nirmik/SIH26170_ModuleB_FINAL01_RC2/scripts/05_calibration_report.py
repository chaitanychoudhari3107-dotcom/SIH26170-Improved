"""
Stage 5 — score the frozen configuration on the 12 calibration lots.

The calibration lots were never trained on and share no lot and no component_id
with train. So this is a genuinely held-out score, and it is the last honest
estimate of holdout performance the team gets before the holdout itself.

What this stage is NOT for: redesigning the model around whatever it shows.
The V1 protocol allows exactly one pre-declared decision at this point, and that
decision is executed in stage 6. Everything here is measurement.

Two numbers to compare, and they answer different questions:

  internal whole-lot CV on train   how the model does on unseen lots drawn from
                                   the same 42 it was tuned against
  calibration                      how it does on 12 lots from a different draw,
                                   with the model fitted on all 42 train lots

A calibration score meaningfully worse than the CV score means the CV was
optimistic. A calibration score better usually just means these 12 lots are
easier. Both are expected to differ; the size of the gap is the signal.
"""
from _common import Stage, header, show, sub, written

import numpy as np
import pandas as pd

from moduleb import baselines, config, cv, dataio, metrics, models
from moduleb.constants import PARAMS
from moduleb.features import add_features, make_folds
from moduleb.guards import assert_lots_disjoint


def main() -> int:
    with Stage("STAGE 5 — held-out calibration score"):
        tr = dataio.load_split("train")
        ca = dataio.load_split("calibration")
        base, _ = dataio.load_specs()
        assert_lots_disjoint(tr.frame, ca.frame, name_a="train", name_b="calibration")

        ftr = add_features(tr.frame, base)
        ftr["fold"] = make_folds(ftr, config.N_FOLDS)
        fca = add_features(ca.frame, base)

        header("5.0 what is being scored")
        print(f"  fitted on   : {len(ftr)} rows / {ftr.lot_id.nunique()} lots (train)")
        print(f"  scored on   : {len(fca)} rows / {fca.lot_id.nunique()} lots (calibration)")
        print(f"  lot overlap : none (checked)")
        print(f"  config      : frozen, digest {config.frozen_config_digest()[:16]}")

        header("5.1 internal whole-lot CV on TRAIN, for reference")
        cvres, _ = cv.cross_validate(ftr, config.RECOMMENDED, with_baselines=True)
        cv_all = (cvres[(cvres.variant == "ALL") & (cvres.model.isin(
            ["MODULE_B", "MedianRatio_24h"]))]
            .pivot(index="param", columns="model", values="MAE").loc[PARAMS])
        show(cv_all.reset_index(), "{:,.5f}")

        header("5.2 held-out CALIBRATION score")
        rows = []
        preds = {}
        for p in PARAMS:
            obj = models.fit_one(ftr, p, config.RECOMMENDED[p])
            yh = models.predict_one(obj, fca, p)
            preds[p] = yh
            ratios = baselines.median_ratio_fit(ftr, p)
            mr = baselines.median_ratio_predict(ratios, fca, p)
            y = fca[f"{p}_168h"].to_numpy(float)
            lots = fca.lot_id.to_numpy()
            rows.append(dict(param=p, variant="ALL", model="MODULE_B",
                             **metrics.metrics(y, yh, lots)))
            rows.append(dict(param=p, variant="ALL", model="MedianRatio_24h",
                             **metrics.metrics(y, mr, lots)))
            for v in sorted(fca.device_variant.unique()):
                s = (fca.device_variant == v).to_numpy()
                rows.append(dict(param=p, variant=v, model="MODULE_B",
                                 **metrics.metrics(y[s], yh[s], lots[s])))
                rows.append(dict(param=p, variant=v, model="MedianRatio_24h",
                                 **metrics.metrics(y[s], mr[s], lots[s])))
        cal = pd.DataFrame(rows)
        written(dataio.write_result(cal, "05_calibration_metrics.csv"))
        show(cal[cal.variant == "ALL"], "{:,.5f}")

        header("5.3 calibration vs internal CV — did the CV flatter the model?")
        cal_all = (cal[(cal.variant == "ALL") & (cal.model == "MODULE_B")]
                   .set_index("param").MAE.loc[PARAMS])
        cmp = pd.DataFrame({
            "cv_train_MAE": cv_all.MODULE_B,
            "calibration_MAE": cal_all,
        })
        cmp["calibration_minus_cv_pct"] = 100 * (cmp.calibration_MAE - cmp.cv_train_MAE) / cmp.cv_train_MAE
        cmp["cal_vs_medianratio_pct"] = 100 * (
            cal[(cal.variant == "ALL") & (cal.model == "MedianRatio_24h")]
            .set_index("param").MAE.loc[PARAMS] - cal_all) / cal[
            (cal.variant == "ALL") & (cal.model == "MedianRatio_24h")].set_index("param").MAE.loc[PARAMS]
        show(cmp.reset_index(), "{:,.5f}")
        written(dataio.write_result(cmp.reset_index(), "05_calibration_vs_cv.csv"))

        header("5.4 paired per-lot test on the calibration lots")
        print("12 lots, so this test has much less power than the 42-lot train CV.")
        print("Treat a non-significant p here as 'not enough lots to tell', not as a")
        print("contradiction of stage 3.")
        rows = []
        for p in PARAMS:
            ratios = baselines.median_ratio_fit(ftr, p)
            mr = baselines.median_ratio_predict(ratios, fca, p)
            t = metrics.paired_lot_test(fca[f"{p}_168h"].to_numpy(float), preds[p], mr,
                                        fca.lot_id.to_numpy())
            t.update(param=p, verdict=metrics.verdict(t, config.TIE_THRESHOLD_PCT,
                                                      config.PAIRED_TEST_ALPHA))
            rows.append(t)
        pt = pd.DataFrame(rows)[["param", "macro_lot_mae_a", "macro_lot_mae_b",
                                 "gain_pct", "n_lots", "lots_won", "wilcoxon_p", "verdict"]]
        show(pt.rename(columns={"macro_lot_mae_a": "MacroLotMAE_module_b",
                                "macro_lot_mae_b": "MacroLotMAE_median_ratio"}), "{:,.5f}")
        written(dataio.write_result(pt, "05_calibration_paired_test.csv"))

        header("5.5 does the CV preserve the BASELINE-RELATIVE effect?")
        print("Added 19 Sep 2026 — review finding F7. Section 5.3 compares absolute MAE")
        print("between CV and calibration, which is confounded by whether these 12 lots")
        print("are intrinsically easier. The quantity that actually has to transfer is the")
        print("per-lot ADVANTAGE over median-ratio. This compares that distribution")
        print("directly, using permitted train and calibration data only.")
        rows = []
        for p in PARAMS:
            oof = cv.out_of_fold_predictions(ftr, p, config.RECOMMENDED[p])
            mr_tr = baselines.fold_baselines(ftr, p, ftr.fold.to_numpy())["MedianRatio_24h"]
            tr_adv = (metrics.per_lot_mae(ftr[f"{p}_168h"].to_numpy(float), mr_tr,
                                          ftr.lot_id.to_numpy())
                      - metrics.per_lot_mae(ftr[f"{p}_168h"].to_numpy(float), oof,
                                            ftr.lot_id.to_numpy()))
            tr_rel = 100 * tr_adv / metrics.per_lot_mae(
                ftr[f"{p}_168h"].to_numpy(float), mr_tr, ftr.lot_id.to_numpy())

            ratios = baselines.median_ratio_fit(ftr, p)
            mr_ca = baselines.median_ratio_predict(ratios, fca, p)
            ca_adv = (metrics.per_lot_mae(fca[f"{p}_168h"].to_numpy(float), mr_ca,
                                          fca.lot_id.to_numpy())
                      - metrics.per_lot_mae(fca[f"{p}_168h"].to_numpy(float), preds[p],
                                            fca.lot_id.to_numpy()))
            ca_rel = 100 * ca_adv / metrics.per_lot_mae(
                fca[f"{p}_168h"].to_numpy(float), mr_ca, fca.lot_id.to_numpy())

            rows.append(dict(
                param=p,
                cv_median_lot_advantage_pct=float(np.median(tr_rel)),
                cv_lots_won=int((tr_rel > 0).sum()), cv_n_lots=int(len(tr_rel)),
                cal_median_lot_advantage_pct=float(np.median(ca_rel)),
                cal_lots_won=int((ca_rel > 0).sum()), cal_n_lots=int(len(ca_rel)),
                shift_pct_points=float(np.median(ca_rel) - np.median(tr_rel)),
            ))
        adv = pd.DataFrame(rows)
        show(adv, "{:,.2f}")
        written(dataio.write_result(adv, "05_relative_effect_transfer.csv"))
        print("\nA parameter whose per-lot advantage holds between the two columns is one")
        print("the CV described honestly. A large negative shift means the CV over-stated")
        print("the advantage on lots it had never seen, which is the failure mode section")
        print("5.3 cannot detect on its own.")

        header("5.6 per-lot detail — which calibration lots are hard?")
        rows = []
        for p in PARAMS:
            per = metrics.per_lot_mae(fca[f"{p}_168h"].to_numpy(float), preds[p],
                                      fca.lot_id.to_numpy())
            for lot, m in per.items():
                rows.append(dict(param=p, lot_id=lot, MAE=m,
                                 variant=fca.loc[fca.lot_id == lot, "device_variant"].iloc[0],
                                 n=int((fca.lot_id == lot).sum())))
        pl = pd.DataFrame(rows)
        written(dataio.write_result(pl, "05_calibration_per_lot.csv"))
        show(pl.pivot(index="lot_id", columns="param", values="MAE")[PARAMS].reset_index(),
             "{:,.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
