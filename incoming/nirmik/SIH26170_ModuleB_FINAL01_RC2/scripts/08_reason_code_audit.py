"""
Stage 8 — the false-positive audit of the B_ reason codes.

Module B's forecasts get checked against a target. Its reason codes do not:
there is no label saying "this component deserved a flag", and by design there
never will be, because the hidden truth is Sanskruti's and the disposition is
fusion's. So the only discipline available is the one applied here — measure how
often each code fires, and refuse to ship a code that fires so often it carries
no information.

The bar, from moduleb.config:
    MAX_FLAG_FIRING_RATE   any single code, on any one parameter or overall
    MAX_ANY_FLAG_RATE      fraction of components carrying at least one code

These are not statistical thresholds. They are a statement about what an
operator can act on. A flag on 2% of a lot is a worklist; a flag on 40% is
wallpaper.

Two further properties are checked structurally rather than by rate, because
they are guarantees rather than tendencies:
  * no limit-based code fires for a variant x parameter cell with no
    static_spec_max — nothing is invented for the seven empty cells;
  * B_NO_EARLY_SIGNAL never appears alone.
"""
from _common import Stage, header, show, sub, written

import numpy as np
import pandas as pd

from moduleb import config, contract, cv, dataio, envelope, models, reason_codes
from moduleb.constants import PARAMS
from moduleb.features import add_features, make_folds


def audit(feat, preds, env, limits, label):
    primary, codes, fired = reason_codes.build_reason_codes(feat, preds, limits, env)
    rates = reason_codes.firing_rates(fired)
    rates.insert(0, "split", label)
    return primary, codes, fired, rates


