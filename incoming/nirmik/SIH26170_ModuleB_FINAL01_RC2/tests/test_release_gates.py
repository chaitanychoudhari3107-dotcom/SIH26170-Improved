"""Release gates: sign-off, decisions, digests, and holdout isolation.

P0-B2, P0-B3, P0-B4 and P1-G1. These are the checks that stop an artifact
nobody approved, a decision that quietly stopped holding, a runtime change that
hid behind an unchanged model digest, and a pre-freeze stage reaching into the
blind file.

The freezes here fit on the synthetic fixture with `fit_envelopes=False` and
land in tmp_path. Nothing in this module writes to models/.
"""
import hashlib
import json
import re
from pathlib import Path

import joblib
import pytest

from moduleb import config, dataio, decisions, freeze, guards, holdout_manifest, serving

ROOT = Path(__file__).resolve().parent.parent


def _split(synth, tmp_path):
    p = tmp_path / "train.csv"
    synth.to_csv(p, index=False)
    return dataio.Split(name="train", path=p, frame=synth.reset_index(drop=True),
                        sha256=dataio.file_sha256(p), has_targets=True)


def _freeze(synth, specs, tmp_path, **kw):
    base, limits = specs
    kw.setdefault("team_signoff", "TEST — unit test sign-off")
    kw.setdefault("release_state", freeze.PRODUCTION)
    return freeze.freeze(_split(synth, tmp_path), None, base, limits,
                         tmp_path / "m.joblib", fit_envelopes=False, **kw)


# ------------------------------------------------------- P0-B2 embedded sign-off
def test_the_manifest_is_complete_before_the_artifact_is_serialised(synth, specs, tmp_path):
    man = _freeze(synth, specs, tmp_path)
    raw = joblib.load(tmp_path / "m.joblib")           # deliberately NOT load_frozen
    embedded = raw["manifest"]
    assert embedded["team_signoff"] == "TEST — unit test sign-off"
    assert embedded["release_state"] == freeze.PRODUCTION
    assert embedded["runtime_contract_digest"] == serving.runtime_contract_digest()
    assert embedded["source_tree_digest"] == freeze.source_tree_digest()
    assert embedded["manifest_digest"] == freeze.manifest_digest(embedded)
    assert embedded == man


def test_sidecar_and_embedded_manifests_agree(synth, specs, tmp_path):
    _freeze(synth, specs, tmp_path)
    side = json.loads((tmp_path / "m.manifest.json").read_text())
    embedded = joblib.load(tmp_path / "m.joblib")["manifest"]
    assert side == embedded
    freeze.load_frozen(tmp_path / "m.joblib")          # does not raise


def test_a_freeze_without_signoff_is_refused(synth, specs, tmp_path):
    with pytest.raises(guards.LeakageError, match="sign-off"):
        _freeze(synth, specs, tmp_path, team_signoff="")
    with pytest.raises(guards.LeakageError, match="sign-off"):
        _freeze(synth, specs, tmp_path, team_signoff="   ")
    assert not (tmp_path / "m.joblib").exists(), "an unsigned artifact was written"


def test_an_unsigned_artifact_is_refused_at_load(synth, specs, tmp_path):
    _freeze(synth, specs, tmp_path)
    art = joblib.load(tmp_path / "m.joblib")
    art["manifest"].pop("team_signoff")
    art["manifest"].pop("manifest_digest")
    joblib.dump(art, tmp_path / "m.joblib")
    (tmp_path / "m.manifest.json").write_text(json.dumps(art["manifest"], indent=2))
    with pytest.raises(guards.LeakageError, match="no team sign-off"):
        freeze.load_frozen(tmp_path / "m.joblib")


def test_a_rehearsal_artifact_is_refused_for_production(synth, specs, tmp_path):
    _freeze(synth, specs, tmp_path, team_signoff=freeze.REHEARSAL_SIGNOFF,
            release_state=freeze.REHEARSAL)
    freeze.load_frozen(tmp_path / "m.joblib", require_production=False)
    with pytest.raises(guards.LeakageError, match="REHEARSAL"):
        freeze.load_frozen(tmp_path / "m.joblib", require_production=True)


def test_the_rehearsal_placeholder_cannot_sign_a_production_freeze(synth, specs, tmp_path):
    with pytest.raises(guards.LeakageError, match="not a production sign-off"):
        _freeze(synth, specs, tmp_path, team_signoff=freeze.REHEARSAL_SIGNOFF,
                release_state=freeze.PRODUCTION)


def test_an_edited_sidecar_is_rejected(synth, specs, tmp_path):
    _freeze(synth, specs, tmp_path)
    side = json.loads((tmp_path / "m.manifest.json").read_text())
    side["team_signoff"] = "someone else entirely"
    (tmp_path / "m.manifest.json").write_text(json.dumps(side, indent=2))
    with pytest.raises(guards.LeakageError, match="sidecar manifest disagrees"):
        freeze.load_frozen(tmp_path / "m.joblib")


