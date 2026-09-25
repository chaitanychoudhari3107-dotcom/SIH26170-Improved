"""
Stage 9 — measure the p95 envelope on FINAL-01. Do not inherit the V1 numbers.

The claim that has to be tested, and the claim that must NOT be made:

  TESTED    marginal coverage — over all components, what fraction of true 168h
            values fall at or below the emitted upper bound. A calibrated
            conformal envelope should land near tau.
  NOT MADE  "95% of defective parts are caught". That is conditional coverage on
            the tail, it is a different quantity, and on Candidate V1 it measured
            ~0.38 at tau = 0.95. It is measured again here rather than assumed.

If tail coverage is low, the honest conclusion is that the envelope is evidence
for fusion and not a screen. That conclusion is already written into the model
card; this stage is what entitles the team to keep writing it.

CORRECTIVE RUN, 19 Sep 2026 — review finding F3
------------------------------------------------
Until 18 Sep this stage ranked the "tail" by the forecast residual
`y_true - point` while describing it as the worst-drifting decile. Those are
different populations, and the definition moved whenever the forecast moved.
The tail is now ranked by observed relative drift from 24 h, `(y_true - x24)/x24`.

The 18 Sep numbers are preserved as
`results/09_envelope_coverage_SUPERSEDED_2026-09-18_residual_ranked.csv`.
They are not wrong arithmetic; they measure a different quantity than the one
the documents claimed. Do not quote them as tail coverage.
"""
from _common import Stage, header, show, sub, written

import numpy as np
import pandas as pd

from moduleb import config, dataio, envelope, models
from moduleb.constants import PARAMS
from moduleb.features import add_features

TAUS = (0.90, 0.95, 0.99)


def main() -> int:
    with Stage("STAGE 9 — prediction-envelope coverage"):
        tr = dataio.load_split("train")
        ca = dataio.load_split("calibration")
        base, _ = dataio.load_specs()
        ftr = add_features(tr.frame, base)
        fca = add_features(ca.frame, base)

        header("9.0 method")
        print("  CORRECTIVE RUN (F3): the tail is ranked by observed relative drift")
        print("  from 24h, not by forecast residual. See the module docstring.")
        print("  conformalised GBR quantile regression (CQR)")
        print(f"  conformal set  : {config.ENVELOPE_CONF_LOTS} whole training lots held back")
        print(f"  operating tau  : {config.ENVELOPE_TAU}")
        print("  scored on      : the 12 calibration lots, unseen by the model and by the")
        print("                   conformal calibration set")

        point = {p: models.predict_one(models.fit_one(ftr, p, config.RECOMMENDED[p]), fca, p)
                 for p in PARAMS}

        header("9.1 coverage at the operating point and two alternatives")
        rows = []
        for tau in TAUS:
            for p in PARAMS:
                env = envelope.fit_envelope(ftr, p, config.RECOMMENDED[p], tau=tau)
                up = np.maximum(envelope.predict_envelope(env, fca, p), point[p])
                rep = envelope.coverage_report(fca[f"{p}_168h"].to_numpy(float), up,
                                               point[p], fca[f"{p}_24h"].to_numpy(float))
                rows.append(dict(tau=tau, param=p, conformal_offset=env.offset, **rep))
        cov = pd.DataFrame(rows)
        written(dataio.write_result(cov, "09_envelope_coverage.csv"))

        sub("marginal coverage — should land near tau")
        show(cov.pivot(index="param", columns="tau", values="marginal_coverage")
             .loc[PARAMS].reset_index(), "{:,.4f}")

        sub("TAIL coverage — the worst-drifting decile. This is NOT tau and never was.")
        show(cov.pivot(index="param", columns="tau", values="tail_coverage")
             .loc[PARAMS].reset_index(), "{:,.4f}")

        sub("mean width as a fraction of the point forecast — the price of each tau")
        show(cov.pivot(index="param", columns="tau", values="mean_rel_width")
             .loc[PARAMS].reset_index(), "{:,.4f}")

        header("9.2 the operating point in full")
        op = cov[cov.tau == config.ENVELOPE_TAU][
            ["param", "n", "marginal_coverage", "tail_coverage", "n_tail",
             "mean_width", "median_width", "mean_rel_width", "conformal_offset"]]
        show(op, "{:,.5f}")

        header("9.3 what may and may not be said about these numbers")
        marg = op.set_index("param").marginal_coverage
        tail = op.set_index("param").tail_coverage
        print(f"  marginal coverage range : {marg.min():.3f} to {marg.max():.3f} "
              f"(target {config.ENVELOPE_TAU})")
        print(f"  tail coverage range     : {tail.min():.3f} to {tail.max():.3f}")
        print()
        print("  MAY be said: the envelope is marginally calibrated — across the whole")
        print("  population its stated level is close to the level it delivers.")
        print()
        print("  MUST NOT be said: that it catches 95% of the parts that drift worst.")
        print("  The tail row above is the measurement of exactly that, and it is far")
        print("  below the nominal level. A part inside its p95 envelope is not thereby")
        print("  safe. The envelope is evidence for fusion; the outlier judgement belongs")
        print("  to Module A.")
        worst = tail.idxmin()
        print(f"\n  Worst case: {worst}, tail coverage {tail[worst]:.3f}. If anyone builds a")
        print("  fusion rule that treats 'inside the envelope' as a pass, that parameter is")
        print("  where it will fail first. Anushka needs this sentence, not just the CSV.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
