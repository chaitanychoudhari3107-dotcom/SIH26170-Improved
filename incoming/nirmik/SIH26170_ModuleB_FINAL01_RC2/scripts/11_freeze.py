"""
Stage 11 — FREEZE.  *** GATED. Read this before running. ***

Running this script fits the final models and envelopes on train + calibration
and writes an immutable artifact. After it runs:

  * no configuration number may change,
  * no runtime-contract behaviour may change,
  * the next and only remaining stage is the one-shot holdout run.

The gate is a required flag rather than a prompt so that the decision is
recorded in whatever the team runs, not in someone's terminal history:

    python scripts/11_freeze.py --team-signoff "<who approved, and when>"

The sign-off is now part of the manifest that is BUILT BEFORE the artifact is
serialised, so it is embedded in the joblib itself and the sidecar JSON is
written from the same dict. Stage 12 compares the two and refuses a mismatch,
a missing sign-off, or a rehearsal placeholder.

Before running, the following must be true:

  1. stage 0 passes (environment, hashes, decisions, unit tests)
  2. stage 3 has been reviewed — the frozen V1 rerun on FINAL-01
  3. stage 6 has been executed — the pre-declared fall-time decision is spent
  4. every recorded release decision still holds (D1, D10, D11, D12, D13, D14)
  5. stage 10 passes — the rehearsal ran clean

The script re-checks 1, 3 and 4 mechanically, including that
`FORECAST_REL_DELTA_CAP` is still `None` (D11). It cannot check that a human
looked at 2 and 5, which is what --team-signoff is for.
"""
from _common import ROOT, Stage, header, show, written

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from moduleb import config, dataio, decisions, freeze, serving
from moduleb.constants import PARAMS

