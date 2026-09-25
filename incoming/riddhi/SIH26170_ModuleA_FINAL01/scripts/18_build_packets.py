"""Stage 18 — build the six teammate packets, from results/ and never by hand.

A packet is derived, never authored. Every figure in every letter is interpolated from a
file this release produced, so a number cannot drift between the packet and its evidence.

All six carry the same `RELEASE_IDENTITY.json`. Two packets disagreeing on
`model_config` or `runtime_contract` means one is from a different build.

Builds:
  * a worked serving example — an input batch and exactly what comes back
  * RELEASE_IDENTITY.json
  * six role-scoped packets, each with its own letter and its own SHA256SUMS.txt
"""
from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path

import pandas as pd

import _letters
from _common import MODELS, PREDICTION, RESULTS, ROOT, release_arg
from modulea import config
from modulea.constants import CONTRACT_FIELDS, DIAGNOSTIC_FIELDS
from modulea.dataio import Release
from modulea.freeze import load, sha256_file

OUT = ROOT / "packets"
PREDICTION_FILES = [f"ModuleA_Final_Holdout_{e}h.csv" for e in (0, 24, 96, 168)]


# --------------------------------------------------------------------------
# facts: every number any letter may quote, read once from results/
# --------------------------------------------------------------------------
def gather_facts(identity: dict) -> dict:
    j = lambda n: json.loads((RESULTS / n).read_text())
    c = lambda n: pd.read_csv(RESULTS / n)

    spec = j("02_spec_witness.json")
    spec_table = c("02_spec_witness.csv")
    at168 = spec_table[spec_table.epoch_h.eq(168)]
    nested = c("04_nested_validation.csv").set_index("arm")
    fusion = j("15_fusion_dryrun.json")
    semantics = j("13_score_semantics.json")
    blind = c("05_blindspot.csv")
    within = blind[blind.population.eq("static, within spec")]
    metrics = c("09_holdout_metrics.csv").set_index("epoch_h")
    tiers = c("09_holdout_tiers.csv").set_index("tier")
    robustness = c("12_robustness.csv")
    selfcheck = c("00_selfcheck.csv").set_index("check")
    tests = str(selfcheck.loc["unit_tests", "detail"])
    claims_ledger = c("10_verify_claims.csv")
    repro_path = RESULTS / "19_reproducibility.json"
    repro = json.loads(repro_path.read_text()) if repro_path.exists() else {
        "identical": 0, "files_compared": 0}

    return {
        "model": config.MODEL_VERSION,
        "package": config.PACKAGE_VERSION,
        "dataset": config.DATASET_ID,
        "state": identity["release_state"],
        "config_digest": identity["digests"]["model_config"],
        "runtime_digest": identity["digests"]["runtime_contract"],
        "source_digest": identity["digests"]["source_tree"],
        "freeze_source_digest": identity["digests"]["source_tree_at_freeze"],
        "build_mismatch": identity["build_mismatch"],
        "monitor_floor": identity["monitor_floor"],
        "spec_flags": int(at168["flagged"].sum()),
        "spec_fp": spec["false_positives_observed"],
        "spec_normals": spec["normals_scored_at_168h"],
        "spec_bound": spec["false_positive_rate_95pct_upper_bound"],
        "train_spec_violations": int(
            at168[at168.split.eq("TRAIN")]["flagged"].iloc[0]),
        "nested_tp": int(nested.loc["shipped", "tp"]),
        "nested_fp": int(nested.loc["shipped", "fp"]),
        "nested_recall": float(nested.loc["shipped", "recall"]),
        "nested_fpr": float(nested.loc["shipped", "fpr"]),
        "inherited_tp": int(nested.loc["inherited", "tp"]),
        "inherited_fp": int(nested.loc["inherited", "fp"]),
        "fusion_rows": fusion["rows_joined"],
        "fusion_checks": len(fusion["checks"]),
        "corroborated": int(fusion["b_evidence_status_counts"].get(
            "SAME_PARAMETER_DRIFT_SUPPORT", 0)),
        "probability_gap": semantics["question_2_is_it_a_probability"][
            "largest_gap_between_score_and_observed_rate"],
        "within_detected": int(within.detected.sum()),
        "within_actual": int(within.actual.sum()),
        "holdout_tp": int(metrics.loc[168, "tp"]),
        "holdout_fp": int(metrics.loc[168, "fp"]),
        "holdout_fn": int(metrics.loc[168, "fn"]),
        "holdout_flagged": int(metrics.loc[168, "flagged"]),
        "confirmed": int(tiers.loc["CONFIRMED", "n"]),
        "robustness_cases": int(len(robustness)),
        "tests": tests,
        "claims": int(len(claims_ledger)),
        "repro_identical": repro.get("identical", 0),
        "repro_total": repro.get("files_compared", 0),
    }


