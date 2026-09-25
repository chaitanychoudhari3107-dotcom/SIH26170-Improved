"""
Stage 2 — is the thing Module B has to predict actually learnable?

Module B is asked to predict the 24h->168h movement from what is visible by 24h.
Three quantities decide whether that is possible at all, and none of them is the
MAE:

  1. how big the late movement is relative to the early movement,
  2. how strongly the early movement predicts the late movement,
  3. how much of the late movement is a whole-LOT effect rather than a
     per-component one.

(3) matters because a lot effect is the one thing a lot-context feature can
capture, and because Riddhi's Module A assumes lot-relative structure exists.

A note on correlations, carried over from the V1 audit and still true: a high
raw 0h<->168h LEVEL correlation is not evidence of a problem. A physical
component should keep most of its baseline ordering through burn-in. The
question is whether the DRIFT is learnable, which is what is measured here.
All correlations are computed WITHIN variant; pooling A/B/C would manufacture
correlation out of the three different baselines alone.
"""
from _common import Stage, header, show, written

import numpy as np
import pandas as pd

from moduleb import config, dataio
from moduleb.constants import PARAMS
from moduleb.features import add_features


def main() -> int:
    with Stage("STAGE 2 — drift and lot structure"):
        tr = dataio.load_split("train")
        base, _ = dataio.load_specs()
        feat = add_features(tr.frame, base)

        header("2.1 early vs late movement, by variant and parameter")
        rows = []
        for v, g in feat.groupby("device_variant"):
            for p in PARAMS:
                x0 = g[f"{p}_0h"].to_numpy(float)
                x24 = g[f"{p}_24h"].to_numpy(float)
                y = g[f"{p}_168h"].to_numpy(float)
                early = (x24 - x0) / x0
                late = (y - x24) / x24
                rows.append(dict(
                    variant=v, param=p,
                    early_med_pct=100 * np.median(early),
                    late_med_pct=100 * np.median(late),
                    late_over_early=float(np.median(late) / np.median(early))
                    if np.median(early) != 0 else np.nan,
                    early_sd_pct=100 * early.std(ddof=1),
                    late_sd_pct=100 * late.std(ddof=1),
                    neg_step_0_24_pct=100 * float((x24 < x0).mean()),
                    r_early_late=float(np.corrcoef(early, late)[0, 1]),
                    r2_early_late=float(np.corrcoef(early, late)[0, 1] ** 2),
                ))
        el = pd.DataFrame(rows)
        show(el, "{:,.4f}")
        written(dataio.write_result(el, "02_early_late.csv"))
        print("\nr_early_late measures the LINEAR same-parameter early->late relationship.")
        print("It is a diagnostic, not a ceiling: a low r does not rule out a nonlinear or")
        print("multivariate route to the same target (corrected 19 Sep, review finding F6).")
        print("r2 is the share of late-drift variance the linear fit explains: a parameter")
        print("with r2 near")
        print("zero is not a modelling failure, it is a parameter whose late drift is simply")
        print("not visible at 24h. Saying so is part of the job.")

        header("2.2 implied drift exponent (is drift linear in time?)")
        print("Fitting late_total ~ (t/24)^k against the median 0->24 and 0->168 moves.")
        rows = []
        for v, g in feat.groupby("device_variant"):
            for p in PARAMS:
                x0 = g[f"{p}_0h"].to_numpy(float)
                d24 = np.median((g[f"{p}_24h"].to_numpy(float) - x0) / x0)
                d168 = np.median((g[f"{p}_168h"].to_numpy(float) - x0) / x0)
                k = np.log(d168 / d24) / np.log(168 / 24) if d24 > 0 and d168 > 0 else np.nan
                rows.append(dict(variant=v, param=p, d24_pct=100 * d24, d168_pct=100 * d168,
                                 implied_exponent_k=k))
        dk = pd.DataFrame(rows)
        show(dk, "{:,.4f}")
        written(dataio.write_result(dk, "02_drift_exponent.csv"))
        print("\nk = 1 is linear, k < 1 sub-linear (the physically expected shape for burn-in:")
        print("fast early settling, then slowing). k is also exactly what the LinExtrap")
        print("baseline assumes to be 1, which is why it is expected to overshoot.")

        header("2.3 how much of the late drift is a LOT effect?")
        print("Variance of per-component late relative drift decomposed into between-lot")
        print("and within-lot, computed inside each variant so the three baselines cannot")
        print("masquerade as lot structure.")
        rows = []
        for v, g in feat.groupby("device_variant"):
            for p in PARAMS:
                late = ((g[f"{p}_168h"].to_numpy(float) - g[f"{p}_24h"].to_numpy(float))
                        / g[f"{p}_24h"].to_numpy(float))
                s = pd.Series(late, index=g.lot_id.to_numpy())
                lot_mean = s.groupby(level=0).mean()
                n = s.groupby(level=0).size()
                grand = s.mean()
                ss_between = float((n * (lot_mean - grand) ** 2).sum())
                ss_total = float(((s - grand) ** 2).sum())
                rows.append(dict(variant=v, param=p, n_lots=int(len(lot_mean)),
                                 lot_var_share_pct=100 * ss_between / ss_total if ss_total else np.nan))
        lv = pd.DataFrame(rows)
        show(lv, "{:,.3f}")
        written(dataio.write_result(lv, "02_lot_variance_share.csv"))
        print("\nOn Candidate V1 this sat at 1.3-5.1%, which is why the V1 review asked for")
        print("stronger lot ageing (accepted as generator change 1). Compare the numbers")
        print("above with that range: it is the direct measurement of whether change 1 landed.")

        header("2.4 cross-parameter structure of the DRIFT, within variant")
        print("Correlation of late relative drift between parameters. This is the mechanism")
        print("behind the timing group's own+lot+cross feature set — if delay/rise/fall")
        print("share a latent slew factor, one another's early moves carry information.")
        for v, g in feat.groupby("device_variant"):
            late = pd.DataFrame({
                p: (g[f"{p}_168h"].to_numpy(float) - g[f"{p}_24h"].to_numpy(float))
                   / g[f"{p}_24h"].to_numpy(float) for p in PARAMS})
            print(f"\n{v}:")
            print(late.corr().round(3).to_string())

        header("2.5 do OTHER parameters' early moves predict this one's late drift?")
        print("Maximum |correlation| between this parameter's late drift and any OTHER")
        print("parameter's 0->24h move, within variant. This is the cross-feature payoff,")
        print("measured directly rather than inferred from the benchmark.")
        rows = []
        for v, g in feat.groupby("device_variant"):
            early = pd.DataFrame({p: g[f"reldelta_{p}"].to_numpy(float) for p in PARAMS})
            for p in PARAMS:
                late = ((g[f"{p}_168h"].to_numpy(float) - g[f"{p}_24h"].to_numpy(float))
                        / g[f"{p}_24h"].to_numpy(float))
                cors = {q: abs(float(np.corrcoef(early[q], late)[0, 1]))
                        for q in PARAMS if q != p}
                best = max(cors, key=cors.get)
                rows.append(dict(variant=v, param=p, own_early_r=abs(float(
                    np.corrcoef(early[p], late)[0, 1])),
                    best_cross=best, best_cross_r=cors[best]))
        cx = pd.DataFrame(rows)
        show(cx, "{:,.4f}")
        written(dataio.write_result(cx, "02_cross_early_signal.csv"))

        header("2.6 early-signal-to-noise: is the 0->24h move bigger than the noise?")
        print("The declared measurement CV is an ASSUMPTION from the design record, not a")
        print("measurement. Noise on a delta is CV*sqrt(2). A parameter whose typical early")
        print("move is below that has no early signal to read, however good the model.")
        rows = []
        for v, g in feat.groupby("device_variant"):
            for p in PARAMS:
                early = np.abs(g[f"reldelta_{p}"].to_numpy(float))
                noise = config.NOISE_CV[p] * np.sqrt(2)
                rows.append(dict(variant=v, param=p,
                                 median_abs_early_move_pct=100 * float(np.median(early)),
                                 assumed_delta_noise_pct=100 * noise,
                                 snr=float(np.median(early) / noise),
                                 pct_below_noise=100 * float((early < noise).mean())))
        sn = pd.DataFrame(rows)
        show(sn, "{:,.4f}")
        written(dataio.write_result(sn, "02_early_snr.csv"))
        print("\nOn Candidate V1, Input_Leakage_Current sat at SNR ~0.7-0.9 — noise-dominated.")
        print("That was raised as generator change 2. These rows are the check on it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
