"""
Stage 10 — rehearse the freeze and the holdout run WITHOUT touching the holdout.

The real holdout is a one-shot. If scripts/11 or scripts/12 has a bug, the team
finds out after the only blind run has been spent. So this stage exercises both
code paths end to end on a stand-in:

    freeze on   : train lots only
    predict on  : the calibration file with its 168h columns STRIPPED, which
                  makes it structurally identical to the holdout — same columns,
                  same guard path, no answers.

Because the real calibration answers exist, the rehearsal can also be scored,
which gives a realistic preview of what the holdout run will look like.

The rehearsal artifact is written to a TEMPORARY directory and deleted at the
end, and it is stamped `release_state="REHEARSAL"` with a placeholder sign-off
that `freeze.load_frozen` refuses for any production use. A rehearsal model must
never be able to masquerade as the frozen one, and it must never be left inside
the release package.

03_HOLDOUT_AFTER_FREEZE/ModuleB_Holdout.csv is not opened by this script — not
even its header. The stand-in is checked against the declared column list in
moduleb.holdout_manifest, and the delivery hash is verified without reading a
value (decision D14).
"""
from _common import ROOT, Stage, header, show, sub, written

import numpy as np
import pandas as pd

import shutil
import tempfile
from pathlib import Path

from moduleb import (config, contract, dataio, freeze, holdout_manifest, metrics,
                     predict, serving)
from moduleb.constants import PARAMS, TARGET_COLS
from moduleb.features import add_features

DRY = dataio.RESULTS / "dryrun"


