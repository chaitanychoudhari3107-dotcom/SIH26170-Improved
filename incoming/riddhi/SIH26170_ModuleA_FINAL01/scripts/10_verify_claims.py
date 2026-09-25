"""Stage 10 — do the documents and the code match the recorded numbers?

Every figure quoted in docs/ is listed here with the file it must come from. A
document that drifts from results/ fails this stage. This is the mechanism that
makes 'zero unsupported claims' a property of the release rather than a promise:
a number nobody can check here does not belong in a document.

Run it after any edit to docs/.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

from _common import MODELS, PREDICTION, RESULTS, ROOT
from modulea import config
from modulea.freeze import sha256_file
import numpy as np

DOCS = ROOT / "docs"


def _json(name):
    return json.loads((RESULTS / name).read_text())


def _csv(name):
    return pd.read_csv(RESULTS / name)


def checks(with_packets: bool = False) -> list[dict]:
    out = []

    def check(claim, ok, detail):
        out.append({"claim": claim, "status": "PASS" if ok else "FAIL", "detail": str(detail)})

    # --- the zero-false-positive claim ----------------------------------
    spec = _csv("02_spec_witness.csv")
    at168 = spec[spec.epoch_h.eq(168)]
    total_fp = int(at168["FALSE_POSITIVES"].sum())
    total_normals = int(at168["normals"].sum())
    check("the datasheet-limit rule raises zero false positives on the whole release",
          total_fp == 0, f"{total_fp} false positives in {total_normals} normals")
    bound = _json("02_spec_witness.json")["false_positive_rate_95pct_upper_bound"]
    check("the zero-FP claim is stated with an upper bound, not as 'never'",
          0 < bound < 0.01, f"95% upper bound {bound:.4%}")

    # --- the holdout CONFIRMED tier -------------------------------------
    tiers = _csv("09_holdout_tiers.csv")
    confirmed = tiers[tiers.tier.eq("CONFIRMED")].iloc[0]
    check("the holdout CONFIRMED tier contains no normal component",
          int(confirmed["normals"]) == 0,
          f"{int(confirmed['n'])} confirmed, {int(confirmed['normals'])} normals")

    # --- nested validation ------------------------------------------------
    nested = _csv("04_nested_validation.csv")
    shipped = nested[nested.arm.eq("shipped")].iloc[0]
    inherited = nested[nested.arm.eq("inherited")].iloc[0]
    check("the shipped nested estimate is 45 of 54 at 9 false alarms",
          int(shipped.tp) == 45 and int(shipped.fp) == 9,
          f"tp={int(shipped.tp)} fp={int(shipped.fp)}")
    check("the before-state under the same protocol is 44 of 54 at 7",
          int(inherited.tp) == 44 and int(inherited.fp) == 7,
          f"tp={int(inherited.tp)} fp={int(inherited.fp)}")
    check("the nested run was made at the budget the release ships at",
          abs(_json("04_nested_validation.json")["fpr_cap"]
              - config.OPERATING_FPR_BUDGET) < 1e-12,
          _json("04_nested_validation.json")["fpr_cap"])
    for cap, expected in [("01", 6), ("03", 12)]:
        picked = _csv(f"04_selected_weights_cap{cap}.csv")
        check(f"at a 0.{cap} budget, {expected} of 12 folds chose pure lot_relative",
              int((picked["lot_relative"] == 1.0).sum()) == expected,
              f"{int((picked['lot_relative'] == 1.0).sum())} of {len(picked)}")
        check(f"at a 0.{cap} budget, no fold chose the inherited overall_extreme",
              bool((picked["overall_extreme"] == 0.0).all()),
              f"max overall_extreme {picked['overall_extreme'].max()}")

    # --- the frozen configuration matches the code -----------------------
    receipt = json.loads((MODELS / "FREEZE_RECEIPT.json").read_text())
    check("the frozen artifact's config digest matches the code",
          receipt["config_digest"] == config.config_digest(),
          receipt["config_digest"][:16])
    check("the frozen artifact on disk matches its receipt hash",
          sha256_file(MODELS / "module_a_final01.joblib") == receipt["artifact_sha256"],
          receipt["artifact_sha256"][:16])
    check("the frozen weights are the ones the docs name",
          receipt["config"]["weights"] == config.WEIGHTS, json.dumps(config.WEIGHTS))

    # --- the holdout run --------------------------------------------------
    prediction = json.loads((PREDICTION / "HOLDOUT_PREDICTION_RECEIPT.json").read_text())
    for epoch, recorded in prediction["outputs"].items():
        path = PREDICTION / recorded["file"]
        check(f"holdout {epoch} h predictions unchanged since stage 8 wrote them",
              sha256_file(path) == recorded["sha256"], recorded["sha256"][:16])
    metrics = _csv("09_holdout_metrics.csv").set_index("epoch_h")
    check("the 168 h holdout result is 65 TP, 13 FP, 25 FN",
          (int(metrics.loc[168, "tp"]), int(metrics.loc[168, "fp"]),
           int(metrics.loc[168, "fn"])) == (65, 13, 25),
          metrics.loc[168, ["tp", "fp", "fn"]].to_dict())
    check("the published floor flags 78 of 1,343 holdout components",
          int(metrics.loc[168, "flagged"]) == 78, int(metrics.loc[168, "flagged"]))

    # --- the blind spot ---------------------------------------------------
    blind = _csv("05_blindspot.csv")
    within = blind[blind.population.eq("static, within spec")]
    check("within-spec static offsets are detected 6 of 21 across both splits",
          (int(within.detected.sum()), int(within.actual.sum())) == (6, 21),
          f"{int(within.detected.sum())} of {int(within.actual.sum())}")

    # --- the score is honest about what it is -----------------------------
    frame = pd.read_csv(PREDICTION / "ModuleA_Final_Holdout_168h.csv")
    floor = prediction["monitor_floor"]
    implied = frame["module_a_score"].ge(floor)
    check("one threshold on module_a_score reproduces module_a_disposition",
          bool((implied == frame["module_a_disposition"].eq("MONITOR")).all()),
          f"floor {floor:.10f}")
    check("Module A never emits REJECT",
          set(frame["module_a_disposition"]) <= {"PASS", "MONITOR"},
          sorted(set(frame["module_a_disposition"])))

    # --- no document quotes a number that is not in results/ ---------------
    stale = []
    for doc in sorted(DOCS.glob("*.md")):
        text = doc.read_text()
        for forbidden in ["78.89%", "0.936978 is the operating threshold",
                          "normal-reference split"]:
            if forbidden in text and "NOT" not in text[max(0, text.find(forbidden) - 120):
                                                       text.find(forbidden)]:
                stale.append(f"{doc.name}: {forbidden}")
    check("no document repeats a superseded figure without marking it superseded",
          not stale, stale or "clean")

    # ================= pre-integration hardening =========================

    # --- robustness -------------------------------------------------------
    robustness = _csv("12_robustness.csv")
    for _, row in robustness.iterrows():
        check(f"robustness / {row['kind'].lower()}: {row['case']}",
              row["status"] in ("PASS", "REVIEW"), str(row["detail"])[:110])
    check("every promised invariance holds with zero score drift",
          bool((robustness[robustness.kind.eq("INVARIANCE")]["max_score_drift"] == 0).all()),
          "max drift across invariance cases")
    check("no robustness case failed",
          not bool(robustness.status.eq("FAIL").any()),
          int(robustness.status.eq("FAIL").sum()))

    # --- score semantics ---------------------------------------------------
    semantics = _json("13_score_semantics.json")
    check("the score is monotone in the observed anomaly rate",
          semantics["question_1_monotone"]["answer"] is True,
          semantics["question_1_monotone"]["statement"])
    check("the score is documented as NOT a probability",
          semantics["question_2_is_it_a_probability"]["answer"] is False,
          f"largest gap {semantics['question_2_is_it_a_probability']['largest_gap_between_score_and_observed_rate']:.3f}")
    check("an individual score moves by less than 0.05 when a lot leaves the reference",
          semantics["question_3_individual_stability"]["max_abs_drift"] < 0.05,
          semantics["question_3_individual_stability"]["max_abs_drift"])
    bands = _csv("13_score_bands.csv")
    check("no component below score 0.5 is anomalous on calibration",
          int(bands.iloc[0]["anomalies"]) == 0, bands.iloc[0].to_dict())

    # --- sensitivity -------------------------------------------------------
    sensitivity = _json("14_sensitivity.json")
    per_variant = _csv("14_per_variant.csv")
    check("no device variant is broken - every variant recalls above 0.6",
          bool((per_variant["recall"] > 0.6).all()),
          per_variant.set_index("device_variant")["recall"].round(3).to_dict())
    check("no device variant exceeds a 2% false-alarm rate",
          bool((per_variant["fpr"] < 0.02).all()),
          per_variant.set_index("device_variant")["fpr"].round(4).to_dict())
    per_severity = _csv("14_per_severity.csv")
    subtle = per_severity[per_severity.severity.eq("SUBTLE")].iloc[0]
    check("subtle anomalies are the weak case and are reported as such",
          float(subtle["detection_rate"]) < 0.6,
          f"SUBTLE detection {float(subtle['detection_rate']):.3f}")

    # --- fusion join -------------------------------------------------------
    fusion = _json("15_fusion_dryrun.json")
    for entry in fusion["checks"]:
        check(f"fusion join / {entry['check']}", entry["status"] == "PASS", entry["detail"])
    check("the fusion join keeps all 1,343 holdout components",
          fusion["rows_joined"] == 1343, fusion["rows_joined"])
    check("no fusion join check failed", fusion["failures"] == 0, fusion["failures"])
    check("B corroboration is recorded as an association, never as a rule",
          "cannot become a rule" in fusion["warning"] or "VIEW, not a rule" in fusion["warning"],
          fusion["warning"][:80])

    # --- the confusion matrix ---------------------------------------------
    matrices = _csv("20_confusion_matrices.csv")
    cm = _json("20_confusion_matrices.json")
    check("every reported confusion matrix balances: TP+TN+FP+FN = n",
          cm["all_balance"] is True, f"{cm['results_reported']} matrices")
    for _, r in matrices.iterrows():
        check(f"matrix balances / {r['result']}",
              int(r.tp + r.tn + r.fp + r.fn) == int(r.n),
              f"{int(r.tp)}+{int(r.tn)}+{int(r.fp)}+{int(r.fn)} = {int(r.n)}")
    reconciliation = _csv("20_reconciliation.csv")
    for _, r in reconciliation.iterrows():
        if pd.notna(r["recall+fnr"]):
            check(f"recall + FNR = 1 / {r['result']}",
                  abs(float(r["recall+fnr"]) - 1.0) < 1e-9, r["recall+fnr"])
        if pd.notna(r["specificity+fpr"]):
            check(f"specificity + FPR = 1 / {r['result']}",
                  abs(float(r["specificity+fpr"]) - 1.0) < 1e-9, r["specificity+fpr"])
    head = cm["headline"]
    check("the holdout 168 h matrix is 65 TP, 1240 TN, 13 FP, 25 FN",
          (head["holdout_168h"]["tp"], head["holdout_168h"]["tn"],
           head["holdout_168h"]["fp"], head["holdout_168h"]["fn"]) == (65, 1240, 13, 25),
          head["holdout_168h"])
    check("the datasheet rule has zero false positives across all three splits",
          head["datasheet_rule_all_splits"]["fp"] == 0,
          head["datasheet_rule_all_splits"])
    check("the datasheet rule's 5,076 true negatives are reported alongside its zero FP",
          head["datasheet_rule_all_splits"]["tn"] == 5076,
          head["datasheet_rule_all_splits"]["tn"])
    check("the confusion implementation is cross-checked against sklearn every run",
          "sklearn" in cm["cross_checked_against"], cm["cross_checked_against"])
    corpus_docs = "\n".join((DOCS / d).read_text() for d in
                             ["MASTER_PROMPT_CONFUSION_MATRIX.md"])
    check("the confusion-matrix brief names all four outcomes explicitly",
          all(w in corpus_docs for w in ["true positive", "true negative",
                                         "false positive", "false negative"]),
          "TP / TN / FP / FN")
    # The word is allowed — explaining WHY accuracy is not reported requires it. What
    # is forbidden is an accuracy FIGURE presented as a result: "accuracy 94%".
    # (An earlier revision of this check banned the word, and promptly failed on the
    #  sentence explaining that accuracy is not reported.)
    accuracy_figure = re.compile(r"accurac(y|ies)[^.\n]{0,40}?\d+(\.\d+)?\s*%",
                                 re.IGNORECASE)
    quoting = []
    for doc in [ROOT / "README.md", *sorted(DOCS.glob("*.md"))]:
        for hit in accuracy_figure.finditer(doc.read_text()):
            context = hit.group(0)
            # the counter-example in the brief is the point, not a claim
            if "flags nothing" in context or "flagging nothing" in context:
                continue
            quoting.append(f"{doc.name}: {context.strip()}")
    check("no document presents an accuracy figure as a result",
          not quoting, quoting or "clean")

    # --- provenance --------------------------------------------------------
    provenance = json.loads((ROOT / "PROVENANCE_ADDENDUM.json").read_text())
    check("the model config digest has not moved since the freeze",
          provenance["model_config_stable_since_freeze"] is True,
          provenance["model_config_digest"][:16])
    check("the runtime contract digest has not moved since the freeze",
          provenance["runtime_contract_stable_since_freeze"] is True,
          provenance["runtime_contract_digest"][:16])
    check("there is no build mismatch", provenance["build_mismatch"] is False,
          provenance["build_mismatch"])
    check("the at-freeze source baseline lives outside the regenerable results/ tree",
          (MODELS / "SOURCE_TREE_AT_FREEZE.json").exists()
          and not (RESULTS / "17_source_tree_at_freeze.json").exists(),
          "models/SOURCE_TREE_AT_FREEZE.json")
    # NOTE: the reproducibility verdict is deliberately NOT checked here. It is
    # produced by comparing two runs, so a check on it inside a per-run stage is
    # circular — the file exists in whichever run compared, and the two can then never
    # converge. stage 19 is the outer check and exits non-zero on its own.
    check("every prediction-path file that changed after the freeze is explained",
          len(provenance["files_changed_in_the_prediction_path"])
          == len(provenance["prediction_path_changes_explained"]),
          provenance["files_changed_in_the_prediction_path"])
    for entry in provenance["prediction_path_changes_explained"]:
        check(f"post-freeze change to {entry['file']} carries proof it changed nothing",
              bool(entry.get("proof_it_changed_nothing")), entry["what"])

    # --- the boundary defect that hardening found --------------------------
    from modulea import tiers as _tiers
    check("a perfect statistical score stays below the out-of-specification floor",
          float(_tiers.compose_score(np.array([1.0]), np.array([False]),
                                     np.array([0.0]))[0]) < _tiers.CONFIRMED_FLOOR,
          "statistical band is closed below the floor")

    # --- the packet --------------------------------------------------------
    identity_path = RESULTS / "18_release_identity.json"
    if with_packets and identity_path.exists():
        identity = json.loads(identity_path.read_text())
        check("the packet identity carries the same config digest as the code",
              identity["digests"]["model_config"] == config.config_digest(),
              identity["digests"]["model_config"][:16])
        check("the packet publishes the monitor floor",
              abs(identity["monitor_floor"]
                  - prediction["monitor_floor"]) < 1e-15, identity["monitor_floor"])
        check("the packet states Module A emits no REJECT",
              identity["emits_reject"] is False, identity["emits_disposition"])
        packet = ROOT / "packets/SIH26170_FINAL_Anushka_ModuleA_Packet"
        for required in ["README_Anushka.md".replace("Anushka", "ANUSHKA"),
                         "RELEASE_IDENTITY.json", "SHA256SUMS.txt",
                         "contract/runtime_contract.json",
                         "contract/ModuleA_Output_Contract.csv",
                         "prediction/ModuleA_Final_Holdout_168h.csv",
                         "prediction/HOLDOUT_PREDICTION_RECEIPT.json",
                         "example/input_one_complete_lot.csv",
                         "example/output_one_complete_lot.csv",
                         "docs/INTEGRATION_NOTE.md", "docs/LIMITATIONS.md",
                         "PROVENANCE_ADDENDUM.json"]:
            check(f"packet contains {required}", (packet / required).exists(), required)
        # every packet, not just Anushka's, must verify its own checksums
        for other in sorted((ROOT / "packets").glob("SIH26170_FINAL_*_ModuleA_Packet")):
            sums = other / "SHA256SUMS.txt"
            if not sums.exists():
                check(f"packet {other.name} has SHA256SUMS.txt", False, "missing")
                continue
            listed = [l.split("  ", 1) for l in sums.read_text().strip().splitlines()]
            bad = [n for d_, n in listed
                   if (other / n).exists() and sha256_file(other / n) != d_]
            check(f"packet {other.name} matches its own checksums", not bad,
                  bad or f"{len(listed)} files")
            ident = other / "RELEASE_IDENTITY.json"
            if ident.exists():
                other_identity = json.loads(ident.read_text())
                check(f"packet {other.name} carries the same model digest",
                      other_identity["digests"]["model_config"] == config.config_digest(),
                      other_identity["digests"]["model_config"][:16])

        if (packet / "SHA256SUMS.txt").exists():
            listed = [l.split("  ", 1) for l in
                      (packet / "SHA256SUMS.txt").read_text().strip().splitlines()]
            bad = [name for digest, name in listed
                   if (packet / name).exists() and sha256_file(packet / name) != digest]
            check("every file in the packet matches its listed checksum", not bad, bad or "clean")

    # --- the fail-safe -----------------------------------------------------
    state_path = ROOT / "state/CHECKPOINT.json"
    if state_path.exists():
        state = json.loads(state_path.read_text())
        check("the checkpoint records no failed step",
              not [s for s in state["steps"] if s["status"] == "FAILED"],
              f"{len(state['steps'])} steps recorded")
        check("the checkpoint is not blocked", state.get("blocked_on") in (None, ""),
              state.get("blocked_on"))
        check("CONTINUATION.md exists so an interrupted session can resume",
              (ROOT / "CONTINUATION.md").exists(), "present")

    # --- every figure quoted in a document, against its source -------------
    # The reverse direction: the document says X, and X must be what results/ holds.
    # A figure that appears in prose and nowhere here is exactly the unsupported claim
    # the master prompt forbids.
    spec_json = _json("02_spec_witness.json")
    nested_shipped = nested[nested.arm.eq("shipped")].iloc[0]
    curve = _csv("03_operating_points.csv")
    frozen_point = curve[curve.fpr_budget.eq(0.01)].iloc[0]
    zero_point = curve[curve.fpr_budget.eq(0.0)].iloc[0]
    blind_within = blind[blind.population.eq("static, within spec")]
    blind_fails = blind[blind.population.eq("static, fails spec")]
    ranking = _json("09_ranking_comparison.json")
    behaviour = _csv("09_holdout_by_behaviour.csv").set_index("defect_behavior")

    figures = [
        ("81 spec flags across the release", "81",
         int(at168["flagged"].sum()) == 81),
        ("5,076 normal components scored", "5,076",
         spec_json["normals_scored_at_168h"] == 5076),
        ("95% upper bound 0.06%", "0.06%",
         abs(spec_json["false_positive_rate_95pct_upper_bound"] - 0.00059) < 0.0001),
        ("shipped nested recall 83.3%", "83.3%",
         abs(float(nested_shipped.recall) - 0.833333) < 0.001),
        ("shipped nested FPR 1.06%", "1.06%",
         abs(float(nested_shipped.fpr) - 0.010563) < 0.0005),
        ("shipped nested estimate 45 of 54 at 9", "45 of 54 at 9",
         int(nested_shipped.tp) == 45 and int(nested_shipped.fp) == 9),
        ("frozen operating threshold", "0.9395405",
         abs(float(frozen_point.threshold) - 0.9395405078597341) < 1e-9),
        ("1% budget catches 47 of 54", "47",
         int(frozen_point.tp) == 47 and int(frozen_point.fp) == 8),
        ("zero-FP statistical threshold catches 38 of 54", "38",
         int(zero_point.tp) == 38 and int(zero_point.fp) == 0),
        ("holdout 78 flags", "78", int(metrics.loc[168, "flagged"]) == 78),
        ("holdout CONFIRMED tier is 23 components", "23",
         int(confirmed["n"]) == 23),
        ("within-spec static detected 6 of 21", "6 of 21",
         (int(blind_within.detected.sum()), int(blind_within.actual.sum())) == (6, 21)),
        ("spec-failing static detected 7 of 7", "7 of 7",
         (int(blind_fails.detected.sum()), int(blind_fails.actual.sum())) == (7, 7)),
        ("holdout PR AUC of the frozen config", "0.8166",
         abs(ranking["holdout_pr_auc_final01"] - 0.8166) < 0.0005),
        ("holdout PR AUC of the inherited weights", "0.8239",
         abs(ranking["holdout_pr_auc_inherited"] - 0.8239) < 0.0005),
        ("accelerating drift detected 17 of 17", "17",
         int(behaviour.loc["ACCELERATING_DRIFT", "detected"]) == 17),
        ("static outliers detected 5 of 18", "5",
         int(behaviour.loc["STATIC_OUTLIER", "detected"]) == 5),
        ("12 calibration lots", "12",
         int(_csv("01_split_structure.csv").set_index("split").loc["calibration", "lots"]) == 12),
        ("all 180 variant-feature references used MAD", "180",
         int(_csv("01_scale_ladder.csv")["MAD"].sum()) == 180),
        ("seven variant-parameter cells have no datasheet limit", "seven",
         int(_csv("02_spec_coverage.csv").iloc[0]["cells_without_limit"]) == 7),
    ]
    for name, literal, ok in figures:
        check(f"figure / {name}", ok, f"quoted as '{literal}'")

    # and the figures must actually appear somewhere in the documents
    corpus = "\n".join((DOCS / d).read_text() for d in
                        ["VALIDATION_SUMMARY.md", "MODEL_CARD.md", "LIMITATIONS.md",
                         "README.md" if (DOCS / "README.md").exists() else "MODEL_CARD.md"])
    corpus += (ROOT / "README.md").read_text()
    for name, literal, _ in figures:
        check(f"figure quoted in a document / {name}", literal in corpus, literal)



    # --- documents that must exist -----------------------------------------
    for doc in ["MASTER_PROMPT.md", "MASTER_PROMPT_DEPLOYMENT.md",
                "MASTER_PROMPT_FINAL_VERIFICATION.md", "MASTER_PROMPT_CONFUSION_MATRIX.md",
                "ACCEPTANCE_CRITERIA.md", "FUTURE_RELEASE_ITEMS.md", "TEAM_HANDOFF.md",
                "RELEASE_CHANGELOG.md", "MODEL_CARD.md",
                "VALIDATION_SUMMARY.md", "DECISION_LOG.md", "LIMITATIONS.md",
                "INTEGRATION_NOTE.md", "RUNBOOK.md", "IMPROVEMENTS.md"]:
        check(f"docs/{doc} exists", (DOCS / doc).exists(), doc)

    return out



def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-packets", action="store_true",
                        help="also check the built packets. Off by default so the "
                             "pre-packet ledger is deterministic: stage 18 embeds this "
                             "count, and a count that depends on stage 18's own output "
                             "is circular and can never reproduce across two runs.")
    args = parser.parse_args()
    table = pd.DataFrame(checks(args.with_packets))
    # Two ledgers on purpose. 10_verify_claims.csv is the release ledger and is written
    # BEFORE the packets exist, so stage 18 can embed its count and still be idempotent:
    # a packet whose content depends on when it was built cannot be verified by its
    # recipient. The packet self-checks land in their own file.
    out = ("10_verify_claims_with_packets.csv" if args.with_packets
           else "10_verify_claims.csv")
    table.to_csv(RESULTS / out, index=False)
    print(table.to_string(index=False))
    failed = table.status.eq("FAIL").any()
    print("\nCLAIM VERIFICATION", "FAILED" if failed else "PASSED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
