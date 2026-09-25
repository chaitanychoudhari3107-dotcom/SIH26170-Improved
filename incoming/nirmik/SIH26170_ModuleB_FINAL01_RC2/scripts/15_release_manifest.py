"""
Stage 15 — build RELEASE_MANIFEST.json, the release candidate's identity card.

One file that answers, without this chat and without running anything: which
dataset, which code, which serving contract, which decisions, which limitations,
how many tests passed, how many documented claims were verified, whether the
holdout has been spent, and whether anyone has signed off.

It is written BEFORE the freeze and it records `release_state` as
`READY_FOR_TEAM_SIGNOFF` with `team_signoff: PENDING` — because that is true.
Stage 11 refuses to freeze without this file and carries its digest into the
freeze receipt, so the artifact and the manifest cannot drift apart afterwards.

    python scripts/15_release_manifest.py            # runs tests + claim checker
    python scripts/15_release_manifest.py --reuse    # reuse the recorded results

`--reuse` exists for the clean-room audit, where the tests have just been run
and running them twice proves nothing.

Order matters here, and it is deliberate. The manifest's digests are written
FIRST, then the tests and the claim checker run against them, then the
verification block is filled in and the manifest rewritten. Doing it the other
way round needs two passes to converge — the checker compares the manifest's
digests with the live code, so on a first pass it is either absent or stale —
and a step that only works when you run it twice is a step someone will run once.
"""
from _common import ROOT, Stage, header, written

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import moduleb
from moduleb import config, dataio, decisions, freeze, holdout_manifest, serving
from moduleb.constants import DATASET_ID

MANIFEST = ROOT / "RELEASE_MANIFEST.json"
MODEL_PATH = ROOT / "models" / "module_b_final01.joblib"
HOLDOUT_OUT = ROOT / "results" / "ModuleB_Final_Holdout_Predictions.csv"


def _run(cmd) -> tuple[int, str]:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def test_status() -> dict:
    rc, out = _run([sys.executable, "-m", "pytest", "tests/", "-q"])
    m = re.search(r"(\d+) passed", out)
    f = re.search(r"(\d+) failed", out)
    return dict(status="PASS" if rc == 0 else "FAIL",
                passed=int(m.group(1)) if m else 0,
                failed=int(f.group(1)) if f else 0)


def claim_status() -> dict:
    rc, out = _run([sys.executable, str(ROOT / "scripts" / "14_verify_claims.py")])
    m = re.search(r"(\d+) passed, (\d+) failed, (\d+) checks", out)
    return dict(status="PASS" if rc == 0 else "FAIL",
                passed=int(m.group(1)) if m else 0,
                failed=int(m.group(2)) if m else 0,
                checks=int(m.group(3)) if m else 0)


def _receipts() -> dict:
    """The freeze and prediction receipts, by hash, when they exist."""
    out = {}
    for label, p in (("freeze", ROOT / "models" / "FREEZE_RECEIPT.json"),
                     ("holdout_prediction", ROOT / "results" / "HOLDOUT_PREDICTION_RECEIPT.json"),
                     ("prediction_output", HOLDOUT_OUT)):
        out[label] = (dict(filename=p.name, sha256=dataio.file_sha256(p),
                           bytes=p.stat().st_size) if p.exists() else None)
    return out