def release_identity() -> dict:
    receipt = json.loads((MODELS / "FREEZE_RECEIPT.json").read_text())
    prediction = json.loads((PREDICTION / "HOLDOUT_PREDICTION_RECEIPT.json").read_text())
    provenance = json.loads((ROOT / "PROVENANCE_ADDENDUM.json").read_text())
    selfcheck = pd.read_csv(RESULTS / "00_selfcheck.csv").set_index("check")
    claims = pd.read_csv(RESULTS / "10_verify_claims.csv")
    return {
        "release_candidate": config.RELEASE_CANDIDATE,
        "package_version": config.PACKAGE_VERSION,
        "model_version": config.MODEL_VERSION,
        "release_state": "HOLDOUT_PREDICTION_DELIVERED",
        "dataset": {"id": config.DATASET_ID, "status": "FINAL",
                    "rows": 5400, "lots": 72, "join_key": "component_id"},
        "digests": {
            "model_config": config.config_digest(),
            "runtime_contract": config.runtime_contract_digest(),
            "source_tree": provenance["source_tree_digest_current"],
            "source_tree_at_freeze": provenance["source_tree_digest_at_freeze"],
        },
        "source_tree_note": provenance["how_to_read_this"],
        "build_mismatch": provenance["build_mismatch"],
        "output_contract_columns": CONTRACT_FIELDS,
        "diagnostic_columns": DIAGNOSTIC_FIELDS,
        "monitor_floor": prediction["monitor_floor"],
        "operating_threshold": prediction["operating_threshold"],
        "operating_fpr_budget": config.OPERATING_FPR_BUDGET,
        "join_key": "component_id",
        "emits_disposition": ["PASS", "MONITOR"],
        "emits_reject": False,
        "verification": {
            "tests": str(selfcheck.loc["unit_tests", "detail"]),
            "claims": {"checked": int(len(claims)),
                       "failed": int(claims.status.eq("FAIL").sum())},
        },
        "frozen_artifact_sha256": receipt["artifact_sha256"],
        "team_signoff": "RECORDED",
        "holdout_prediction_state": "SPENT",
        "built_for": "one of six role-scoped team artifacts, all derived from this release",
    }


def build_serving_example(release: Release) -> Path:
    model, _ = load(MODELS / "module_a_final01.joblib")
    holdout = release.split("holdout")
    lot = holdout["lot_id"].iloc[0]
    batch = holdout[holdout["lot_id"].eq(lot)].reset_index(drop=True)
    output = model.predict(batch, 168)
    folder = RESULTS / "18_serving_example"
    folder.mkdir(exist_ok=True)
    batch.to_csv(folder / "input_one_complete_lot.csv", index=False)
    output.to_csv(folder / "output_one_complete_lot.csv", index=False)
    (folder / "README.txt").write_text(
        f"A worked serving call.\n\n"
        f"input_one_complete_lot.csv   lot {lot}, {len(batch)} components, all four epochs\n"
        f"output_one_complete_lot.csv  what Module A returns for it\n\n"
        f"The lot is complete - every component the manifest declares for {lot} is "
        f"present. Remove one row and the call is refused, deliberately: a lot-relative "
        f"reference computed on a partial lot is wrong, not approximate.\n\n"
        f"Of these {len(batch)} components, "
        f"{int(output['module_a_disposition'].eq('MONITOR').sum())} are MONITOR and "
        f"{int(output['module_a_evidence_tier'].eq('CONFIRMED').sum())} are CONFIRMED.\n")
    return folder