def test_an_edited_embedded_manifest_fails_its_own_digest(synth, specs, tmp_path):
    _freeze(synth, specs, tmp_path)
    art = joblib.load(tmp_path / "m.joblib")
    art["manifest"]["team_signoff"] = "forged"
    joblib.dump(art, tmp_path / "m.joblib")
    with pytest.raises(guards.LeakageError, match="does not match its own digest"):
        freeze.load_frozen(tmp_path / "m.joblib")


def test_a_missing_sidecar_is_rejected(synth, specs, tmp_path):
    _freeze(synth, specs, tmp_path)
    (tmp_path / "m.manifest.json").unlink()
    with pytest.raises(guards.LeakageError, match="sidecar manifest .* is missing"):
        freeze.load_frozen(tmp_path / "m.joblib")


# ------------------------------------------------------- P0-B3 decisions
def test_every_recorded_release_decision_holds():
    assert decisions.check_release_decisions() == []
    ids = [d.id for d in decisions.RELEASE_DECISIONS]
    assert {"D1", "D10", "D11", "D12", "D13", "D14"} <= set(ids)


def test_a_non_none_cap_fails_the_freeze_preflight(synth, specs, tmp_path, monkeypatch):
    """The D11 negative test. Turning the cap on must stop the freeze, not
    produce a differently-digested artifact nobody noticed."""
    monkeypatch.setattr(config, "FORECAST_REL_DELTA_CAP", 0.5)
    failures = decisions.check_release_decisions()
    assert any(f.startswith("D11:") for f in failures)
    with pytest.raises(guards.LeakageError, match="freeze preflight failed"):
        _freeze(synth, specs, tmp_path)
    assert not (tmp_path / "m.joblib").exists()


def test_a_disposition_in_the_contract_fails_the_preflight(monkeypatch):
    from moduleb import constants
    monkeypatch.setattr(constants, "FORBIDDEN_OUTPUT_COLS", [])
    assert any(f.startswith("D1:") for f in decisions.check_release_decisions())


def test_moving_the_fall_time_feature_set_fails_the_preflight(monkeypatch):
    rec = {k: dict(v) for k, v in config.RECOMMENDED.items()}
    rec["Output_Fall_Time"]["features"] = "own"
    monkeypatch.setattr(config, "RECOMMENDED", rec)
    assert any(f.startswith("D10:") for f in decisions.check_release_decisions())


# ------------------------------------------------------- P0-B4 runtime digest
def test_a_runtime_change_moves_only_the_runtime_digest(monkeypatch):
    model_before = config.frozen_config_digest()
    runtime_before = serving.runtime_contract_digest()
    monkeypatch.setattr(config, "MIN_LOT_COHORT", 31)
    assert config.frozen_config_digest() == model_before, \
        "a serving change must not claim to be a different fitted model"
    assert serving.runtime_contract_digest() != runtime_before, \
        "a serving change must be visible in the runtime digest"


def test_a_model_change_moves_only_the_model_digest(monkeypatch):
    model_before = config.frozen_config_digest()
    runtime_before = serving.runtime_contract_digest()
    monkeypatch.setattr(config, "HUBER", dict(epsilon=1.4, alpha=1e-3, max_iter=800))
    assert config.frozen_config_digest() != model_before
    assert serving.runtime_contract_digest() == runtime_before


def test_a_stale_runtime_contract_is_rejected_at_load(synth, specs, tmp_path, monkeypatch):
    _freeze(synth, specs, tmp_path)
    monkeypatch.setattr(config, "MIN_LOT_COHORT", 31)
    with pytest.raises(guards.LeakageError, match="runtime contract has changed"):
        freeze.load_frozen(tmp_path / "m.joblib")


def test_a_stale_model_config_is_rejected_at_load(synth, specs, tmp_path, monkeypatch):
    _freeze(synth, specs, tmp_path)
    monkeypatch.setattr(config, "GLOBAL_SEED", 1)
    with pytest.raises(guards.LeakageError, match="different moduleb.config"):
        freeze.load_frozen(tmp_path / "m.joblib")


def test_the_runtime_digest_covers_the_things_it_claims_to():
    payload = serving.runtime_contract_payload()
    for key in ("serving_contract_version", "requires_completeness_proof",
                "partial_lot_default", "min_lot_cohort", "input_contract",
                "output_contract", "reason_code_thresholds", "static_limit_policy",
                "clipping_semantics", "envelope_tau"):
        assert key in payload, key
    assert payload["emits_disposition"] is False


# ------------------------------------------------------- P1-G1 holdout isolation
# Built rather than written out, so this file does not itself contain the literal
# it is looking for — otherwise the scan finds its own source and every run fails.
FORBIDDEN_READS = tuple("load_split(" + q + "holdout" + q + ")" for q in ('"', "'"))


