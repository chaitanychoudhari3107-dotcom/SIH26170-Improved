"""Stage 11 — write RELEASE_MANIFEST.json and SHA256SUMS.txt."""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import sklearn

from _common import MODELS, PREDICTION, RESULTS, ROOT
from modulea import config
from modulea.freeze import sha256_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", default=os.environ.get("SIH26170_RELEASE", ""),
                        help="release root, so the recorded test count is the full "
                             "suite rather than the release-dependent tests skipped")
    args = parser.parse_args()
    if not args.release:
        raise SystemExit("pass --release (or set SIH26170_RELEASE) so the manifest "
                         "records the full test suite, not a partially skipped run")
    files = sorted(p for p in ROOT.rglob("*")
                   if p.is_file() and "__pycache__" not in p.parts
                   and p.name not in ("SHA256SUMS.txt", "RELEASE_MANIFEST.json"))
    lines = [f"{sha256_file(p)}  {p.relative_to(ROOT).as_posix()}" for p in files]
    (ROOT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n")

    env = {**os.environ, "SIH26170_RELEASE": args.release}
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", str(ROOT / "tests")],
                          capture_output=True, text=True, env=env)
    if proc.returncode:
        raise SystemExit("the test suite failed; refusing to write a release manifest")
    tail = re.findall(r"(\d+)\s+(passed|failed|error|errors|skipped)",
                      (proc.stdout or "").strip().splitlines()[-1] if proc.stdout else "")
    tail = [", ".join(f"{n} {w}" for n, w in tail) or "no pytest summary found"]

    receipt = json.loads((MODELS / "FREEZE_RECEIPT.json").read_text())
    prediction = json.loads((PREDICTION / "HOLDOUT_PREDICTION_RECEIPT.json").read_text())
    claims = pd.read_csv(RESULTS / "10_verify_claims.csv")
    packet_ledger = RESULTS / "10_verify_claims_with_packets.csv"
    packet_claims = (pd.read_csv(packet_ledger) if packet_ledger.exists() else None)

    manifest = {
        "release_candidate": config.RELEASE_CANDIDATE,
        "package_version": config.PACKAGE_VERSION,
        "model_version": config.MODEL_VERSION,
        "dataset_id": config.DATASET_ID,
        "written_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config": config.config_payload(),
        "config_digest": config.config_digest(),
        "runtime_contract_digest": config.runtime_contract_digest(),
        "frozen_artifact": {"filename": receipt["artifact_filename"],
                            "sha256": receipt["artifact_sha256"],
                            "frozen_at_utc": receipt["frozen_at_utc"],
                            "preflight_checks_passed": receipt["preflight_checks_passed"]},
        "holdout_run": {"spent": True,
                        "outputs": prediction["outputs"],
                        "monitor_floor": prediction["monitor_floor"]},
        "verification": {
            "tests": tail[0],
            "claims_checked": int(len(claims)),
            "claims_failed": int(claims.status.eq("FAIL").sum()),
            "claims_checked_including_packets": (
                int(len(packet_claims)) if packet_claims is not None else None),
            "claims_failed_including_packets": (
                int(packet_claims.status.eq("FAIL").sum())
                if packet_claims is not None else None)},
        "environment": {"python": sys.version.split()[0], "platform": platform.platform(),
                        "numpy": np.__version__, "pandas": pd.__version__,
                        "scikit_learn": sklearn.__version__},
        "files": len(files),
    }
    (ROOT / "RELEASE_MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
