"""
Stage 4 — the controlled grid. EVIDENCE ONLY; it changes nothing.

24 configurations: 2 structures x 4 model families x 3 feature sets, scored on
the same whole-lot folds as stage 3. This is deliberately a small, enumerable
grid rather than a hyper-parameter search. Blind optimisation over 42 lots would
find differences that are fold noise, and the team rule already says anything
under 5% MAE is a tie.

Nothing in this script writes to moduleb.config. If the grid says some other
configuration wins, that is an input to a team decision under the V1 freeze
protocol, not a licence to edit the frozen block. Read stage 6 for the one
change that IS pre-declared and therefore may be executed.

    python scripts/04_benchmark_grid.py            # full grid
    python scripts/04_benchmark_grid.py --quick    # linear models only, no GBR
"""
from _common import Stage, header, show, sub, written

import argparse
import time

import numpy as np
import pandas as pd

from moduleb import config, cv, dataio, metrics
from moduleb.baselines import fold_baselines
from moduleb.constants import PARAMS
from moduleb.features import add_features, make_folds
from moduleb.models import MODEL_NAMES
from moduleb.featureset import FEATURE_SETS


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="skip the GBR configurations")
    a = ap.parse_args()

    with Stage("STAGE 4 — controlled configuration grid (evidence only)"):
        tr = dataio.load_split("train")
        base, _ = dataio.load_specs()
        feat = add_features(tr.frame, base)
        feat["fold"] = make_folds(feat, config.N_FOLDS)

        model_names = [m for m in MODEL_NAMES if not (a.quick and m == "GBR")]
        grid = {}
        for structure in ("pooled", "per-variant"):
            for model in model_names:
                for fs in FEATURE_SETS:
                    grid[f"{structure}/{model}/{fs}"] = dict(
                        structure=structure, model=model, features=fs)
        print(f"{len(grid)} configurations x {len(PARAMS)} parameters "
              f"x {config.N_FOLDS} whole-lot folds")

        # baselines once, on the same folds
        mr = {p: fold_baselines(feat, p, feat.fold.to_numpy())["MedianRatio_24h"]
              for p in PARAMS}

        rows, t0 = [], time.time()
        for i, (tag, cfg) in enumerate(grid.items(), 1):
            res, oof = cv.cross_validate(feat, {p: cfg for p in PARAMS},
                                         with_baselines=False)
            for p in PARAMS:
                t = metrics.paired_lot_test(feat[f"{p}_168h"].to_numpy(float),
                                            oof[p], mr[p], feat.lot_id.to_numpy())
                rows.append(dict(config=tag, param=p, MAE=t["mae_a"],
                                 gain_vs_medianratio_pct=t["gain_pct"],
                                 lots_won=t["lots_won"], n_lots=t["n_lots"],
                                 wilcoxon_p=t["wilcoxon_p"],
                                 verdict=metrics.verdict(t, config.TIE_THRESHOLD_PCT,
                                                         config.PAIRED_TEST_ALPHA)))
            print(f"  [{i:2d}/{len(grid)}] {tag:32s} {time.time() - t0:6.1f}s")

        g = pd.DataFrame(rows)
        written(dataio.write_result(g, "04_grid.csv"))

        header("4.1 MAE by configuration and parameter")
        show(g.pivot(index="config", columns="param", values="MAE")[PARAMS].reset_index(),
             "{:,.5f}")

        header("4.2 % gain over median-ratio, by configuration")
        show(g.pivot(index="config", columns="param",
                     values="gain_vs_medianratio_pct")[PARAMS].reset_index(), "{:,.2f}")

        header("4.3 best configuration per parameter, and the frozen one")
        frozen_tag = {p: f"{config.RECOMMENDED[p]['structure']}/"
                         f"{config.RECOMMENDED[p]['model']}/{config.RECOMMENDED[p]['features']}"
                      for p in PARAMS}
        out = []
        for p in PARAMS:
            sub_g = g[g.param == p].sort_values("MAE")
            best = sub_g.iloc[0]
            frozen = sub_g[sub_g.config == frozen_tag[p]].iloc[0]
            out.append(dict(
                param=p, frozen_config=frozen_tag[p], frozen_MAE=frozen.MAE,
                best_config=best.config, best_MAE=best.MAE,
                best_minus_frozen_pct=100 * (frozen.MAE - best.MAE) / frozen.MAE,
                frozen_verdict=frozen.verdict, best_verdict=best.verdict))
        cmpdf = pd.DataFrame(out)
        show(cmpdf, "{:,.5f}")
        written(dataio.write_result(cmpdf, "04_best_vs_frozen.csv"))

        print("\nRead `best_minus_frozen_pct` against the 5% tie rule. A best-in-grid")
        print("configuration that beats the frozen one by less than that is the grid")
        print("finding fold noise, and switching to it would be exactly the leaderboard")
        print("behaviour the V1 protocol was written to prevent.")
        big = cmpdf[cmpdf.best_minus_frozen_pct >= config.TIE_THRESHOLD_PCT]
        if len(big):
            print("\nConfigurations that clear the tie threshold and therefore deserve a")
            print("team decision (NOT applied by this script):")
            show(big, "{:,.3f}")
        else:
            print("\nNo configuration clears the tie threshold against the frozen one.")
            print("The frozen configuration stands on this evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
