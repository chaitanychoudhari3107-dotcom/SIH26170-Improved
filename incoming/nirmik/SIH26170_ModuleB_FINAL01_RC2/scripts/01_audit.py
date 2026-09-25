"""
Stage 1 — audit FINAL-01 before any model touches it.

This answers one question: is anything here a DATA BUG that Chaitany needs to
know about, as opposed to a modelling problem Module B has to live with? The
distinction is set out in docs/DATA_BUG_VS_MODEL_PROBLEM.md and it is not a
matter of taste — "the MAE is worse than I hoped" is never a data bug.

Everything checked here is checked again by moduleb.guards on every load. This
script exists so the numbers are visible and reviewable, not because the
pipeline depends on someone reading them.

The holdout is NOT opened. Its row shown in the structure table comes from the
declared moduleb.holdout_manifest, and the two holdout separation checks move to
stage 12, where the file is legitimately open and the frozen manifest names the
lots the model was actually trained on. That is a stronger check than this one,
not a weaker one: it compares the delivery against the artifact rather than
against another file (decision D14).
"""
from _common import Stage, header, show, sub, written

import numpy as np
import pandas as pd

from moduleb import dataio, holdout_manifest
from moduleb.constants import PARAMS, PREDICTOR_COLS, TARGET_COLS
from moduleb.features import add_features, make_folds
from moduleb.guards import assert_lots_disjoint
from moduleb import config


def structural_table(splits) -> pd.DataFrame:
    rows = []
    for s in splits.values():
        d = s.frame
        num = d[PREDICTOR_COLS + ([c for c in TARGET_COLS if c in d.columns])]
        rows.append(dict(
            split=s.name, rows=len(d), lots=d.lot_id.nunique(),
            variants=d.device_variant.nunique(),
            cols=len(d.columns),
            dup_component_id=int(d.component_id.duplicated().sum()),
            nulls=int(d.isna().sum().sum()),
            nonpositive=int((num <= 0).sum().sum()),
            cols_96h=len([c for c in d.columns if "96" in c]),
            has_all_targets=all(c in d.columns for c in TARGET_COLS),
            min_rows_per_lot=int(d.groupby("lot_id").size().min()),
            max_rows_per_lot=int(d.groupby("lot_id").size().max()),
        ))
    rows.append(dict(
        split="holdout (declared, not read)",
        rows=holdout_manifest.N_ROWS, lots=holdout_manifest.N_LOTS,
        variants=len(set(["CMOS_A", "CMOS_B", "CMOS_C"])),
        cols=holdout_manifest.N_COLUMNS,
        dup_component_id=0, nulls=0, nonpositive=0,
        cols_96h=len([c for c in holdout_manifest.COLUMNS if "96" in c]),
        has_all_targets=holdout_manifest.HAS_TARGETS,
        min_rows_per_lot=holdout_manifest.ROWS_PER_LOT_MIN,
        max_rows_per_lot=holdout_manifest.ROWS_PER_LOT_MAX,
    ))
    return pd.DataFrame(rows)


