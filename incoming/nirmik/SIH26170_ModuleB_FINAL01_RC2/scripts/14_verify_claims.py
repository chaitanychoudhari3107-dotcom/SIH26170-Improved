"""
Stage 14 — check the prose against the numbers.

Documentation drifts. Someone reruns a stage, a number moves, and the model card
still quotes the old one — and a model card that quotes a stale number is worse
than no model card, because it will be believed.

This script asserts every load-bearing figure in README.md, the docs, the runner
scripts' own printed output, the notebooks and RELEASE_MANIFEST.json against the
CSVs in results/. It does not check prose; it checks claims that are numbers and
claims that are structural guarantees.

Two things it deliberately does NOT do. It does not quote its own check count in
a document — a number that has to be edited every time a check is added is a
number that will be stale — the count lives in RELEASE_MANIFEST.json, written by
the run itself. And it does not open the holdout: the split's structure comes
from moduleb.holdout_manifest, verified against the delivery hash (decision D14).

Run it after any rerun, and before sending anything to the team.
"""
from _common import ROOT, Stage, header

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

import moduleb
from moduleb import (config, dataio, decisions, freeze, holdout_manifest,
                     serving)
from moduleb.constants import PARAMS

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, bool(ok), detail))


def doc(name: str) -> str:
    return (ROOT / name).read_text()


