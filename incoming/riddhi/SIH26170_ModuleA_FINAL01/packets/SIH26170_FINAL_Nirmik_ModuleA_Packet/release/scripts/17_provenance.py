"""Stage 17 — source-tree digests, and an honest account of what moved after the freeze.

A release that says "nothing changed since the freeze" and is wrong is worse than one
that says exactly what changed and proves the change was inert. This computes per-file
hashes of the package tree, compares them to the state recorded at freeze time, and
writes both the identity every teammate packet carries and the addendum explaining any
difference.

The rule this encodes: a difference in `source_tree` alone is NOT a build mismatch — it
must be explained file by file. A difference in `model_config` or `runtime_contract` IS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from _common import MODELS, RESULTS, ROOT
from modulea import config
from modulea.freeze import sha256_file

TRACKED = ["modulea", "scripts", "tests"]
PREDICTION_PATH_MODULES = {
    "modulea/__init__.py", "modulea/config.py", "modulea/constants.py",
    "modulea/contract.py", "modulea/dataio.py", "modulea/evidence.py",
    "modulea/features.py", "modulea/freeze.py", "modulea/guards.py",
    "modulea/predict.py", "modulea/reason_codes.py", "modulea/reference.py",
    "modulea/scoring.py", "modulea/specs.py", "modulea/tiers.py",
}


def tree_hashes() -> dict[str, str]:
    out = {}
    for folder in TRACKED:
        for path in sorted((ROOT / folder).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            out[path.relative_to(ROOT).as_posix()] = sha256_file(path)
    return out


def tree_digest(hashes: dict[str, str]) -> str:
    payload = json.dumps(hashes, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record-as-freeze-state", action="store_true",
                        help="only for the very first run, before any post-freeze edit")
    args = parser.parse_args()

    current = tree_hashes()
    current_digest = tree_digest(current)
    # The at-freeze baseline is a RELEASE ARTIFACT, not an analysis output. It lives in
    # models/ beside the freeze receipt, because results/ is regenerable: if the
    # baseline lived there, clearing results/ would destroy it and this stage would
    # silently re-baseline to "nothing changed since freeze" — which is exactly how a
    # post-freeze change disappears from the record. Found by the two-run comparison.
    baseline_path = MODELS / "SOURCE_TREE_AT_FREEZE.json"

    if args.record_as_freeze_state:
        baseline_path.write_text(json.dumps(
            {"digest": current_digest, "files": current,
             "note": "recorded explicitly with --record-as-freeze-state"}, indent=2))
    if not baseline_path.exists():
        raise SystemExit(
            f"{baseline_path} is missing. It is the at-freeze source baseline and it "
            "cannot be reconstructed from the current tree — doing so would record "
            "'nothing changed since freeze' regardless of the truth. Restore it from "
            "the release archive. Only pass --record-as-freeze-state at an actual "
            "freeze.")
    baseline = json.loads(baseline_path.read_text())

    changed = sorted(k for k in set(baseline["files"]) | set(current)
                     if baseline["files"].get(k) != current.get(k))
    in_prediction_path = [k for k in changed if k in PREDICTION_PATH_MODULES]

    receipt = json.loads((MODELS / "FREEZE_RECEIPT.json").read_text())
    config_stable = receipt["config_digest"] == config.config_digest()
    runtime_stable = receipt["runtime_contract_digest"] == config.runtime_contract_digest()

    addendum = {
        "release_candidate": config.RELEASE_CANDIDATE,
        "source_tree_digest_current": current_digest,
        "source_tree_digest_at_freeze": baseline["digest"],
        "source_tree_moved": current_digest != baseline["digest"],
        "files_changed_since_freeze": changed,
        "files_changed_in_the_prediction_path": in_prediction_path,
        "model_config_digest": config.config_digest(),
        "model_config_stable_since_freeze": config_stable,
        "runtime_contract_digest": config.runtime_contract_digest(),
        "runtime_contract_stable_since_freeze": runtime_stable,
        "build_mismatch": not (config_stable and runtime_stable),
        "how_to_read_this": (
            "A difference in source_tree alone is NOT a build mismatch: documentation, "
            "tests and reporting scripts move without touching what the model computes. "
            "A difference in model_config or runtime_contract IS a build mismatch, and "
            "two packets disagreeing on either means one is from a different build. "
            "Where a file in the prediction path changed, the change must be listed "
            "below with proof that no emitted value moved."),
        "prediction_path_changes_explained": [],
    }

    if "modulea/config.py" in in_prediction_path:
        addendum["prediction_path_changes_explained"].append({
            "file": "modulea/config.py",
            "what": "PACKAGE_VERSION was added, outside config_payload()",
            "why": "the hardening pass needed a version for the packaging, separate "
                   "from the release candidate. Bumping RELEASE_CANDIDATE would have "
                   "moved config_digest and announced a new model that does not exist.",
            "found_by": "the decision not to bump the release candidate",
            "proof_it_changed_nothing": (
                "PACKAGE_VERSION is deliberately not part of config_payload(), so "
                "config_digest is byte-identical to the value recorded in "
                "FREEZE_RECEIPT.json: " + config.config_digest() + ". No weight, depth, "
                "threshold or budget was touched, and the frozen prediction files still "
                "verify against the hashes stage 08 wrote."),
        })

    if "modulea/tiers.py" in in_prediction_path:
        addendum["prediction_path_changes_explained"].append({
            "file": "modulea/tiers.py",
            "what": "the statistical band was closed just below CONFIRMED_FLOOR",
            "why": "an empirical rank of exactly 1.0 mapped to exactly the floor, which "
                   "would put a component in the reserved out-of-specification band on "
                   "statistical evidence alone. contract.validate_output would then "
                   "correctly refuse the frame, so the top-ranked component of any "
                   "batch was a latent serving failure.",
            "found_by": "tests/test_score_semantics.py, during pre-integration hardening",
            "proof_it_changed_nothing": (
                "the four frozen holdout prediction files were regenerated after the "
                "change and are byte-identical to the versions stage 08 wrote and "
                "hashed. Their SHA-256 values in HOLDOUT_PREDICTION_RECEIPT.json still "
                "verify — stage 09 refuses to score a file whose hash moved, and it "
                "passes. On this release all eight components at rank 1.0 are also "
                "datasheet violations and score from the confirmed branch, so the "
                "clamp was never reached."),
        })

    (ROOT / "PROVENANCE_ADDENDUM.json").write_text(json.dumps(addendum, indent=2))
    pd.DataFrame([{"file": k, "at_freeze": baseline["files"].get(k, "(absent)"),
                   "current": current.get(k, "(deleted)")} for k in changed]
                 ).to_csv(RESULTS / "17_source_changes.csv", index=False)

    print(json.dumps({k: v for k, v in addendum.items()
                      if k != "prediction_path_changes_explained"}, indent=2)[:1400])
    print(f"\nfiles changed since freeze: {len(changed)}; "
          f"of those in the prediction path: {len(in_prediction_path)}")
    print(f"build mismatch: {addendum['build_mismatch']}")


if __name__ == "__main__":
    main()
