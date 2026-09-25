"""
Stage 12 — the one-shot holdout run.  *** GATED. ***

    python scripts/12_predict_holdout.py --frozen

This is the ONLY stage permitted to read the contents of
03_HOLDOUT_AFTER_FREEZE/ModuleB_Holdout.csv. It runs the frozen artifact over
it and writes ModuleB_Final_Holdout_Predictions.csv in the exact integration
contract, plus HOLDOUT_PREDICTION_RECEIPT.json so Sanskruti can prove which
release produced the file she is scoring.

Refusals, all deliberate:
  * no frozen artifact             -> stage 11 has not been run
  * model config digest mismatch   -> the fitted model's code has changed
  * runtime contract digest mismatch -> serving behaviour has changed since the
                                      freeze, even if every fitted parameter is
                                      identical
  * missing or placeholder sign-off -> an unapproved artifact is not runnable
  * embedded/sidecar manifest mismatch -> one of them has been edited
  * manifest fails its own digest  -> the manifest was edited after the freeze
  * a REHEARSAL artifact           -> stage 10's disposable model is not this
  * holdout delivery hash mismatch -> not the attested delivery; ask Chaitany
  * a holdout lot appears in the artifact's training lots -> blindness is gone
  * holdout carries 168h columns   -> a data bug; stop and tell Chaitany
  * an output file already exists  -> the one-shot has already been spent

After this runs: send the CSV and the receipt to Sanskruti for blind evaluation,
and the CSV to Anushka only if fusion needs it. Do not ask Sanskruti for the
hidden targets, and do not change anything in response to the errors she
reports. A worse holdout score than calibration is an ordinary result, not a bug.
"""
from _common import ROOT, Stage, header, show, written

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import moduleb
from moduleb import contract, dataio, freeze, holdout_manifest, predict, serving
from moduleb.constants import PARAMS

