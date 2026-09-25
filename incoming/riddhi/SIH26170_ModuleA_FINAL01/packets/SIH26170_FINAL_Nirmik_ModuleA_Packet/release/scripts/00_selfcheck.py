"""Stage 0 — are the code and the inputs what we think they are?

Nothing downstream is worth reading if this fails.
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys

import numpy as np
import pandas as pd
import sklearn

from _common import RESULTS, ROOT, release_arg
from modulea import config
from modulea.dataio import Release


def test_summary(output: str) -> str:
    """Counts only. pytest's trailing "in 17.08s" changes every run, and a results file
    that is not reproducible cannot be used to compare two independent runs."""
    tail = (output or "").strip().splitlines()[-1:] or [""]
    counts = re.findall(r"(\d+)\s+(passed|failed|error|errors|skipped|xfailed)", tail[0])
    if not counts:
        return "no pytest summary found"
    return ", ".join(f"{n} {word}" for n, word in counts)


def main() -> int:
    parser = release_arg(argparse.ArgumentParser())
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()

    release = Release(args.release)
    rows = []

    for name, ok in release.verify_hashes().items():
        rows.append({"check": f"sha256:{name}", "status": "PASS" if ok else "FAIL",
                     "detail": release.hashes()[name]})

    contract = release.contract_columns()
    expected = list(config.RUNTIME_CONTRACT.contract_fields)
    rows.append({"check": "output_contract_matches_release",
                 "status": "PASS" if contract == expected else "FAIL",
                 "detail": f"release says {contract}"})

    rows.append({"check": "config_digest", "status": "PASS",
                 "detail": config.config_digest()})
    rows.append({"check": "runtime_contract_digest", "status": "PASS",
                 "detail": config.runtime_contract_digest()})

    environment = {"python": sys.version.split()[0], "platform": platform.platform(),
                   "numpy": np.__version__, "pandas": pd.__version__,
                   "scikit_learn": sklearn.__version__}
    rows.append({"check": "environment", "status": "PASS", "detail": json.dumps(environment)})

    if not args.skip_tests:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", str(ROOT / "tests")],
                              capture_output=True, text=True)
        rows.append({"check": "unit_tests",
                     "status": "PASS" if proc.returncode == 0 else "FAIL",
                     "detail": test_summary(proc.stdout or proc.stderr)})

    table = pd.DataFrame(rows)
    table.to_csv(RESULTS / "00_selfcheck.csv", index=False)
    (RESULTS / "00_environment.json").write_text(json.dumps(environment, indent=2))
    print(table.to_string(index=False))
    failed = table["status"].eq("FAIL").any()
    print("\nSELFCHECK", "FAILED" if failed else "PASSED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