def test_no_pre_freeze_stage_reads_the_holdout_contents():
    """Only the gated stage may open the file. Everything else gets the declared
    structure from moduleb.holdout_manifest, and may hash the file for
    provenance — a SHA-256 reads bytes, not measurements."""
    allowed = set(holdout_manifest.CONTENT_READERS)
    offenders = []
    for path in sorted((ROOT / "scripts").glob("*.py")) + \
            sorted((ROOT / "notebooks").glob("*.ipynb")) + \
            sorted((ROOT / "moduleb").glob("*.py")):
        rel = f"{path.parent.name}/{path.name}"
        if rel in allowed or path.name in ("dataio.py", "holdout_manifest.py"):
            continue
        text = path.read_text()
        for pat in FORBIDDEN_READS:
            if pat in text:
                offenders.append(f"{rel}: {pat}")
        for m in re.finditer(r'PATHS\[.holdout.\]', text):
            window = text[max(0, m.start() - 80): m.end() + 40]
            if "file_sha256" not in window:
                offenders.append(f"{rel}@{m.start()}: holdout path used without hashing")
    assert not offenders, f"pre-freeze holdout access: {offenders}"


def test_the_corrected_holdout_provenance_is_a_fixed_historical_record():
    """It describes what happened BEFORE the freeze, so it must not move afterwards."""
    p = holdout_manifest.PROVENANCE
    assert "one_shot_predictive_evaluation" not in p, \
        "the spend state must not be asserted in the historical record"
    assert p["decision"] == "D14"
    assert p["predictor_only_file_read_before_freeze"] is True, \
        "the corrected history says the predictor-only file WAS read; do not rewrite it"
    assert p["hidden_168h_truth_available_to_module_b"] is False
    assert p["holdout_forecast_generated"] is False
    assert p["holdout_score_observed"] is False
    assert p["model_or_config_decision_used_holdout_outcome"] is False
    assert holdout_manifest.CONTENT_READERS == ("scripts/12_predict_holdout.py",)


def test_the_declared_holdout_header_carries_no_targets_and_no_96h():
    cols = holdout_manifest.COLUMNS
    assert len(cols) == holdout_manifest.N_COLUMNS
    assert not [c for c in cols if "96" in c]
    assert not [c for c in cols if "168" in c]


def test_the_declared_delivery_hash_matches_the_shipped_file():
    holdout_manifest.verify_delivery_hash(dataio.file_sha256(dataio.PATHS["holdout"]))
    with pytest.raises(ValueError, match="not the delivery recorded"):
        holdout_manifest.verify_delivery_hash("0" * 64)


def test_the_one_shot_state_is_consistent_with_what_is_on_disk():
    """State-aware, deliberately.

    Before the freeze this asserted "no artifact, no prediction". That was right
    until 20 Sep 2026, when the team signed off and stages 11 and 12 ran — after
    which a test pinned to the pre-freeze state fails on a package that is doing
    exactly what it was built to do, and Chaitany's re-verification instructions
    break. What must hold in BOTH states is consistency: a frozen artifact must be
    a genuinely signed production artifact, a prediction file must exist only
    alongside a frozen artifact and its receipt, and the recorded state must match
    the disk.
    """
    model = ROOT / "models" / "module_b_final01.joblib"
    pred = ROOT / "results" / "ModuleB_Final_Holdout_Predictions.csv"
    receipt = ROOT / "results" / "HOLDOUT_PREDICTION_RECEIPT.json"

    assert holdout_manifest.one_shot_state() == ("SPENT" if pred.exists() else "UNSPENT")

    if pred.exists():
        # The prediction's provenance is its RECEIPT, not the local presence of the
        # artifact: the frozen artifact deliberately does not travel with the release
        # (it stays with the owner) and reaches everyone else as a hash in the receipt.
        # A distributed copy must still be fully verifiable, so the invariant is stated
        # against the receipt.
        assert receipt.exists(), "a prediction exists without its provenance receipt"
        rec = json.loads(receipt.read_text())
        assert rec["model_config_digest"] == config.frozen_config_digest()
        assert rec["runtime_contract_digest"] == serving.runtime_contract_digest()
        assert rec["holdout_input_sha256"] == holdout_manifest.SHA256
        assert rec["n_rows"] == holdout_manifest.N_ROWS
        assert rec["n_lots"] == holdout_manifest.N_LOTS
        assert rec["team_signoff"] and rec["team_signoff"] != freeze.REHEARSAL_SIGNOFF
        assert hashlib.sha256(pred.read_bytes()).hexdigest() == rec["prediction_output_sha256"]
        if model.exists():                      # the owner's own tree
            man = freeze.load_frozen(model, require_production=True)["manifest"]
            assert man["team_signoff"] == rec["team_signoff"]
            assert dataio.file_sha256(model) == rec["frozen_artifact_sha256"]
    else:
        assert not model.exists(), "a frozen artifact exists but nothing was predicted"
        assert not receipt.exists()


def test_the_spent_one_shot_cannot_be_re_run_by_accident():
    """The one-shot is protected by the output file's existence, not by memory."""
    src = (ROOT / "scripts" / "12_predict_holdout.py").read_text()
    assert "already exists" in src and "--force" in src
    assert "one-shot" in src