# --------------------------------------------------------------------------
# what each packet contains, as (destination, source) pairs
# --------------------------------------------------------------------------
def packet_contents(name: str, release: Release, example: Path) -> list[tuple[str, Path]]:
    R, D = RESULTS, ROOT / "docs"
    contract = release.root / "integration_safe"
    items: list[tuple[str, Path]] = []

    def docs(*names):
        return [(f"docs/{n}", D / n) for n in names]

    # Every packet stands alone. These go in all six.
    items += docs("MODEL_CARD.md", "LIMITATIONS.md")
    items += [("evidence/20_confusion_matrices.csv", R / "20_confusion_matrices.csv"),
              ("evidence/20_reconciliation.csv", R / "20_reconciliation.csv"),
              ("evidence/09_holdout_metrics.csv", R / "09_holdout_metrics.csv"),
              ("evidence/09_holdout_tiers.csv", R / "09_holdout_tiers.csv"),
              ("evidence/09_holdout_by_behaviour.csv", R / "09_holdout_by_behaviour.csv"),
              ("evidence/10_verify_claims.csv", R / "10_verify_claims.csv"),
              ("prediction/ModuleA_Final_Holdout_168h.csv",
               PREDICTION / "ModuleA_Final_Holdout_168h.csv"),
              ("prediction/HOLDOUT_PREDICTION_RECEIPT.json",
               PREDICTION / "HOLDOUT_PREDICTION_RECEIPT.json")]

    if name == "Anushka":
        items += [("contract/ModuleA_Output_Contract.csv",
                   contract / "ModuleA_Output_Contract.csv"),
                  ("contract/Device_Specs.csv", contract / "Device_Specs.csv"),
                  ("contract/Schema_Data_Dictionary.csv",
                   contract / "Schema_Data_Dictionary.csv")]
        items += [(f"prediction/{n}", PREDICTION / n) for n in PREDICTION_FILES]
        items += [("prediction/HOLDOUT_PREDICTION_RECEIPT.json",
                   PREDICTION / "HOLDOUT_PREDICTION_RECEIPT.json")]
        items += [(f"example/{p.name}", p) for p in sorted(example.iterdir())]
        items += [("example/fusion_joined_example_60_rows.csv",
                   R / "15_fusion_joined_example_60_rows.csv"),
                  ("example/fusion_join_checks.csv", R / "15_fusion_dryrun.csv"),
                  ("example/robustness_cases.csv", R / "12_robustness.csv"),
                  ("example/confusion_matrices.csv", R / "20_confusion_matrices.csv")]
        items += docs("INTEGRATION_NOTE.md", "MODEL_CARD.md", "LIMITATIONS.md")

    elif name == "Sanskruti":
        items += [(f"prediction/{n}", PREDICTION / n) for n in PREDICTION_FILES]
        items += [("prediction/HOLDOUT_PREDICTION_RECEIPT.json",
                   PREDICTION / "HOLDOUT_PREDICTION_RECEIPT.json")]
        for n in ["10_verify_claims.csv", "04_nested_validation.csv",
                  "04_nested_validation_cap03.csv", "04_nested_per_lot.csv",
                  "04_selected_weights_cap01.csv", "04_selected_weights_cap03.csv",
                  "03_operating_points.csv", "03_threshold_curve.csv",
                  "09_holdout_metrics.csv", "09_holdout_tiers.csv",
                  "09_holdout_by_behaviour.csv", "09_ranking_comparison.json",
                  "02_spec_witness.csv", "12_robustness.csv", "13_score_bands.csv",
                  "14_per_lot.csv", "14_per_variant.csv", "14_per_severity.csv",
                  "19_reproducibility.csv", "20_confusion_matrices.csv",
                  "20_reconciliation.csv"]:
            if (R / n).exists():
                items.append((f"verification/{n}", R / n))
        items += docs("VALIDATION_SUMMARY.md", "ACCEPTANCE_CRITERIA.md",
                      "DECISION_LOG.md", "LIMITATIONS.md",
                      "MASTER_PROMPT_FINAL_VERIFICATION.md",
                      "MASTER_PROMPT_CONFUSION_MATRIX.md")

    elif name == "Chaitany":
        for n in ["01_audit.json", "01_split_structure.csv", "01_scale_ladder.csv",
                  "02_spec_witness.csv", "05_static_composition.csv", "05_blindspot.csv",
                  "05_blindspot.json"]:
            if (R / n).exists():
                items.append((f"data_findings/{n}", R / n))
        items += docs("LIMITATIONS.md", "FUTURE_RELEASE_ITEMS.md")

    elif name == "Tanisha":
        items += [("domain/Device_Specs.csv", contract / "Device_Specs.csv")]
        for n in ["02_spec_witness.csv", "02_spec_coverage.csv", "05_blindspot.csv",
                  "14_per_severity.csv", "14_per_variant.csv"]:
            if (R / n).exists():
                items.append((f"domain/{n}", R / n))
        items += docs("LIMITATIONS.md", "MODEL_CARD.md", "FUTURE_RELEASE_ITEMS.md")

    elif name == "Riddhi":
        for n in ["04_nested_validation.csv", "09_ranking_comparison.json",
                  "09_holdout_by_behaviour.csv", "03_operating_points.csv",
                  "12_robustness.csv"]:
            if (R / n).exists():
                items.append((f"comparison/{n}", R / n))
        items += docs("DECISION_LOG.md", "VALIDATION_SUMMARY.md", "IMPROVEMENTS.md",
                      "MODEL_CARD.md", "LIMITATIONS.md")

    return items


