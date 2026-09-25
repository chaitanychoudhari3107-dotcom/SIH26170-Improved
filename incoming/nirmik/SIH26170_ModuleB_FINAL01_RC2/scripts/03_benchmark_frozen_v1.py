"""
Stage 3 — rerun the Candidate V1 frozen configuration on FINAL-01, UNCHANGED.

This is the honesty stage. Decision D5 (15 Sep 2026) says: when the new dataset
lands, run the same benchmark with no configuration changes, so any difference
is attributable to the data rather than to model shopping. Nothing in
moduleb.config's FROZEN_V1 block has been touched to produce this table.

What gets reported, and why each one:

  MAE                the official primary metric
  vs MedianRatio     the baseline that actually matters — one constant per
                     variant per parameter. Beating persistence is trivial;
                     beating this is the question.
  lots won           of the held-out lots, how many the model wins. 42 lots is
                     the honest sample size, not 3,151 rows.
  Wilcoxon p         paired signed-rank over per-lot MAEs.
  verdict            BETTER / TIE / WORSE under the team's own rule: differences
                     under 5% MAE are ties whatever the rank or the p-value.

A tie is a real and reportable result. If the frozen model ties the median-ratio
baseline on a parameter, the defensible thing to say is that a single constant
is as good as the model there — not to go looking for a configuration that
breaks the tie.
"""
from _common import Stage, header, show, sub, written

import numpy as np
import pandas as pd

from moduleb import config, cv, dataio, metrics, models
from moduleb.constants import PARAMS
from moduleb.features import add_features, make_folds


def main() -> int:
    with Stage("STAGE 3 — frozen Candidate-V1 configuration on FINAL-01"):
        tr = dataio.load_split("train")
        base, _ = dataio.load_specs()
        feat = add_features(tr.frame, base)
        feat["fold"] = make_folds(feat, config.N_FOLDS)

        header("3.0 the configuration being run (unchanged from the V1 freeze)")
        cfg = pd.DataFrame(config.RECOMMENDED).T.rename_axis("param").reset_index()
        show(cfg)
        print(f"\nHuber: {config.HUBER}")
        print(f"folds: {config.N_FOLDS} whole-lot   seed: {config.GLOBAL_SEED}")
        print(f"frozen config digest: {config.frozen_config_digest()[:32]}")

        header("3.1 whole-lot cross-validation, all models, all variants")
        res, oof = cv.cross_validate(feat, config.RECOMMENDED, with_baselines=True)
        res.insert(0, "dataset", "SIH26170-FINAL-01")
        written(dataio.write_result(res, "03_cv_metrics.csv"))

        piv = (res[res.variant == "ALL"]
               .pivot(index="param", columns="model", values="MAE")
               .loc[PARAMS, ["Persistence", "LinExtrap", "MedianRatio_24h", "MODULE_B"]])
        piv["MODULE_B_vs_MedianRatio_pct"] = 100 * (
            piv.MedianRatio_24h - piv.MODULE_B) / piv.MedianRatio_24h
        sub("pooled over variants — MAE in native units, and % gain over median-ratio")
        show(piv.reset_index(), "{:,.5f}")

        header("3.2 the paired per-lot test — the number to quote")
        print("Held-out lots are the unit of independence. 42 lots, not 3,151 rows.")
        print("The MAE columns here are MACRO-LOT means — every lot weighted equally.")
        print("They differ slightly from the row-weighted pooled MAE in 3.1 because the")
        print("lots are not the same size. Quote the right one for the claim being made.")
        rows = []
        for p in PARAMS:
            y = feat[f"{p}_168h"].to_numpy(float)
            mr = np.full(len(feat), np.nan)
            folds = feat.fold.to_numpy()
            from moduleb.baselines import fold_baselines
            mr = fold_baselines(feat, p, folds)["MedianRatio_24h"]
            t = metrics.paired_lot_test(y, oof[p], mr, feat.lot_id.to_numpy())
            t.update(param=p,
                     verdict=metrics.verdict(t, config.TIE_THRESHOLD_PCT,
                                             config.PAIRED_TEST_ALPHA))
            rows.append(t)
        pt = pd.DataFrame(rows)[["param", "macro_lot_mae_a", "macro_lot_mae_b",
                                 "gain_pct", "n_lots", "lots_won", "wilcoxon_p", "verdict"]]
        pt = pt.rename(columns={"macro_lot_mae_a": "MacroLotMAE_module_b",
                                "macro_lot_mae_b": "MacroLotMAE_median_ratio"})
        show(pt, "{:,.5f}")
        written(dataio.write_result(pt, "03_paired_lot_test.csv"))

        header("3.3 per-variant breakdown — is one variant carrying the result?")
        pv = (res[(res.model == "MODULE_B") & (res.variant != "ALL")]
              .pivot(index="param", columns="variant", values="MAE").loc[PARAMS])
        mrv = (res[(res.model == "MedianRatio_24h") & (res.variant != "ALL")]
               .pivot(index="param", columns="variant", values="MAE").loc[PARAMS])
        gain = (100 * (mrv - pv) / mrv).round(2)
        gain.columns = [f"gain%_{c}" for c in gain.columns]
        show(pd.concat([pv, gain], axis=1).reset_index(), "{:,.5f}")
        written(dataio.write_result(pd.concat([pv, gain], axis=1).reset_index(),
                                    "03_per_variant.csv"))

        header("3.4 stability and bias — the two things a pooled MAE hides")
        stab = (res[(res.variant == "ALL") & (res.model.isin(["MODULE_B", "MedianRatio_24h"]))]
                [["param", "model", "MAE", "MedAE", "P90AE", "RMSE", "MeanSignedError",
                  "UnderPredRate", "MacroLotMAE", "WorstLotMAE", "nMAE_pct"]])
        show(stab, "{:,.5f}")
        print("\nMeanSignedError < 0 means the forecast is systematically LOW. For a")
        print("screening context that is the dangerous direction, so it is reported")
        print("next to the MAE rather than buried in a results file.")
        print("WorstLotMAE / MacroLotMAE is the spread across held-out lots: a ratio far")
        print("above 1 means one lot is much harder than the rest.")

        header("3.5 how close is this to the measurement-noise floor?")
        print("If the forecast error were driven entirely by the declared measurement")
        print("noise, MAE would be about 0.8 x CV x level. The ratio below says how much")
        print("room is left. A ratio near 1 means the parameter is essentially solved;")
        print("a large ratio means real predictable drift is being missed.")
        rows = []
        for p in PARAMS:
            lvl = float(np.median(feat[f"{p}_168h"]))
            floor = 0.7979 * config.NOISE_CV[p] * lvl      # E|N(0,s)| = s*sqrt(2/pi)
            mae = float(piv.loc[p, "MODULE_B"])
            rows.append(dict(param=p, median_168h=lvl, assumed_noise_floor_MAE=floor,
                             module_b_MAE=mae, ratio_to_floor=mae / floor))
        cl = pd.DataFrame(rows)
        show(cl, "{:,.5f}")
        written(dataio.write_result(cl, "03_noise_floor.csv"))

        header("3.6 optimiser convergence")
        if models.CONVERGENCE_ISSUES:
            show(pd.DataFrame(models.CONVERGENCE_ISSUES))
            print("\nWARNING: at least one Huber fit stopped on max_iter rather than")
            print("converging. Its coefficients are not a solved optimum. Raising")
            print("max_iter is a FROZEN_V1 change and needs a decision, not a quiet edit.")
        else:
            print("  all fits converged within max_iter — no capped optimisations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
