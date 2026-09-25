"""Run the ungated stages in order. The two gated ones are deliberately absent."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STAGES = ["00_selfcheck.py", "01_audit.py", "02_spec_witness.py",
          "03_threshold_curve.py", "04_nested_validation.py",
          "05_blindspot_report.py", "06_dryrun.py",
          "12_robustness.py", "13_score_semantics.py", "14_sensitivity.py",
          "20_confusion_matrix.py"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", required=True)
    parser.add_argument("--from-stage", default="")
    args = parser.parse_args()

    stages = STAGES
    if args.from_stage:
        stages = [s for s in STAGES if s >= args.from_stage]

    missing = [n for n in ["ModuleA_Final_Holdout_168h.csv",
                           "HOLDOUT_PREDICTION_RECEIPT.json"]
               if not (ROOT / "prediction" / n).exists()]
    if missing:
        print("prediction/ is missing " + ", ".join(missing) + ".\n"
              "These are the spent one-shot holdout outputs; they are release artifacts "
              "and cannot be regenerated. Restore them from the release archive. Do NOT "
              "re-run scripts/08_predict_holdout.py to recreate them.")
        return 2

    for stage in stages:
        print(f"\n{'=' * 72}\n{stage}\n{'=' * 72}")
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / stage),
                               "--release", args.release])
        if proc.returncode:
            print(f"\n{stage} failed with exit code {proc.returncode}; stopping.")
            return proc.returncode

    print("\nAll ungated stages completed. Stages 07 and 08 are gated and must be run "
          "deliberately — see docs/RUNBOOK.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