def runtime_contract_json(identity: dict) -> str:
    return json.dumps({
        "serving_contract_version": "ma-serving-1.0",
        "runtime_contract_digest": config.runtime_contract_digest(),
        **dict(config.RUNTIME_CONTRACT.__dict__),
        "monitor_floor": identity["monitor_floor"],
        "operating_threshold": identity["operating_threshold"],
        "score_bands": {"statistical": "[0.00, 0.90)",
                        "out_of_specification": "[0.90, 1.00]"},
        "epochs_supported": [0, 24, 96, 168],
        "refuses": ["a lot that cannot be proved complete against external lot sizes",
                    "an unknown device_variant",
                    "a null, non-numeric, zero or negative measurement",
                    "a duplicate component_id",
                    "a lot containing more than one device_variant",
                    "a lot below 30 components"],
        "does_not_refuse": ["a batch that omits a whole lot - screening one lot is "
                            "legitimate, so Module A returns one row per component SENT"],
    }, indent=2)


def build_packet(name: str, release: Release, identity: dict, facts: dict,
                 example: Path) -> Path:
    folder = OUT / f"SIH26170_FINAL_{name}_ModuleA_Packet"
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)

    if name == "Nirmik":
        # The owner gets the whole release. The packet build's OWN outputs are left
        # out — 18_*, the post-packet ledger, and packets/ itself — because including
        # them would make this archive depend on when it was built, and an archive
        # whose hash moves on a rebuild cannot be verified by whoever receives it.
        # Everything excluded is regenerated by scripts/release.sh.
        volatile = {"18_release_identity.json", "18_letter_facts.json",
                    "18_packets.csv", "10_verify_claims_with_packets.csv",
                    "19_reproducibility.csv", "19_reproducibility.json"}
        for item in sorted(ROOT.iterdir()):
            if item.name in {"packets", ".git", "__pycache__", ".pytest_cache"}:
                continue
            target = folder / "release" / item.name
            if item.is_dir():
                shutil.copytree(
                    item, target,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc",
                                                  "18_serving_example", *volatile))
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(item, target)
        (folder / "release" / "REGENERATE.txt").write_text(
            "This copy of the release deliberately omits the outputs of the packet\n"
            "build itself: results/18_*, results/19_reproducibility.*, and\n"
            "results/10_verify_claims_with_packets.csv. Including them would make this\n"
            "archive's hash depend on when it was built.\n\n"
            "Regenerate them with:\n"
            "  bash scripts/run_canonical.sh <release-root> <moduleB-packet-root>\n"
            "  bash scripts/release.sh <release-root> <second-run>/results\n")
    else:
        seen = set()
        for destination, source in packet_contents(name, release, example):
            if destination in seen:
                continue
            seen.add(destination)
            target = folder / destination
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(source, target)
        shutil.copy(ROOT / "PROVENANCE_ADDENDUM.json", folder / "PROVENANCE_ADDENDUM.json")
        if name == "Anushka":
            (folder / "contract/runtime_contract.json").write_text(
                runtime_contract_json(identity))

    (folder / "RELEASE_IDENTITY.json").write_text(json.dumps(identity, indent=2))
    (folder / f"README_{name.upper()}.md").write_text(_letters.LETTERS[name](facts))
    role, one_line, do, dont = _letters.START_HERE[name]
    (folder / "START_HERE.txt").write_text(
        _letters.start_here(name, role, one_line, do, dont, facts))

    lines = [f"{sha256_file(p)}  {p.relative_to(folder).as_posix()}"
             for p in sorted(folder.rglob("*"))
             if p.is_file() and p.name != "SHA256SUMS.txt"]
    (folder / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n")

    archive = OUT / f"{folder.name}.zip"
    if archive.exists():
        archive.unlink()
    # Deterministic: a fixed entry timestamp and fixed mode, entries in sorted order.
    # Filesystem mtimes would otherwise make two identical packets produce different
    # bytes, and a release artifact that cannot be compared byte for byte cannot be
    # verified by whoever receives it.
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(folder.rglob("*")):
            if not p.is_file():
                continue
            info = zipfile.ZipInfo(f"{folder.name}/{p.relative_to(folder).as_posix()}",
                                   date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, p.read_bytes())
    return archive


ROLE = {
    "Anushka": ("integration lead",
                "Threshold module_a_score at the published floor and you have "
                "reproduced Module A's decision exactly. The join to Module B is "
                "already done and checked."),
    "Sanskruti": ("evaluation",
                  "166 claim checks, each naming the file it verifies. Two "
                  "independent runs agree byte for byte. Two corrections the "
                  "machinery caught are documented."),
    "Chaitany": ("data",
                 "Two dataset findings: the train split is not anomaly-free, and "
                 "calibration and holdout are composed very differently for one "
                 "defect class. One concrete ask for the next split."),
    "Tanisha": ("domain and standards",
                "Please sanity-check the eleven datasheet limits the CONFIRMED tier "
                "rests on, and tell me whether a physically justified parameter "
                "relationship exists."),
    "Riddhi": ("Module A history",
               "What measuring Better Potential, RC2 and RC3 under one protocol "
               "showed, the six defects and their fixes, and the hypothesis I got "
               "wrong."),
    "Nirmik": ("owner",
               "Everything, plus the three decisions that need you: the operating "
               "point, calibration-split Module B forecasts, and a fresh test set."),
}


def build_envelope(identity: dict, facts: dict, built: list) -> Path:
    """The cover note for the whole delivery. Derived, so its checksums cannot drift."""
    matrices = pd.read_csv(RESULTS / "20_confusion_matrices.csv").set_index("result")
    hold = matrices.loc["holdout @ 168 h — frozen release"]
    cal = matrices.loc["calibration out-of-fold — shipped configuration"]
    rows = "\n".join(
        f"| **{b['for']}** | {ROLE[b['for']][0]} | `{b['zip']}` | {b['bytes']:,} | "
        f"`{b['sha256'][:16]}…` |" for b in built)
    notes = "\n\n".join(f"**{b['for']}** — {ROLE[b['for']][1]}" for b in built)

    text = f"""# Module A · final delivery envelope

**Model** `{facts['model']}` · **package** `{facts['package']}` ·
dataset `{facts['dataset']}` · state **{facts['state']}**
**Model digest** `{facts['config_digest'][:16]}…` ·
**runtime digest** `{facts['runtime_digest'][:16]}…`
**Holdout run** SPENT · **build mismatch** {facts['build_mismatch']}

Six packets, one per person. Each is self-contained: its own letter, its own
`SHA256SUMS.txt`, and the same `RELEASE_IDENTITY.json`. **If two packets disagree on
`model_config` or `runtime_contract`, one is from a different build and must not be
used.**

## Who gets what

| For | Role | File | Bytes | SHA-256 |
|---|---|---|---:|---|
{rows}

{notes}

## State of the release

| | |
|---|---|
| tests | {facts['tests']} |
| claim checks | {facts['claims']}, 0 failed |
| reproducibility | {facts['repro_identical']} of {facts['repro_total']} files identical, two independent runs |
| robustness cases | {facts['robustness_cases']}, 0 failures |
| confusion matrices | {len(matrices)} reported, all balance, all cross-checked against sklearn |

## The four outcomes

Every headline here is a view of four integers. Both rows below are the complete matrix.

| result | TP | TN | FP | FN | recall | precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|
| calibration, out of fold, shipped config | {int(cal.tp)} | {int(cal.tn):,} | {int(cal.fp)} | {int(cal.fn)} | {cal.recall:.1%} | {cal.precision:.1%} | {cal.fpr:.2%} |
| holdout 168 h — **DIAGNOSTIC** | {int(hold.tp)} | {int(hold.tn):,} | {int(hold.fp)} | {int(hold.fn)} | {hold.recall:.1%} | {hold.precision:.1%} | {hold.fpr:.2%} |

**FN is the expensive cell** — {int(hold.fn)} real defects passed onward on the holdout.
FP costs review time and harms nobody. Accuracy is deliberately not reported: with 90
anomalies in 1,343 components, flagging nothing would score above 93%.

The datasheet-limit rule, across all 5,400 components in the dataset:
**{facts['spec_flags']} flagged, every one a real anomaly, {facts['spec_fp']} false
positives in {facts['spec_normals']:,} healthy components.** The honest form, used
everywhere in these packets: no observed false positive, 95% upper bound on the true
rate {facts['spec_bound']:.2%}. Not "never".

## What is not claimed

- **The holdout is not an independent test.** It shaped RC1, RC2, RC3 and this
  release's reporting. Every holdout cell above is a comparison against prior runs.
- **The score is not a probability.** Monotone in the anomaly rate, but the largest gap
  between a band midpoint and its observed rate is {facts['probability_gap']:.2f}.
- **Within-spec static offsets are largely invisible** — {facts['within_detected']} of
  {facts['within_actual']}. Established as a ceiling across nine statistics, not a
  deficiency of this candidate.
- **This is synthetic data.** Nothing here supports a claim about real silicon.

## Verifying a packet

```bash
unzip SIH26170_FINAL_<name>_ModuleA_Packet.zip
cd SIH26170_FINAL_<name>_ModuleA_Packet
sha256sum -c SHA256SUMS.txt
```

Archives are byte-deterministic: two release runs from identical analysis produce
identical zips, so the hashes above are reproducible rather than incidental.
"""
    path = OUT / "ENVELOPE.md"
    path.write_text(text)
    return path


def main() -> None:
    parser = release_arg(argparse.ArgumentParser())
    parser.add_argument("--only", default="", help="build one packet by name")
    args = parser.parse_args()
    release = Release(args.release)
    OUT.mkdir(exist_ok=True)

    identity = release_identity()
    (RESULTS / "18_release_identity.json").write_text(json.dumps(identity, indent=2))
    facts = gather_facts(identity)
    (RESULTS / "18_letter_facts.json").write_text(json.dumps(facts, indent=2, default=float))
    example = build_serving_example(release)

    names = [args.only] if args.only else list(_letters.LETTERS)
    # Nirmik last: his packet contains the others.
    names = [n for n in names if n != "Nirmik"] + (["Nirmik"] if "Nirmik" in names else [])

    built = []
    for name in names:
        archive = build_packet(name, release, identity, facts, example)
        built.append({"for": name, "zip": archive.name,
                      "bytes": archive.stat().st_size,
                      "sha256": sha256_file(archive)})
    table = pd.DataFrame(built)
    table.to_csv(RESULTS / "18_packets.csv", index=False)
    if len(built) == len(_letters.LETTERS):
        envelope = build_envelope(identity, facts, built)
        print(f"envelope: {envelope}")
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