def _signoff() -> dict:
    """Read the sign-off from the frozen artifact, never from a constant.

    Before the freeze there is nothing to read and the state is PENDING. After it,
    the authority is the artifact's own embedded manifest — not this script, and not
    a document someone could edit.
    """
    side = MODEL_PATH.with_suffix(".manifest.json")
    if not side.exists():
        return dict(state="PENDING", recorded=None,
                    note="Stage 11 embeds the genuine sign-off in the frozen artifact's "
                         "manifest. Module B does not manufacture it.")
    man = json.loads(side.read_text())
    return dict(state="RECORDED", recorded=man.get("team_signoff"),
                frozen_at_utc=man.get("frozen_at_utc"),
                source="embedded manifest of models/module_b_final01.joblib",
                note="Read from the frozen artifact, which is the authority for it.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reuse", action="store_true",
                    help="reuse the recorded test/claim results instead of rerunning")
    a = ap.parse_args()

    prev_verification = None
    if MANIFEST.exists():
        try:
            prev_verification = json.loads(MANIFEST.read_text())["verification"]
        except Exception:
            prev_verification = None

    with Stage("STAGE 15 — release manifest"):
        header("15.1 decisions")
        failures = decisions.check_release_decisions()
        if failures:
            for f in failures:
                print(f"  FAIL {f}")
            raise SystemExit("a recorded release decision no longer holds")
        print(f"  all {len(decisions.RELEASE_DECISIONS)} recorded decisions hold")

        header("15.2 build")
        meta = dataio.load_dataset_version()
        inputs = {}
        for name in ("train", "calibration", "holdout", "specs", "dictionary",
                     "contract", "version"):
            p = dataio.PATHS[name]
            inputs[name] = dict(filename=p.name, bytes=p.stat().st_size,
                                sha256=dataio.file_sha256(p))

        man = dict(
            manifest="RELEASE_MANIFEST",
            project="SIH 26170 — AI-driven anomaly detection in component burn-in "
                    "and screening",
            module="B — 168 h drift forecasting from 0 h + 24 h",
            owner="Nirmik",
            release_candidate=moduleb.RELEASE_CANDIDATE,
            package_version=moduleb.__version__,
            release_state=("HOLDOUT_PREDICTION_DELIVERED" if HOLDOUT_OUT.exists()
                           else "FROZEN" if MODEL_PATH.exists()
                           else "READY_FOR_TEAM_SIGNOFF"),
            built_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),

            dataset=dict(id=DATASET_ID, status=meta["status"],
                         generator_version_public=meta["generator_version_public"],
                         split_id=meta["split_id"], rows=meta["rows"], lots=meta["lots"],
                         join_key=meta["join_key"]),
            inputs=inputs,

            digests=dict(
                model_config=config.frozen_config_digest(),
                runtime_contract=serving.runtime_contract_digest(),
                source_tree=freeze.source_tree_digest(),
                input_contract=freeze._digest_of(
                    serving.runtime_contract_payload()["input_contract"]),
                output_contract=freeze._digest_of(
                    serving.runtime_contract_payload()["output_contract"]),
            ),
            serving_contract=serving.runtime_contract_payload(),

            verification=dict(tests=dict(status="PENDING", passed=0, failed=0),
                              claim_check=dict(status="PENDING", passed=0, failed=0,
                                               checks=0)),
            release_decisions=decisions.decision_state(),
            known_limitations=list(decisions.KNOWN_LIMITATIONS),
            holdout_access_provenance=dict(holdout_manifest.PROVENANCE),
            holdout=dict(declared=holdout_manifest.as_dict()["sha256"],
                         n_rows=holdout_manifest.N_ROWS,
                         n_lots=holdout_manifest.N_LOTS,
                         prediction_state=("SPENT" if HOLDOUT_OUT.exists() else "UNSPENT"),
                         content_readers=list(holdout_manifest.CONTENT_READERS)),
            frozen_artifact_present=MODEL_PATH.exists(),
            receipts=_receipts(),
            team_signoff=_signoff(),
            next_actions=(
                ["Send ModuleB_Final_Holdout_Predictions.csv + "
                 "HOLDOUT_PREDICTION_RECEIPT.json to Sanskruti for blind scoring.",
                 "Send models/FREEZE_RECEIPT.json to Chaitany for the archive.",
                 "Send the prediction file to Anushka only if final fusion needs it.",
                 "Change nothing in response to the scores. The one-shot is spent."]
                if HOLDOUT_OUT.exists() else
                ["Team reviews this release candidate.",
                 "Genuine team sign-off.",
                 'python scripts/11_freeze.py --team-signoff "<who approved, and when>"',
                 "python scripts/12_predict_holdout.py --frozen   (once, and only once)",
                 "Send the prediction output + HOLDOUT_PREDICTION_RECEIPT.json to Sanskruti."]
            ),
        )
        def _seal(m: dict) -> dict:
            m["release_manifest_digest"] = hashlib.sha256(
                json.dumps({k: v for k, v in m.items()
                            if k not in ("release_manifest_digest", "built_utc")},
                           sort_keys=True, separators=(",", ":"), default=str).encode()
            ).hexdigest()
            return m

        # Written before verification runs, so the claim checker compares the live
        # code against a manifest that already describes it.
        MANIFEST.write_text(json.dumps(_seal(man), indent=2) + "\n")

        header("15.3 verification")
        if a.reuse and prev_verification is not None:
            tests, claims = prev_verification["tests"], prev_verification["claim_check"]
            print("  reusing the recorded results")
        else:
            tests = test_status()
            claims = claim_status()
        print(f"  tests        {tests['status']}  {tests['passed']} passed, "
              f"{tests['failed']} failed")
        print(f"  claim check  {claims['status']}  {claims['passed']}/{claims['checks']}")
        man["verification"] = dict(tests=tests, claim_check=claims)
        MANIFEST.write_text(json.dumps(_seal(man), indent=2) + "\n")
        if tests["status"] != "PASS" or claims["status"] != "PASS":
            raise SystemExit(
                "verification is not green. The manifest records the failure rather "
                "than being quietly left at the last green state; fix it and rerun.")
        print(f"  release candidate  {man['release_candidate']}")
        print(f"  release state      {man['release_state']}")
        print(f"  model digest       {man['digests']['model_config'][:32]}")
        print(f"  runtime digest     {man['digests']['runtime_contract'][:32]}")
        print(f"  source digest      {man['digests']['source_tree'][:32]}")
        print(f"  manifest digest    {man['release_manifest_digest'][:32]}")
        print(f"  holdout prediction {man['holdout']['prediction_state']}")
        print(f"  team signoff       {man['team_signoff']['state']}")
        written(MANIFEST)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
