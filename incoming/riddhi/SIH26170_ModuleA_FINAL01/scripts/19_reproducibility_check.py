"""Stage 19 — do two independent runs of this release produce the same files?

Reproducibility is the claim that makes every other claim checkable by someone else.
It is asserted constantly and verified rarely, so this verifies it: point the script at
two `results/` trees produced by two independent runs and it reports, file by file,
whether they agree.

Three categories, because not everything *should* match:

  MUST_MATCH   every analysis output. A difference here is a defect.
  MAY_DIFFER   files that legitimately carry a timestamp or an absolute path.
  ABSENT       present in one tree and not the other — always a defect.

Usage
-----
    python scripts/19_reproducibility_check.py --a run_a/results --b run_b/results
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

# Files whose content legitimately embeds a wall-clock time or a machine-specific path.
# Everything else must be byte-identical between two runs on the same inputs.
MAY_DIFFER = {
    "00_environment.json",          # platform string, python build
    "17_source_tree_at_freeze.json",  # absolute-path independent, but run-order seeded
}
# This script's own output. It exists only in whichever tree it was written into, so
# comparing it would report a failure caused by the act of comparing.
# This script's own output, and the stage-18 release artifacts that embed its verdict.
# All of these exist only in whichever tree ran the comparison and the release step, so
# comparing them reports a difference caused by the act of comparing. They are checked
# instead by scripts/10_verify_claims.py --with-packets, which runs after the release
# step and verifies every packet against its own checksums.
EXCLUDE = {"19_reproducibility.csv", "19_reproducibility.json",
           "18_release_identity.json", "18_letter_facts.json", "18_packets.csv",
           "10_verify_claims_with_packets.csv"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a", required=True, help="results/ from the first run")
    parser.add_argument("--b", required=True, help="results/ from the second run")
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    a, b = Path(args.a), Path(args.b)

    # Release-step artifacts live under 18_serving_example/ and are excluded wholesale
    # for the same reason as the other stage-18 outputs: they are produced once, after
    # the comparison, not by the analysis runs being compared.
    names = sorted(n for n in
                   ({p.relative_to(a).as_posix() for p in a.rglob("*") if p.is_file()} |
                    {p.relative_to(b).as_posix() for p in b.rglob("*") if p.is_file()})
                   if n not in EXCLUDE and not n.startswith("18_serving_example/"))
    rows = []
    for name in names:
        pa, pb = a / name, b / name
        if not pa.exists() or not pb.exists():
            rows.append({"file": name, "category": "ABSENT", "status": "FAIL",
                         "detail": f"missing from {'A' if not pa.exists() else 'B'}"})
            continue
        same = digest(pa) == digest(pb)
        category = "MAY_DIFFER" if Path(name).name in MAY_DIFFER else "MUST_MATCH"
        status = "PASS" if (same or category == "MAY_DIFFER") else "FAIL"
        rows.append({"file": name, "category": category, "status": status,
                     "detail": "identical" if same else "differs"})

    table = pd.DataFrame(rows)
    failures = table[table.status.eq("FAIL")]
    summary = {
        "files_compared": int(len(table)),
        "must_match": int(table.category.eq("MUST_MATCH").sum()),
        "identical": int((table.detail == "identical").sum()),
        "failures": failures[["file", "category", "detail"]].to_dict("records"),
        "verdict": "REPRODUCIBLE" if failures.empty else "NOT REPRODUCIBLE",
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(args.out, index=False)
        Path(args.out).with_suffix(".json").write_text(json.dumps(summary, indent=2))

    print(table[table.status.eq("FAIL") | table.category.eq("MAY_DIFFER")]
          .to_string(index=False) if len(failures) or table.category.eq("MAY_DIFFER").any()
          else "every compared file is byte-identical")
    print(f"\n{summary['identical']} of {summary['files_compared']} files identical; "
          f"verdict: {summary['verdict']}")
    return 0 if failures.empty else 1


if __name__ == "__main__":
    sys.exit(main())