def main() -> int:
    with Stage("STAGE 8 — reason-code false-positive audit"):
        tr = dataio.load_split("train")
        ca = dataio.load_split("calibration")
        base, limits = dataio.load_specs()
        ftr = add_features(tr.frame, base)
        ftr["fold"] = make_folds(ftr, config.N_FOLDS)
        fca = add_features(ca.frame, base)

        header("8.0 how the two audits differ")
        print("  train_oof   : out-of-fold point forecasts, envelope fitted on all train")
        print("                lots. The envelope is therefore mildly optimistic here.")
        print("  calibration : model and envelope fitted on train only, scored on 12 lots")
        print("                that share no lot and no component with train. This is the")
        print("                honest number; the train row is context.")

        fitted = {p: models.fit_one(ftr, p, config.RECOMMENDED[p]) for p in PARAMS}
        envs = {p: envelope.fit_envelope(ftr, p, config.RECOMMENDED[p]) for p in PARAMS}

        oof = {p: cv.out_of_fold_predictions(ftr, p, config.RECOMMENDED[p]) for p in PARAMS}
        env_tr = {p: np.maximum(envelope.predict_envelope(envs[p], ftr, p), oof[p])
                  for p in PARAMS}
        cal = {p: models.predict_one(fitted[p], fca, p) for p in PARAMS}
        env_ca = {p: np.maximum(envelope.predict_envelope(envs[p], fca, p), cal[p])
                  for p in PARAMS}

        _, codes_tr, fired_tr, rates_tr = audit(ftr, oof, env_tr, limits, "train_oof")
        primary_ca, codes_ca, fired_ca, rates_ca = audit(fca, cal, env_ca, limits, "calibration")
        rates = pd.concat([rates_tr, rates_ca], ignore_index=True)
        written(dataio.write_result(rates, "08_reason_code_rates.csv"))

        header("8.1 firing rate of each code, overall")
        overall = rates[rates.param == "ANY"].pivot(index="code", columns="split",
                                                    values="rate")
        show(overall.reset_index(), "{:,.4f}")

        header("8.2 firing rate by code and parameter (calibration)")
        byp = rates_ca[rates_ca.param != "ANY"].pivot(index="code", columns="param",
                                                      values="rate")[PARAMS]
        show(byp.reset_index(), "{:,.4f}")

        header("8.3 how many codes does a flagged component carry?")
        n_codes = fired_ca.sum(axis=1)
        dist = n_codes.value_counts().sort_index()
        print(pd.DataFrame({"n_codes": dist.index, "components": dist.to_numpy(),
                            "pct": (100 * dist / len(fired_ca)).round(2).to_numpy()}
                           ).to_string(index=False))

        header("8.4 primary parameter distribution")
        print("Every component gets a primary parameter, flagged or not. A wildly uneven")
        print("distribution would mean the scale-free z is not doing its job.")
        pp = (pd.crosstab(primary_ca.to_numpy(), fca.device_variant.to_numpy())
              .reindex(PARAMS, fill_value=0))
        pp["total"] = pp.sum(axis=1)
        pp["pct"] = (100 * pp.total / len(fca)).round(2)
        print(pp.to_string())

        header("8.5 STRUCTURAL CHECK — no invented limits")
        problems = []
        for p in PARAMS:
            no_lim = limits.index[limits[p].isna()].tolist()
            if not no_lim:
                continue
            sel = fca.device_variant.isin(no_lim).to_numpy()
            for code in ("B_FORECAST_EXCEEDS_LIMIT", "B_ENVELOPE_REACHES_LIMIT"):
                n = int(fired_ca.loc[sel, f"{code}:{p}"].sum())
                print(f"  {code}:{p:24s} variants without a limit {no_lim} -> fired {n} times")
                if n:
                    problems.append(f"{code}:{p}")
        if problems:
            raise SystemExit(f"FAIL: limit codes fired where no static limit exists: {problems}")
        print("\n  PASS — no limit-based code fires for any of the seven empty cells.")

        header("8.6 STRUCTURAL CHECK — the qualifier never stands alone")
        q = fired_ca[[c for c in fired_ca.columns if c.startswith("B_NO_EARLY_SIGNAL")]].any(axis=1)
        other = fired_ca[[c for c in fired_ca.columns
                          if not c.startswith("B_NO_EARLY_SIGNAL")]].any(axis=1)
        alone = int((q & ~other).sum())
        print(f"  components carrying B_NO_EARLY_SIGNAL with no risk flag: {alone}")
        if alone:
            raise SystemExit("FAIL: B_NO_EARLY_SIGNAL fired alone")
        print("  PASS")

        header("8.7 ACCEPTANCE")
        fails = []
        for _, r in rates_ca.iterrows():
            if r.code == "ANY_CODE":
                if r.rate > config.MAX_ANY_FLAG_RATE:
                    fails.append(f"{r.rate:.1%} of components carry at least one code "
                                 f"(max {config.MAX_ANY_FLAG_RATE:.0%})")
            elif r.rate > config.MAX_FLAG_FIRING_RATE:
                fails.append(f"{r.code}:{r.param} fires on {r.rate:.1%} "
                             f"(max {config.MAX_FLAG_FIRING_RATE:.0%})")
        any_rate = float(rates_ca.loc[(rates_ca.code == "ANY_CODE"), "rate"].iloc[0])
        print(f"  components carrying at least one code : {any_rate:.2%} "
              f"(limit {config.MAX_ANY_FLAG_RATE:.0%})")
        print(f"  highest single-code rate              : "
              f"{rates_ca[rates_ca.code != 'ANY_CODE'].rate.max():.2%} "
              f"(limit {config.MAX_FLAG_FIRING_RATE:.0%})")
        if fails:
            for f in fails:
                print(f"  FAIL  {f}")
            raise SystemExit("reason codes are too common to be evidence")
        print("\n  PASS — every code clears the pre-declared sparsity gate. Sparsity limits")
        print("  alert flooding; it does not establish precision, recall or actionability,")
        print("  and Module B has no correctness label for its own codes (finding A1).")

        header("8.8 a sample of what integration will actually receive")
        out = contract.build_output(fca, cal, limits, env_ca)
        flagged = out[out.module_b_reason_codes != ""]
        cols = ["component_id", "module_b_primary_parameter", "module_b_reason_codes"]
        print(flagged[cols].head(15).to_string(index=False))
        print(f"\n  {len(flagged)} of {len(out)} calibration components carry any code.")
        written(dataio.write_result(out, "08_calibration_contract_sample.csv"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