def main() -> int:
    with Stage("STAGE 10 — freeze/predict rehearsal on a stand-in holdout"):
        DRY.mkdir(parents=True, exist_ok=True)
        tmp = Path(tempfile.mkdtemp(prefix="moduleb_rehearsal_"))
        tr = dataio.load_split("train")
        ca = dataio.load_split("calibration")
        base, limits = dataio.load_specs()

        header("10.1 freeze on train lots only, into a temporary directory")
        art_path = tmp / "rehearsal_model.joblib"
        man = freeze.freeze(tr, None, base, limits, art_path,
                            team_signoff=freeze.REHEARSAL_SIGNOFF,
                            release_state=freeze.REHEARSAL)
        print(f"  models + envelopes fitted on {man['n_train_rows']} rows / "
              f"{man['n_train_lots']} lots")
        print(f"  release state      {man['release_state']}  (never a production artifact)")
        print(f"  config digest      {man['frozen_config_digest'][:32]}")
        print(f"  runtime digest     {man['runtime_contract_digest'][:32]}")
        print(f"  emits disposition  {man['emits_disposition']}")
        print(f"  written to         {art_path}  (temporary; deleted at 10.9)")

        header("10.2 reload the artifact through every load-time check")
        art = freeze.load_frozen(art_path, require_production=False)
        print("  model digest, runtime digest, dataset, manifest digest and the")
        print("  embedded/sidecar manifest pair all agree — load_frozen accepted it")
        try:
            freeze.load_frozen(art_path, require_production=True)
        except Exception as exc:
            print(f"  and it is correctly REFUSED for production use: "
                  f"{type(exc).__name__}")
        else:
            raise SystemExit("a REHEARSAL artifact was accepted for production use")

        header("10.3 build a stand-in holdout from the calibration file")
        stand_in = ca.frame.drop(columns=TARGET_COLS).copy()
        print(f"  {len(stand_in)} rows, {len(stand_in.columns)} columns")
        holdout_manifest.verify_delivery_hash(dataio.file_sha256(dataio.PATHS["holdout"]))
        hold_cols = list(holdout_manifest.COLUMNS)
        print("  compared against the DECLARED holdout header, hash-verified; the file")
        print("  itself is not opened")
        same = list(stand_in.columns) == hold_cols
        print(f"  column list identical to the real holdout header: {same}")
        if not same:
            print(f"    stand-in: {list(stand_in.columns)}")
            print(f"    holdout : {hold_cols}")
            raise SystemExit("the stand-in does not match the holdout shape; fix before freezing")
        sip = DRY / "dryrun_standin_holdout.csv"
        stand_in.to_csv(sip, index=False)

        header("10.4 run the real predict path, through the real serving contract")
        att = serving.file_attestation(
            sip, source="stage 10 rehearsal stand-in, built from ModuleB_Calibration.csv",
            n_rows=int(len(stand_in)), n_lots=int(stand_in.lot_id.nunique()))
        out, rep = predict.predict_csv(art, sip, DRY / "dryrun_predictions.csv",
                                       delivery=att)
        for line in rep.lines():
            print("  " + line)
        print(f"  contract columns present: "
              f"{all(c in out.columns for c in contract.CONTRACT_COLS)}")
        print(f"  module_b_disposition absent: {'module_b_disposition' not in out.columns}")
        print(f"  evidence columns: {len([c for c in out.columns if c.startswith('evidence_')])}")
        written(DRY / "dryrun_predictions.csv")

        header("10.5 what the output looks like")
        show(out[contract.CONTRACT_COLS].head(5), "{:,.5f}")

        header("10.6 score the rehearsal against the answers we happen to have")
        print("This is the preview of the holdout run. The real holdout has no answers and")
        print("this comparison will not be possible there — that is the point of doing it")
        print("here instead.")
        rows = []
        feat = add_features(ca.frame, base)
        for p in PARAMS:
            y = feat[f"{p}_168h"].to_numpy(float)
            yh = out[f"predicted_{p}_168h"].to_numpy(float)
            rows.append(dict(param=p, **metrics.metrics(y, yh, feat.lot_id.to_numpy())))
        show(pd.DataFrame(rows), "{:,.5f}")

        header("10.7 determinism — the same input twice gives the same file")
        out2, _ = predict.predict_csv(art, sip, DRY / "dryrun_predictions_2.csv",
                                      delivery=att)
        num = [c for c in contract.CONTRACT_COLS
               if c.startswith(("predicted_", "module_b_p")) and c.endswith("_168h")]
        identical = (np.allclose(out[num].to_numpy(float), out2[num].to_numpy(float),
                                 rtol=0, atol=0)
                     and (out.module_b_reason_codes == out2.module_b_reason_codes).all()
                     and (out.module_b_primary_parameter
                          == out2.module_b_primary_parameter).all())
        print(f"  byte-for-byte identical predictions and codes: {identical}")
        if not identical:
            raise SystemExit("prediction is not deterministic; do not freeze")
        (DRY / "dryrun_predictions_2.csv").unlink()

        header("10.8 the serving contract refuses an incomplete lot")
        lot0 = sorted(stand_in.lot_id.unique())[0]
        full_lot = stand_in[stand_in.lot_id == lot0]
        short = pd.concat([full_lot.iloc[:len(full_lot) - 5],
                           stand_in[stand_in.lot_id != lot0]], ignore_index=True)
        sizes = {str(k): int(v) for k, v in stand_in.groupby("lot_id").size().items()}
        try:
            predict.predict_frame(art, short, expected_lot_sizes=sizes, name="short")
        except serving.IncompleteLotError as exc:
            print(f"  a lot short by 5 of {len(full_lot)} rows is refused, as it should be")
            print(f"  ({str(exc).splitlines()[0][:110]}...)")
        else:
            raise SystemExit("an incomplete lot was accepted; do not freeze")
        _, rep_o = predict.predict_frame(art, short, expected_lot_sizes=sizes,
                                         allow_partial_lot=True, name="short-override")
        print(f"  with the explicit override it proceeds, report.clean = {rep_o.clean}, "
              f"offending lots recorded: {rep_o.completeness['offending_lots']}")

        header("10.9 clean up the rehearsal artifact")
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"  temporary rehearsal directory removed: {tmp}")
        print("  no rehearsal model remains inside the package")

        header("10.10 verdict")
        print("  The freeze path, the digest check, the predict path, the contract")
        print("  validation and the determinism check all pass on a file structurally")
        print("  identical to the holdout.")
        print("  scripts/11_freeze.py and scripts/12_predict_holdout.py are ready to run")
        print("  once the team signs off. The real holdout's contents were not read by this")
        print("  stage — only its delivery hash was verified. The one-shot predictive")
        print("  evaluation is unspent; see moduleb.holdout_manifest for the full recorded")
        print("  access history (decision D14).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