def main() -> int:
    with Stage("STAGE 14 — verify documented claims against results/"):
        R = dataio.RESULTS
        # Release-state paths, defined early because several later sections ask which
        # state the package is in.
        out = ROOT / "results" / "ModuleB_Final_Holdout_Predictions.csv"
        model = ROOT / "models" / "module_b_final01.joblib"
        readme = doc("README.md")
        card = doc("docs/MODEL_CARD.md")
        find = doc("docs/FINDINGS_FOR_TEAM.md")
        acc = doc("docs/ACCEPTANCE_CRITERIA.md")

        # ---------------------------------------------------------- dataset
        meta = dataio.load_dataset_version()
        splits = {n: dataio.load_split(n) for n in ("train", "calibration")}
        holdout_manifest.verify_delivery_hash(dataio.file_sha256(dataio.PATHS["holdout"]))
        rows = sum(s.n_rows for s in splits.values()) + holdout_manifest.N_ROWS
        lots = sum(s.n_lots for s in splits.values()) + holdout_manifest.N_LOTS
        check("dataset totals match the manifest", rows == meta["rows"] and lots == meta["lots"],
              f"{rows} rows / {lots} lots")
        check("README quotes 5,400 rows and 72 lots",
              "5,400 rows, 72 lots" in readme)
        check("README quotes the 42/12/18 split", "42/12/18" in find)
        check("split sizes really are 42/12/18",
              (splits["train"].n_lots, splits["calibration"].n_lots,
               holdout_manifest.N_LOTS) == (42, 12, 18))
        check("the declared holdout structure matches the delivery hash", True,
              holdout_manifest.SHA256[:16])

        # ---------------------------------------------------------- stage 3
        pt = pd.read_csv(R / "03_paired_lot_test.csv").set_index("param")
        cvm = pd.read_csv(R / "03_cv_metrics.csv")
        pooled = (cvm[(cvm.variant == "ALL") & (cvm.model == "MODULE_B")]
                  .set_index("param").MAE)
        better = sorted(pt.index[pt.verdict == "BETTER"])
        check("4 of 6 parameters are BETTER", len(better) == 4, ", ".join(better))
        check("README says four of six", "four of six" in readme)
        check("findings says four of six", "four of six" in find.lower())
        check("model card quotes pooled row-weighted MAE, labelled as such",
              "row-weighted pooled" in card)
        for p in PARAMS:
            m = re.search(rf"\|\s*{re.escape(p)}\s*\|\s*([0-9.]+)\s*(?:µA|ns)\s*\|", card)
            if m:
                check(f"model card MAE for {p}",
                      abs(float(m.group(1)) - pooled[p]) < 5e-6,
                      f"card {m.group(1)} vs results {pooled[p]:.5f}")
        gains = pt.gain_pct
        check("BETTER gains are in the 6.8-9.0% band quoted",
              6.7 <= gains[better].min() <= 9.1 and 6.7 <= gains[better].max() <= 9.1,
              f"{gains[better].min():.2f}-{gains[better].max():.2f}%")
        check("lots won for BETTER params are 30-34 of 42",
              pt.loc[better, "lots_won"].min() >= 30 and pt.loc[better, "lots_won"].max() <= 34,
              f"{pt.loc[better, 'lots_won'].min()}-{pt.loc[better, 'lots_won'].max()}")
        check("all BETTER p-values <= 0.0015",
              pt.loc[better, "wilcoxon_p"].max() <= 0.0015,
              f"max p {pt.loc[better, 'wilcoxon_p'].max():.5f}")
        check("IDDQ and Active_Supply_Current are TIEs on train CV",
              pt.loc["IDDQ", "verdict"] == "TIE"
              and pt.loc["Active_Supply_Current", "verdict"] == "TIE")

        # ---------------------------------------------------------- stage 4
        bf = pd.read_csv(R / "04_best_vs_frozen.csv")
        worst = bf.best_minus_frozen_pct.max()
        check("no grid config beats the frozen one by >5%", worst < config.TIE_THRESHOLD_PCT,
              f"max {worst:.2f}%")
        check("README quotes the 4.5% figure", "4.5" in readme and "4.5" in find,
              f"actual {worst:.2f}%")

        # ---------------------------------------------------------- stage 5/7
        calp = pd.read_csv(R / "05_calibration_paired_test.csv").set_index("param")
        il = calp.loc["Input_Leakage_Current", "gain_pct"]
        check("Input_Leakage is ~33% worse on calibration", -34 < il < -32, f"{il:.2f}%")
        check("docs state the -33% figure", "33 %" in find or "33%" in find or "−33 %" in find)
        ec = pd.read_csv(R / "07_error_concentration.csv").set_index("param")
        share = ec.loc["Input_Leakage_Current", "worst_row_share_pct"]
        check("one row carries ~28% of Input_Leakage calibration error",
              27 < share < 29, f"{share:.2f}%")
        tt = pd.read_csv(R / "07_target_tails.csv").set_index("param")
        check("Input_Leakage max target is 13.3x", abs(tt.loc["Input_Leakage_Current", "max"] - 13.3193) < 0.01)
        check("Input_Leakage max/p99 is ~54x", 53 < tt.loc["Input_Leakage_Current", "max_over_p99"] < 55,
              f"{tt.loc['Input_Leakage_Current', 'max_over_p99']:.1f}x")
        check("no other parameter exceeds 15x max/p99",
              tt.drop("Input_Leakage_Current").max_over_p99.max() < 15,
              f"max {tt.drop('Input_Leakage_Current').max_over_p99.max():.1f}x")
        cs = pd.read_csv(R / "07_cap_sweep.csv")
        c05 = cs[(cs.cap == 0.5) & (cs.split == "calibration")]
        touched = c05[c05.n_capped > 0]
        check("a 0.5 cap touches exactly one calibration forecast",
              len(touched) == 1 and int(touched.n_capped.iloc[0]) == 1)
        check("the 0.5 cap only touches Input_Leakage_Current",
              set(touched.param) == {"Input_Leakage_Current"})
        gain = float(touched.MAE_change_pct.iloc[0])
        check("the 0.5 cap removes ~28% of that MAE", 27 < gain < 29, f"{gain:.2f}%")
        check("FORECAST_REL_DELTA_CAP is still off", config.FORECAST_REL_DELTA_CAP is None)

        # ---------------------------------------------------------- stage 6
        ft = pd.read_csv(R / "06_predeclared_falltime_decision.csv").iloc[0]
        check("the pre-declared fall-time rule did not fire", not bool(ft.rule_fires))
        check("it lost on 10 of 12 lots", int(ft.lots_won) == 2 and int(ft.n_lots) == 12,
              f"{ft.lots_won}/{ft.n_lots}")
        check("config still uses the frozen fall-time feature set",
              config.RECOMMENDED["Output_Fall_Time"]["features"] == ft.from_set)
        check("docs quote -1.5% and 2 of 12", "1.5" in find and "2 of 12" in find)

        # ---------------------------------------------------------- stage 8
        rates = pd.read_csv(R / "08_reason_code_rates.csv")
        cal = rates[(rates.split == "calibration") & (rates.param == "ANY")].set_index("code")
        any_rate = float(cal.loc["ANY_CODE", "rate"])
        top = float(cal.drop("ANY_CODE").rate.max())
        check("any-code rate is 14.9%", abs(any_rate - 0.149) < 0.002, f"{any_rate:.4f}")
        check("top single-code rate is 10.9%", abs(top - 0.109) < 0.002, f"{top:.4f}")
        check("any-code rate is under the acceptance limit", any_rate <= config.MAX_ANY_FLAG_RATE)
        check("every single code is under its limit", top <= config.MAX_FLAG_FIRING_RATE)
        check("docs quote 14.9% flagged", "14.9" in readme and "14.9" in card)

        # ---------------------------------------------------------- stage 9
        cov = pd.read_csv(R / "09_envelope_coverage.csv")
        op = cov[cov.tau == config.ENVELOPE_TAU].set_index("param")
        check("marginal coverage spans 0.933-0.974",
              abs(op.marginal_coverage.min() - 0.933) < 0.002
              and abs(op.marginal_coverage.max() - 0.974) < 0.002,
              f"{op.marginal_coverage.min():.3f}-{op.marginal_coverage.max():.3f}")
        check("tail coverage spans 0.407-0.769 (corrected, F3)",
              abs(op.tail_coverage.min() - 0.4066) < 0.003
              and abs(op.tail_coverage.max() - 0.7692) < 0.003,
              f"{op.tail_coverage.min():.3f}-{op.tail_coverage.max():.3f}")
        check("Output_Rise_Time is the worst tail", op.tail_coverage.idxmin() == "Output_Rise_Time")
        check("docs never call the envelope a screen",
              "95% safety guarantee" not in card and "95 % safety guarantee" not in card)
        check("the model card states the tail limitation",
              "thereby safe" in card)
        check("the integration note states it too",
              "do not treat" in doc("docs/INTEGRATION_NOTE.md").lower())

        # ---------------------------------------------------------- structural
        base, limits = dataio.load_specs()
        check("exactly 7 Device_Specs limit cells are empty",
              int(limits.isna().to_numpy().sum()) == 7)
        check("docs say seven empty cells",
              "seven" in card.lower() and "seven" in find.lower())
        sample = pd.read_csv(R / "08_calibration_contract_sample.csv")
        check("no disposition column is emitted", "module_b_disposition" not in sample.columns)
        ref = dataio.expected_contract_columns()
        check("every reference contract column is produced",
              all(c in sample.columns for c in ref))
        check("24 evidence columns are produced",
              len([c for c in sample.columns if c.startswith("evidence_")]) == 24)

        # ---------------------------------------------------------- R1 corrections
        # Review round 1, 19 Sep 2026. These are mostly NEGATIVE checks: a corrected
        # claim is only corrected if the old wording is gone everywhere. A checker
        # that merely confirms the new sentence exists would pass while the old one
        # still sits two paragraphs above it.
        docs = {n: doc(f"docs/{n}") for n in
                ("COMPLETE_GUIDE.md", "MODEL_CARD.md", "INTEGRATION_NOTE.md",
                 "ACCEPTANCE_CRITERIA.md", "FINDINGS_FOR_TEAM.md", "DECISION_LOG.md",
                 "RUNBOOK.md", "MASTER_PROMPT.md", "TEAM_HANDOFF.md",
                 "FINAL_FREEZE_READINESS.md", "RELEASE_CHANGELOG.md",
                 "FUTURE_RELEASE_ITEMS.md", "ROUND2_FINAL_ADJUDICATION.md")
                if (ROOT / "docs" / n).exists()}
        docs["README.md"] = readme
        everywhere = "\n".join(docs.values())

        # R2: the executable surfaces are scanned too. A withdrawn claim that
        # survives in a script's printed output is still shipped — it just says it
        # to a terminal instead of to a reader.
        executable = {}
        for sp in sorted((ROOT / "scripts").glob("*.py")):
            if sp.name == Path(__file__).name:
                continue          # this file quotes every withdrawn phrase on purpose
            executable[f"scripts/{sp.name}"] = sp.read_text()
        for nb in sorted((ROOT / "notebooks").glob("*.ipynb")):
            executable[f"notebooks/{nb.name}"] = nb.read_text()
        for mp in sorted((ROOT / "moduleb").glob("*.py")):
            executable[f"moduleb/{mp.name}"] = mp.read_text()
        if (ROOT / "RELEASE_MANIFEST.json").exists():
            executable["RELEASE_MANIFEST.json"] = (ROOT / "RELEASE_MANIFEST.json").read_text()

        MARKERS = ("corrected", "previously", "superseded", "withdrawn", "no longer",
                   "review finding", "used to", "~~", "closed 19 sep", "before the freeze",
                   "was written before", "old criterion", "it was previously")

        def nowhere(phrase, label, allow=()):
            """A withdrawn phrase may survive ONLY inside a correction note.

            Deleting every trace would destroy the provenance the review asked us to
            keep, so the test is not "absent" but "never asserted": each surviving
            occurrence must sit within 400 characters of a correction marker.

            Scanned across the documents AND the executable surfaces — scripts,
            notebooks, package source and the release manifest — because a stale
            claim printed to a terminal is still a claim the project makes.
            """
            offenders = []
            for n, t in {**docs, **executable}.items():
                if n in allow:
                    continue
                for m in re.finditer(re.escape(phrase), t):
                    window = t[max(0, m.start() - 400): m.end() + 400].lower()
                    if not any(k in window for k in MARKERS):
                        offenders.append(f"{n}@{m.start()}")
            check(f"R1: '{label}' is never asserted", not offenders, ", ".join(offenders))

        # F1 — the withdrawn single-component invariance claim
        nowhere("Batch size does not matter", "batch size does not matter")
        nowhere("One component or 1,343 gives identical", "one component == 1,343")
        nowhere("identical across row order and batch size", "F5 as written before")
        check("R1/F1: cohort contract is stated", "cohort-level" in everywhere)
        check("R1/F1: MIN_LOT_COHORT exists and is 30", config.MIN_LOT_COHORT == 30)
        check("R1/F1: the 7.18% divergence is on record", "7.18" in everywhere)
        check("R1/F1: the completeness guard is wired into predict_frame",
              "serving.assert_delivery_complete" in
              Path(ROOT / "moduleb" / "predict.py").read_text())
        check("R1/F1: the replacement test exists",
              "test_raw_request_composition_changes_timing_forecasts"
              in Path(ROOT / "tests" / "test_pipeline.py").read_text())
        check("R1/F1: the old test name is gone",
              "def test_prediction_is_batch_size_invariant"
              not in Path(ROOT / "tests" / "test_pipeline.py").read_text())

        # F2 — the conformal overclaim
        nowhere("finite-sample valid", "finite-sample validity")
        check("R1/F2: the empirical claim is stated",
              "empirical" in docs["MODEL_CARD.md"] and "exchangeab" in docs["MODEL_CARD.md"])

        # F3 — the tail metric
        check("R1/F3: coverage_report ranks by true drift",
              "true_relative_drift_from_24h" in
              Path(ROOT / "moduleb" / "envelope.py").read_text())
        superseded = R / "09_envelope_coverage_SUPERSEDED_2026-09-18_residual_ranked.csv"
        check("R1/F3: the superseded figures are preserved", superseded.exists())
        check("R1/F3: results carry the new rank basis",
              "tail_rank_basis" in pd.read_csv(R / "09_envelope_coverage.csv").columns)
        nowhere("0.473", "the superseded tail figure 0.473")
        check("R1/F3: corrected tail range is quoted",
              all(f"{op.loc[p_, 'tail_coverage']:.4f}"[:5] in everywhere
                  or f"{op.loc[p_, 'tail_coverage']:.3f}" in everywhere for p_ in PARAMS))

        # F4 / D11
        check("R1/F4: the cap is still off", config.FORECAST_REL_DELTA_CAP is None)
        check("R1/F4: D11 is recorded as closed",
              "LEAVE_OFF" in docs["DECISION_LOG.md"])
        nowhere("must close before freeze", "D11 still open")
        nowhere("The one open decision", "an open decision remains")

        # F5 — the denominator
        nowhere("one forecast in 5,400", "the 5,400 cap denominator")
        nowhere("rows touched (of 5,400)", "the 5,400 cap column header")
        check("R1/F5: split denominators are used",
              "906 rows" in docs["COMPLETE_GUIDE.md"] and "3,151 rows" in docs["COMPLETE_GUIDE.md"])

        # F6 / F7 / A1
        nowhere("ceiling on what a same-parameter", "r as a predictability ceiling")
        nowhere("validation protocol is sound", "CV proves the protocol sound")
        nowhere("sparse enough to be actionable", "sparsity implies actionability")
        check("R1/F7: the relative-effect diagnostic was produced",
              (R / "05_relative_effect_transfer.csv").exists())

        # the digest must NOT have moved
        check("R1: config digest unchanged by the R1 fixes",
              config.frozen_config_digest().startswith("8d0621941f86fbb8"),
              config.frozen_config_digest()[:16])

        # ---------------------------------------------------------- R2 corrections
        # Round 2, 19 Sep 2026 — release engineering. The four freeze blockers, the
        # provenance correction, and the withdrawn claims that were still being
        # asserted by executable surfaces rather than by documents.
        freeze_src = (ROOT / "moduleb" / "freeze.py").read_text()
        serving_src = (ROOT / "moduleb" / "serving.py").read_text()

        # P2 — the nine withdrawn/overstated claims, now scanned in code as well
        nowhere("is the ceiling on what a same-parameter", "r as a predictability ceiling")
        nowhere("sparse enough to be actionable", "sparsity implies actionability")
        nowhere("This is not a retune", "the cap is 'not a retune'")
        nowhere("has not been opened", "the holdout was never opened")
        nowhere("was not opened by it", "the holdout was never opened (stage 10)")
        nowhere("53 / 53", "the stale 53-check count")
        nowhere("asserts 53 load-bearing", "the stale 53-figure count")
        nowhere("finite-sample valid", "finite-sample conformal validity")
        nowhere("one forecast in 5,400", "the 5,400 cap denominator")
        nowhere("validation protocol is sound", "CV proves the protocol sound")
        check("R2/P2: the check count is not hard-coded in a document",
              "RELEASE_MANIFEST" in docs["COMPLETE_GUIDE.md"])

        # P0-B1 — the serving contract
        check("R2/P0-B1: completeness must be proved, not assumed",
              serving.REQUIRES_COMPLETENESS_PROOF)
        check("R2/P0-B1: a partial lot is never the default",
              serving.PARTIAL_LOT_DEFAULT is False)
        check("R2/P0-B1: MIN_LOT_COHORT is only a secondary floor",
              "secondary sanity floor" in
              serving.runtime_contract_payload()["min_lot_cohort_role"])
        check("R2/P0-B1: both completeness proofs are implemented",
              "request_metadata" in serving_src and "delivery_attestation" in serving_src)
        check("R2/P0-B1: the override is recorded, not silent",
              "offending_lots" in serving_src and "report.clean" in serving_src)
        check("R2/P0-B1: the serving tests ship", (ROOT / "tests" / "test_serving.py").exists())

        # P0-B2 — the sign-off lives inside the artifact
        check("R2/P0-B2: the manifest is built before serialisation",
              freeze_src.index("manifest = build_manifest(") < freeze_src.index("joblib.dump("))
        check("R2/P0-B2: a freeze without sign-off is refused",
              "cannot be built without a team sign-off" in freeze_src)
        check("R2/P0-B2: load_frozen compares embedded and sidecar manifests",
              "sidecar manifest disagrees" in freeze_src)
        check("R2/P0-B2: a rehearsal artifact cannot pass as production",
              "REHEARSAL" in freeze_src and "require_production" in freeze_src)

        # P0-B3 — decisions are machine-enforced
        dec_failures = decisions.check_release_decisions()
        check("R2/P0-B3: every recorded release decision holds", not dec_failures,
              "; ".join(dec_failures))
        for d_ in decisions.RELEASE_DECISIONS:
            check(f"R2/P0-B3: {d_.id} enforced in code",
                  not any(f.startswith(d_.id + ":") for f in dec_failures), d_.statement[:60])
        check("R2/P0-B3: freeze runs the decision preflight",
              "check_release_decisions" in freeze_src)
        check("R2/P0-B3: stage 11 runs it too",
              "check_release_decisions" in executable["scripts/11_freeze.py"])

        # P0-B4 — two digests
        check("R2/P0-B4: the runtime digest is distinct from the model digest",
              serving.runtime_contract_digest() != config.frozen_config_digest())
        check("R2/P0-B4: the manifest carries both",
              "runtime_contract_digest=serving.runtime_contract_digest()" in freeze_src)
        check("R2/P0-B4: stage 12 validates both",
              "runtime digest" in executable["scripts/12_predict_holdout.py"])
        check("R2/P0-B4: the source-tree digest exists too",
              len(freeze.source_tree_digest()) == 64)

        # P1-G1 — corrected holdout provenance
        check("R2/P1-G1: D14 is in the decision log", "D14" in docs["DECISION_LOG.md"])
        check("R2/P1-G1: the corrected history is recorded, not rewritten",
              holdout_manifest.PROVENANCE["predictor_only_file_read_before_freeze"] is True)
        check("R2/P1-G1: exactly one stage may read the holdout contents",
              holdout_manifest.CONTENT_READERS == ("scripts/12_predict_holdout.py",))
        leaks = []
        for n_, src_ in executable.items():
            if n_ in holdout_manifest.CONTENT_READERS or n_ == "moduleb/dataio.py" \
                    or n_ == "moduleb/holdout_manifest.py":
                continue
            if ("load_split(" + chr(34) + "holdout" + chr(34) + ")") in src_:
                leaks.append(n_)
        check("R2/P1-G1: no pre-freeze stage loads the holdout", not leaks, ", ".join(leaks))
        check("R2/P1-G1: the spend state is not asserted in the historical record",
              "one_shot_predictive_evaluation" not in holdout_manifest.PROVENANCE)

        # release manifest, when it has been built
        rm_path = ROOT / "RELEASE_MANIFEST.json"
        if rm_path.exists():
            rm = json.loads(rm_path.read_text())
            check("R2: the release manifest names this release candidate",
                  rm["release_candidate"] == moduleb.RELEASE_CANDIDATE, rm["release_candidate"])
            check("R2: the release manifest's model digest is current",
                  rm["digests"]["model_config"] == config.frozen_config_digest())
            check("R2: the release manifest's runtime digest is current",
                  rm["digests"]["runtime_contract"] == serving.runtime_contract_digest())
            check("R2: the release manifest's source digest is current",
                  rm["digests"]["source_tree"] == freeze.source_tree_digest())
            check("R2: the release manifest's sign-off state matches the release state",
                  (rm["team_signoff"]["state"] == "RECORDED") if out.exists()
                  else (rm["team_signoff"]["state"] == "PENDING"),
                  rm["team_signoff"]["state"])
            check("R2: the release manifest's holdout state matches disk",
                  rm["holdout"]["prediction_state"] == holdout_manifest.one_shot_state(),
                  rm["holdout"]["prediction_state"])
            check("R2: the release manifest carries the known limitations",
                  len(rm["known_limitations"]) == len(decisions.KNOWN_LIMITATIONS))

        # owner handoff — no unresolved marker in a current-release document
        unresolved = []
        for n_, t_ in docs.items():
            for marker in ("TODO", "TBD", "FIXME", "must choose", "DECIDE:"):
                for m_ in re.finditer(re.escape(marker), t_):
                    window = t_[max(0, m_.start() - 300): m_.end() + 300].lower()
                    if not any(k in window for k in MARKERS + ("future_release_items",
                                                               "future release")):
                        unresolved.append(f"{n_}:{marker}@{m_.start()}")
        check("R2: no unresolved decision marker in a current-release document",
              not unresolved, ", ".join(unresolved[:6]))
        check("R2: future work is parked in FUTURE_RELEASE_ITEMS.md",
              (ROOT / "docs" / "FUTURE_RELEASE_ITEMS.md").exists())

        # ---------------------------------------------------------- release state
        # State-aware since 20 Sep 2026. Before the freeze these asserted "no artifact,
        # no prediction"; after a legitimate freeze and one-shot run, a checker pinned
        # to the pre-freeze state fails on a package doing exactly what it should. What
        # must hold in both states is CONSISTENCY between disk, the documents and the
        # receipts — which is a stronger check than either fixed state.
        spent = out.exists()
        check("the recorded one-shot state matches disk",
              holdout_manifest.one_shot_state() == ("SPENT" if spent else "UNSPENT"),
              holdout_manifest.one_shot_state())
        if not spent:
            check("no frozen artifact exists yet", not model.exists())
            check("README states the model is not frozen", "not frozen" in readme)
        else:
            receipt_p = ROOT / "results" / "HOLDOUT_PREDICTION_RECEIPT.json"
            freeze_p = ROOT / "models" / "FREEZE_RECEIPT.json"
            # The frozen artifact does NOT travel with the release — it stays with the
            # owner and reaches everyone else as a hash inside the receipts. So the
            # invariant a distributed copy must satisfy is about the receipt, not about
            # a local .joblib.
            check("the prediction receipt travels with the prediction", receipt_p.exists())
            if receipt_p.exists():
                rec = json.loads(receipt_p.read_text())
                frz = json.loads(freeze_p.read_text()) if freeze_p.exists() else None
                import hashlib as _h
                check("the receipt's output hash matches the prediction file",
                      rec["prediction_output_sha256"]
                      == _h.sha256(out.read_bytes()).hexdigest())
                check("the receipt's holdout input hash is the attested delivery",
                      rec["holdout_input_sha256"] == holdout_manifest.SHA256)
                check("the receipt's model digest is the current one",
                      rec["model_config_digest"] == config.frozen_config_digest())
                check("the receipt's runtime digest is the current one",
                      rec["runtime_contract_digest"] == serving.runtime_contract_digest())
                check("the prediction receipt names a signed frozen artifact",
                      bool(rec["frozen_artifact_sha256"]) and bool(rec["team_signoff"]))
                if frz is not None:
                    check("the two receipts name the same artifact",
                          rec["frozen_artifact_sha256"] == frz["artifact_sha256"])
                    check("the two receipts carry the same sign-off",
                          rec["team_signoff"] == frz["team_signoff"])
                st = rec["statement"].lower()
                check("the receipt states no target or scoring information was used",
                      "no scoring information" in st and "target" in st
                      and "0 h and 24 h" in rec["statement"])
                check("the prediction has one row per declared holdout component",
                      rec["n_rows"] == holdout_manifest.N_ROWS
                      and rec["n_lots"] == holdout_manifest.N_LOTS,
                      f"{rec['n_rows']} rows / {rec['n_lots']} lots")
                pred_hdr = pd.read_csv(out, nrows=0).columns.tolist()
                ref_cols = dataio.expected_contract_columns()
                check("the prediction's contract columns are first and in order",
                      pred_hdr[:len(ref_cols)] == ref_cols)
                check("the prediction emits no disposition column",
                      not any(c in pred_hdr for c in
                              ("module_b_disposition", "module_b_pass", "module_b_verdict")))
                check("the prediction leaks no 96h or 168h input column",
                      not [c for c in pred_hdr if "96h" in c]
                      and not [c for c in pred_hdr if c.endswith("_168h")
                               and not c.startswith(("predicted_", "module_b_p"))])
            check("README no longer says the model is not frozen",
                  "not frozen" not in readme.lower())
            check("README states the one-shot is spent",
                  "spent" in readme.lower())

        # ---------------------------------------------------------- the guide
        # docs/COMPLETE_GUIDE.md restates most of the project's numbers in prose.
        # It is read-only against results/ — these checks make sure it did not drift.
        guide_path = ROOT / "docs" / "COMPLETE_GUIDE.md"
        if guide_path.exists():
            guide = guide_path.read_text()
            g = lambda t: t in guide   # noqa: E731

            # split shape
            check("guide: 3,151 / 906 / 1,343 rows", g("3,151") and g("906") and g("1,343"))
            check("guide: 42 / 12 / 18 lots", g("| 3,151 | 42 |") and g("| 906 | 12 |")
                  and g("| 1,343 | 18 |"))
            check("guide: the three SHA-256 prefixes",
                  all(g(s.sha256[:16]) for s in splits.values())
                  and g(holdout_manifest.SHA256[:16]))

            # train CV pooled MAE, to 5 dp, straight out of 03_cv_metrics.csv
            for p_ in PARAMS:
                check(f"guide: pooled MAE {p_}", g(f"{pooled[p_]:.5f}"),
                      f"{pooled[p_]:.5f}")

            # paired test
            for p_ in PARAMS:
                check(f"guide: macro-lot MAE {p_}", g(f"{pt.loc[p_, 'MacroLotMAE_module_b']:.5f}"),
                      f"{pt.loc[p_, 'MacroLotMAE_module_b']:.5f}")
                check(f"guide: lots won {p_}",
                      g(f"{int(pt.loc[p_, 'lots_won'])} / 42"),
                      f"{int(pt.loc[p_, 'lots_won'])}/42")

            # calibration
            calm = pd.read_csv(R / "05_calibration_metrics.csv")
            cal_pooled = (calm[(calm.variant == "ALL") & (calm.model == "MODULE_B")]
                          .set_index("param").MAE)
            for p_ in PARAMS:
                check(f"guide: calibration MAE {p_}", g(f"{cal_pooled[p_]:.5f}"),
                      f"{cal_pooled[p_]:.5f}")

            # grid
            for _, r in bf.iterrows():
                check(f"guide: grid gap {r.param}", g(f"{r.best_minus_frozen_pct:.2f} %"),
                      f"{r.best_minus_frozen_pct:.2f}%")

            # envelope at the operating point
            for p_ in PARAMS:
                check(f"guide: marginal coverage {p_}", g(f"{op.loc[p_, 'marginal_coverage']:.4f}"))
                check(f"guide: tail coverage {p_}", g(f"{op.loc[p_, 'tail_coverage']:.4f}"))

            # reason codes
            for code in ("B_WIDE_ENVELOPE", "B_HIGH_FORECAST_DRIFT", "B_LOT_OUTLIER_24H",
                         "B_NO_EARLY_SIGNAL", "B_FORECAST_EXCEEDS_LIMIT",
                         "B_ENVELOPE_REACHES_LIMIT"):
                r_ = float(cal.loc[code, "rate"])
                check(f"guide: rate {code}", g(f"{100 * r_:.2f} %"), f"{100 * r_:.2f}%")
            check("guide: any-code rate", g(f"{100 * any_rate:.2f} %"))

            # the open decision
            check("guide: C03478 named", g("C03478") and g("B_L23"))
            check("guide: 27.7% error share", g("27.7"))
            check("guide: 195.30% predicted drift", g("+195.30 %") or g("195.30"))
            check("guide: 53.9x max/p99", g("53.9"))
            check("guide: cap is off", g("`None`") and g("FORECAST_REL_DELTA_CAP"))

            # fall-time rule
            check("guide: fall-time -1.525%", g("1.525") or g("−1.525"))
            check("guide: fall-time 2 of 12", g("2 of 12"))

            # drift structure ranges
            lv = pd.read_csv(R / "02_lot_variance_share.csv")
            check("guide: lot-share range",
                  g(f"{lv.lot_var_share_pct.min():.2f}") and g(f"{lv.lot_var_share_pct.max():.2f}"))
            sn = pd.read_csv(R / "02_early_snr.csv")
            check("guide: SNR range", g(f"{sn.snr.min():.2f}") and g(f"{sn.snr.max():.2f}"))
            dk = pd.read_csv(R / "02_drift_exponent.csv")
            check("guide: drift exponent range",
                  g(f"{dk.implied_exponent_k.min():.3f}") and g(f"{dk.implied_exponent_k.max():.3f}"))

            # structural statements the guide must contain
            # Targeted, not blunt: the guide legitimately says "the reason-code
            # reference distributions were not frozen from training", which is about
            # something else entirely. What must not survive is the bare claim that the
            # MODEL is not frozen.
            check("guide: describes the freeze state that is actually on disk",
                  (g("FROZEN 20 Sep 2026") and "**NOT frozen**" not in guide)
                  if out.exists() else g("**NOT frozen**"))
            check("guide: describes the one-shot correctly", g("one-shot"))
            check("guide: excludes the mock datasets", g("excluded entirely"))
            check("guide: never calls the envelope a guarantee",
                  "safety guarantee" not in guide.replace("Never \"95 % safety guarantee\"", ""))
            check("guide: no module_b_disposition emitted", g("no `module_b_disposition`"))
        else:
            check("docs/COMPLETE_GUIDE.md exists", False, "not found")

        # ---------------------------------------------------------- report
        header("results")
        width = max(len(n) for n, _, _ in CHECKS)
        for name, ok, detail in CHECKS:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name:<{width}}  {detail}")
        n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
        print(f"\n  {len(CHECKS) - n_fail} passed, {n_fail} failed, "
              f"{len(CHECKS)} checks")
        if n_fail:
            raise SystemExit("documented claims disagree with results/ — fix the docs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