MODEL_PATH = ROOT / "models" / "module_b_final01.joblib"
RECEIPT_PATH = ROOT / "models" / "FREEZE_RECEIPT.json"
RELEASE_MANIFEST = ROOT / "RELEASE_MANIFEST.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--team-signoff", required=True,
                    help="who approved the freeze, and when. Embedded in the artifact.")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing frozen artifact (needs a reason too)")
    ap.add_argument("--reason", default="", help="why a re-freeze is justified")
    a = ap.parse_args()

    with Stage("STAGE 11 — FREEZE"):
        if MODEL_PATH.exists() and not a.force:
            raise SystemExit(
                f"A frozen artifact already exists at {MODEL_PATH}.\n"
                "Re-freezing after a holdout run destroys the blindness of the evaluation.\n"
                "If this is a legitimate pre-holdout re-freeze, pass --force with --reason.")
        if a.force and not a.reason:
            raise SystemExit("--force requires --reason")
        if a.team_signoff.strip() == freeze.REHEARSAL_SIGNOFF:
            raise SystemExit("that is the rehearsal placeholder, not a team sign-off.")

        header("11.1 pre-flight — unit tests")
        r = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"],
                           cwd=ROOT, capture_output=True, text=True)
        print(f"  unit tests: {r.stdout.strip().splitlines()[-1] if r.stdout else 'no output'}")
        if r.returncode != 0:
            raise SystemExit("unit tests fail; not freezing")

        header("11.2 pre-flight — the pre-declared decision")
        dec = dataio.RESULTS / "06_predeclared_falltime_decision.csv"
        if not dec.exists():
            raise SystemExit(
                "the pre-declared Output_Fall_Time decision has not been executed.\n"
                "Run scripts/06_predeclared_falltime_rule.py first — it must be decided on\n"
                "calibration, and it cannot be decided after the holdout.")
        d = pd.read_csv(dec).iloc[0]
        print(f"  pre-declared fall-time rule: {d.decision} "
              f"(gain {d.gain_pct:+.2f}%, lots {d.lots_won}/{d.n_lots})")
        expected = d.move_to if d.rule_fires else d.from_set
        actual = config.RECOMMENDED["Output_Fall_Time"]["features"]
        if actual != expected:
            raise SystemExit(
                f"moduleb.config says Output_Fall_Time uses {actual!r} but the executed "
                f"pre-declared rule says {expected!r}. Reconcile before freezing.")
        print(f"  moduleb.config agrees: Output_Fall_Time uses {actual!r}")

        header("11.3 pre-flight — every recorded release decision")
        failures = decisions.check_release_decisions()
        for dd in decisions.RELEASE_DECISIONS:
            state = "FAIL" if any(f.startswith(dd.id + ":") for f in failures) else "holds"
            print(f"  [{state:5s}] {dd.id:4s} {dd.statement}")
        if failures:
            for f in failures:
                print(f"    {f}")
            raise SystemExit(
                "a recorded release decision no longer holds; not freezing. "
                "Reconcile the code with docs/DECISION_LOG.md, or record a new decision.")
        print(f"  FORECAST_REL_DELTA_CAP = {config.FORECAST_REL_DELTA_CAP!r}  (D11: must be None)")

        header("11.4 digests")
        print(f"  model config     {config.frozen_config_digest()}")
        print(f"  runtime contract {serving.runtime_contract_digest()}")
        print(f"  source tree      {freeze.source_tree_digest()}")
        release_manifest_digest = None
        if RELEASE_MANIFEST.exists():
            rm = json.loads(RELEASE_MANIFEST.read_text())
            release_manifest_digest = rm.get("release_manifest_digest")
            print(f"  release manifest {release_manifest_digest}")
        else:
            print("  release manifest MISSING — run scripts/15_release_manifest.py first")
            raise SystemExit("RELEASE_MANIFEST.json is part of the freeze provenance")

        header("11.5 inputs")
        tr = dataio.load_split("train")
        ca = dataio.load_split("calibration")
        base, limits = dataio.load_specs()
        print("  " + tr.describe())
        print("  " + ca.describe())

        header("11.6 fitting the final models on train + calibration")
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        man = freeze.freeze(tr, ca, base, limits, MODEL_PATH,
                            team_signoff=a.team_signoff,
                            release_state=freeze.PRODUCTION,
                            refreeze_reason=a.reason or None)
        show(pd.DataFrame(man["config"]).T.rename_axis("param").reset_index())
        print(f"\n  rows {man['n_train_rows']}  lots {man['n_train_lots']}")
        print(f"  envelope offsets: "
              f"{ {p: round(man['envelope']['offsets'][p], 5) for p in PARAMS} }")
        print(f"  team sign-off embedded in the artifact: {man['team_signoff']!r}")
        written(MODEL_PATH)
        written(MODEL_PATH.with_suffix(".manifest.json"))

        header("11.7 verify what was just written")
        art = freeze.load_frozen(MODEL_PATH, require_production=True)
        print("  reloaded through load_frozen: both digests match, the manifest verifies")
        print("  against its own digest, and the embedded and sidecar manifests agree")

        RECEIPT_PATH.write_text(json.dumps(dict(
            receipt="FREEZE_RECEIPT",
            module="B",
            release_candidate=__import__("moduleb").RELEASE_CANDIDATE,
            artifact_filename=MODEL_PATH.name,
            artifact_sha256=dataio.file_sha256(MODEL_PATH),
            model_config_digest=man["frozen_config_digest"],
            runtime_contract_digest=man["runtime_contract_digest"],
            source_tree_digest=man["source_tree_digest"],
            manifest_digest=man["manifest_digest"],
            release_manifest_digest=release_manifest_digest,
            team_signoff=man["team_signoff"],
            refreeze_reason=man["refreeze_reason"],
            frozen_at_utc=man["frozen_at_utc"],
            receipt_written_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            environment=man["environment"],
            dataset=man["dataset"],
            release_decisions=man["release_decisions"],
            holdout_prediction_state="UNSPENT",
        ), indent=2))
        written(RECEIPT_PATH)

        header("11.8 FROZEN")
        print("  From this point the only remaining action is:")
        print("      python scripts/12_predict_holdout.py --frozen")
        print("  Run it once. Send the output and its prediction receipt to Sanskruti.")
        print("  Do not retune after seeing any holdout error, and do not re-freeze")
        print("  afterwards.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
