#!/usr/bin/env python3
"""
Run every ungated stage, in order, from a clean results/ directory.

    python run_all.py              # stages 0-10 and 13, full grid (~8 min)
    python run_all.py --quick      # skips the GBR half of the grid (~2 min)
    python run_all.py --from 5     # resume at a stage

Stages 11 (freeze) and 12 (holdout) are deliberately NOT run here. They are
one-way doors and each needs its own explicit command — see docs/RUNBOOK.md.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

STAGES = [
    (0, "00_selfcheck.py", []),
    (1, "01_audit.py", []),
    (2, "02_drift_structure.py", []),
    (3, "03_benchmark_frozen_v1.py", []),
    (4, "04_benchmark_grid.py", []),
    (5, "05_calibration_report.py", []),
    (6, "06_predeclared_falltime_rule.py", []),
    (7, "07_extrapolation_risk.py", []),
    (8, "08_reason_code_audit.py", []),
    (9, "09_envelope_coverage.py", []),
    (10, "10_dryrun_freeze_predict.py", []),
    (13, "13_build_validation_summary.py", []),
    (14, "14_verify_claims.py", []),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="skip the GBR grid configurations")
    ap.add_argument("--from", dest="start", type=int, default=0)
    ap.add_argument("--clean", action="store_true", help="delete results/ first")
    a = ap.parse_args()

    if a.clean and (ROOT / "results").exists():
        shutil.rmtree(ROOT / "results")
        print("[clean] results/ removed")

    log = []
    t_all = time.time()
    for num, script, extra in STAGES:
        if num < a.start:
            continue
        args = list(extra)
        if a.quick and script.startswith("04_"):
            args.append("--quick")
        print(f"\n{'#' * 78}\n# stage {num}: {script} {' '.join(args)}\n{'#' * 78}")
        t0 = time.time()
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / script), *args],
                           cwd=ROOT / "scripts")
        dt = time.time() - t0
        log.append((num, script, r.returncode, dt))
        if r.returncode != 0:
            print(f"\nSTOPPED at stage {num} ({script}), exit {r.returncode}", file=sys.stderr)
            break

    print(f"\n{'=' * 78}\nSUMMARY   total {time.time() - t_all:.1f}s\n{'=' * 78}")
    for num, script, rc, dt in log:
        print(f"  stage {num:2d}  {'OK  ' if rc == 0 else 'FAIL'}  {dt:6.1f}s  {script}")
    failed = [n for n, _, rc, _ in log if rc != 0]
    if failed:
        print(f"\nfailed stages: {failed}")
        return 1
    print("\nAll ungated stages passed, and stage 14 confirms every documented")
    print("number matches results/. Stages 11 (freeze) and 12 (holdout) are")
    print("one-way doors and are not run from here — see docs/RUNBOOK.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