MODEL_PATH = ROOT / "models" / "module_b_final01.joblib"
OUT_PATH = ROOT / "results" / "ModuleB_Final_Holdout_Predictions.csv"
RECEIPT = ROOT / "results" / "HOLDOUT_PREDICTION_RECEIPT.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frozen", action="store_true", required=True,
                    help="confirm the model is frozen and this is the one-shot run")
    ap.add_argument("--force", action="store_true", help="re-run a spent one-shot")
    a = ap.parse_args()

    with Stage("STAGE 12 — one-shot holdout prediction"):
        if not MODEL_PATH.exists():
            raise SystemExit(f"no frozen artifact at {MODEL_PATH}; run scripts/11_freeze.py")
        if OUT_PATH.exists() and not a.force:
            raise SystemExit(
                f"{OUT_PATH.name} already exists. The holdout run is a one-shot; re-running "
                "it after seeing an evaluation is how a blind test stops being blind.\n"
                "Pass --force only if the first run failed before producing a usable file.")

        header("12.1 load the frozen artifact through every gate")
        art = freeze.load_frozen(MODEL_PATH, require_production=True, check_sidecar=True)
        man = art["manifest"]
        print(f"  release state  {man['release_state']}")
        print(f"  frozen at      {man['frozen_at_utc']}")
        print(f"  signoff        {man['team_signoff']}")
        print(f"  model digest   {man['frozen_config_digest'][:32]}  (matches current code)")
        print(f"  runtime digest {man['runtime_contract_digest'][:32]}  (matches current code)")
        print(f"  manifest       verifies against its own digest; sidecar agrees")
        print(f"  trained on     {man['n_train_rows']} rows / {man['n_train_lots']} lots")

        header("12.2 verify the holdout delivery, then open it")
        holdout_sha = dataio.file_sha256(dataio.PATHS["holdout"])
        holdout_manifest.verify_delivery_hash(holdout_sha)
        print(f"  delivery hash matches the declared manifest: {holdout_sha[:32]}")
        print("  this is the first and only stage that reads the contents")
        ho = dataio.load_split("holdout")     # allow_target=False; raises if answers present
        print("  " + ho.describe())
        print("  guards passed: no 96h column, no hidden labels, no 168h targets")
        if (len(ho.frame) != holdout_manifest.N_ROWS
                or ho.frame.lot_id.nunique() != holdout_manifest.N_LOTS):
            raise SystemExit(
                f"the holdout delivery is {len(ho.frame)} rows / "
                f"{ho.frame.lot_id.nunique()} lots; the declared manifest says "
                f"{holdout_manifest.N_ROWS} / {holdout_manifest.N_LOTS}. Stop and ask "
                "Chaitany which delivery is current.")

        header("12.3 blindness — the artifact never saw these lots")
        trained = set(man["train_lots"])
        overlap = sorted(set(ho.frame.lot_id) & trained)
        if overlap:
            raise SystemExit(
                f"{len(overlap)} holdout lot(s) appear in the frozen artifact's training "
                f"lots: {overlap[:5]}. This evaluation would not be blind. Stop.")
        print(f"  {ho.frame.lot_id.nunique()} holdout lots, none of them among the "
              f"{len(trained)} lots the artifact was fitted on")

        header("12.4 predict, under the serving contract")
        delivery = serving.DeliveryAttestation(
            source="Chaitany · SIH26170-FINAL-01 holdout delivery, declared in "
                   "moduleb.holdout_manifest",
            sha256=holdout_manifest.SHA256,
            n_rows=holdout_manifest.N_ROWS,
            n_lots=holdout_manifest.N_LOTS)
        out, rep = predict.predict_frame(art, ho.frame, allow_target=False,
                                         delivery=delivery, file_sha256=holdout_sha,
                                         name="holdout")
        for line in rep.lines():
            print("  " + line)
        if not rep.clean:
            print("  NOTE the run is not clean; every clip and override is listed above "
                  "and is recorded in the receipt.")

        header("12.5 contract check")
        ref = dataio.expected_contract_columns()
        problems = contract.check_against_reference(out, ref)
        if problems:
            for p in problems:
                print(f"  FAIL {p}")
            raise SystemExit("output does not match ModuleB_Output_Contract.csv")
        print(f"  all {len(ref)} contract columns present, in order")
        print(f"  {len([c for c in out.columns if c.startswith('evidence_')])} evidence columns")
        print(f"  module_b_disposition absent: {'module_b_disposition' not in out.columns}")
        print(f"  rows: {len(out)} (holdout has {len(ho.frame)})")

        header("12.6 summary of what is being sent")
        flagged = (out.module_b_reason_codes != "").sum()
        print(f"  components carrying at least one reason code: {flagged} "
              f"({100 * flagged / len(out):.2f}%)")
        print("\n  primary parameter distribution:")
        print(out.module_b_primary_parameter.value_counts().reindex(PARAMS, fill_value=0)
              .to_string())
        show(out[contract.CONTRACT_COLS].head(5), "{:,.5f}")

        out.to_csv(OUT_PATH, index=False)
        RECEIPT.write_text(json.dumps(dict(
            receipt="HOLDOUT_PREDICTION_RECEIPT",
            module="B",
            release_candidate=moduleb.RELEASE_CANDIDATE,
            dataset=man["dataset"],
            frozen_artifact_filename=MODEL_PATH.name,
            frozen_artifact_sha256=dataio.file_sha256(MODEL_PATH),
            model_config_digest=man["frozen_config_digest"],
            runtime_contract_digest=man["runtime_contract_digest"],
            source_tree_digest=man["source_tree_digest"],
            manifest_digest=man["manifest_digest"],
            team_signoff=man["team_signoff"],
            holdout_input_filename=Path(dataio.PATHS["holdout"]).name,
            holdout_input_sha256=holdout_sha,
            prediction_output_filename=OUT_PATH.name,
            prediction_output_sha256=dataio.file_sha256(OUT_PATH),
            n_rows=int(len(out)), n_lots=int(ho.frame.lot_id.nunique()),
            n_components_flagged=int(flagged),
            serving=rep.as_dict(),
            run_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            environment=man["environment"],
            statement=(
                "These forecasts were produced from 0 h and 24 h measurements only, by "
                "the frozen artifact identified above, in a single run. No 168 h target, "
                "no hidden ground truth and no scoring information of any kind was "
                "available to, read by, or used by this run — the holdout file carries no "
                "answers and Module B has never held them. Nothing was tuned after this "
                "run; the model is spent."),
        ), indent=2))
        written(OUT_PATH)
        written(RECEIPT)

        header("12.7 send")
        print("  Sanskruti : ModuleB_Final_Holdout_Predictions.csv + "
              "HOLDOUT_PREDICTION_RECEIPT.json,")
        print("              for blind evaluation against the hidden 168h targets.")
        print("              Do not ask for the targets.")
        print("  Anushka   : the same prediction file, only if final fusion needs it,")
        print("              plus docs/INTEGRATION_NOTE.md for the backend interface.")
        print("\n  The model is spent. Any change from here is a new model with a new")
        print("  digest, and it cannot be evaluated on this holdout.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