def main() -> int:
    with Stage("STAGE 1 — audit SIH26170-FINAL-01"):
        splits = {n: dataio.load_split(n) for n in ("train", "calibration")}
        base, limits = dataio.load_specs()
        holdout_manifest.verify_delivery_hash(dataio.file_sha256(dataio.PATHS["holdout"]))

        header("1.1 structure")
        show(structural_table(splits), "{:,.0f}")
        print("\nRead: zero nulls, zero duplicate ids, zero non-positive measurements and")
        print("zero 96h columns are the four that would be escalations. `has_all_targets`")
        print("must be True for train/calibration and False for holdout — a holdout file")
        print("carrying answers would itself be a data bug. The holdout row is the DECLARED")
        print("structure from moduleb.holdout_manifest, verified against the delivery hash;")
        print("this stage does not open the file (decision D14).")

        header("1.2 lot balance by variant")
        for n, s in splits.items():
            t = s.frame.groupby("device_variant").agg(
                lots=("lot_id", "nunique"), rows=("component_id", "size"))
            print(f"\n{n}:")
            print(t.to_string())

        header("1.3 whole-lot separation between splits")
        for a, b in [("train", "calibration")]:
            assert_lots_disjoint(splits[a].frame, splits[b].frame, name_a=a, name_b=b)
            print(f"  {a:12s} vs {b:12s}  no shared lot, no shared component_id  OK")
        print("  train/holdout and calibration/holdout: deferred to stage 12, which is the")
        print("  only stage allowed to open the holdout. It asserts the delivered holdout")
        print("  lots are disjoint from the lots recorded in the frozen artifact's own")
        print("  manifest — the artifact, not a second file, is the thing that must not")
        print("  have seen them.")

        header("1.4 column contract")
        d = splits["train"].frame
        print(f"  predictors present     : {len(PREDICTOR_COLS)}/12")
        print(f"  targets present (train): {sum(c in d.columns for c in TARGET_COLS)}/6")
        print(f"  targets in holdout     : "
              f"{sum(c in holdout_manifest.COLUMNS for c in TARGET_COLS)}/6 "
              "(must be 0; declared header)")
        extra = sorted(set(d.columns) - set(PREDICTOR_COLS) - set(TARGET_COLS)
                       - {"component_id", "lot_id", "device_family", "device_variant"})
        print(f"  unexpected columns     : {extra or 'none'}")

        header("1.5 Device_Specs coverage")
        cov = limits.notna().astype(int)
        cov.loc["cells_with_limit"] = cov.sum()
        print(cov.to_string())
        n_missing = int(limits.isna().to_numpy().sum())
        print(f"\n  variant x parameter cells with NO static_spec_max: {n_missing} of 18")
        print("  Per decision D1 these stay empty. No limit is invented for them, and the")
        print("  limit-based reason codes never fire there. Inventing one would create")
        print("  authoritative-looking false positives.")

        header("1.6 measurement ranges by variant")
        rows = []
        for v, g in splits["train"].frame.groupby("device_variant"):
            for p in PARAMS:
                rows.append(dict(
                    variant=v, param=p,
                    spec_baseline_0h=float(base.loc[v, p]),
                    min_0h=g[f"{p}_0h"].min(), med_0h=g[f"{p}_0h"].median(),
                    max_0h=g[f"{p}_0h"].max(),
                    med_168h=g[f"{p}_168h"].median(),
                    static_limit=float(limits.loc[v, p]) if pd.notna(limits.loc[v, p]) else np.nan,
                ))
        rng = pd.DataFrame(rows)
        show(rng, "{:,.4f}")
        written(dataio.write_result(rng, "01_ranges_by_variant.csv"))

        header("1.7 static-limit headroom (context for Module A and fusion, not a Module B job)")
        rows = []
        for split_name in ("train", "calibration"):
            g = splits[split_name].frame
            for v in sorted(g.device_variant.unique()):
                sel = g.device_variant == v
                for p in PARAMS:
                    lim = limits.loc[v, p]
                    if pd.isna(lim):
                        continue
                    y = g.loc[sel, f"{p}_168h"]
                    rows.append(dict(split=split_name, variant=v, param=p, limit=float(lim),
                                     n=int(sel.sum()),
                                     n_breach_168h=int((y >= lim).sum()),
                                     max_frac_of_limit=float((y / lim).max())))
        hd = pd.DataFrame(rows)
        show(hd, "{:,.4f}")
        n_cells = int(hd.n.sum())
        print(f"\n  168h static breaches: {int(hd.n_breach_168h.sum())} component x parameter")
        print(f"  cells out of {n_cells} checkable ones "
              f"({100 * hd.n_breach_168h.sum() / n_cells:.2f}%), across "
              f"{hd.loc[hd.n_breach_168h > 0, ['variant', 'param']].drop_duplicates().shape[0]} "
              "distinct variant x parameter combinations.")
        print("  Candidate V1 had 5 breaches, all in CMOS_C propagation delay. FINAL-01")
        print("  spreads them, which is generator change 5 landing. Module B does not act")
        print("  on this — it is the fusion layer's context — but it is what makes the")
        print("  B_FORECAST_EXCEEDS_LIMIT code able to fire at all.")
        written(dataio.write_result(hd, "01_limit_headroom.csv"))

        header("1.8 fold construction")
        feat = add_features(splits["train"].frame, base)
        feat["fold"] = make_folds(feat, config.N_FOLDS)
        fold_tab = feat.groupby(["fold", "device_variant"]).lot_id.nunique().unstack(fill_value=0)
        fold_tab["rows"] = feat.groupby("fold").size()
        print(fold_tab.to_string())
        print(f"\n  {config.N_FOLDS} folds, whole lots only, deterministic from the lot names.")
        written(dataio.write_result(fold_tab.reset_index(), "01_folds.csv"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
