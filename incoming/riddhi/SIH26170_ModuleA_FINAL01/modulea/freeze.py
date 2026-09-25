"""Freezing, and the preflight that can refuse it.

A freeze is the moment a configuration stops being a proposal. It is gated on a
recorded human sign-off, the sign-off is embedded in the artifact before the bytes
are written, and every release decision is re-checked mechanically at that moment
rather than taken on trust from a document.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib

from modulea import config
from modulea.scoring import check_weights


class FreezeRefused(RuntimeError):
    """A precondition of freezing failed. Fix the condition, never the check."""


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def preflight(model, signoff: str, input_hashes: dict) -> list[str]:
    """Every condition re-checked at freeze time. Returns the passing check names."""
    checks = []

    if not signoff or len(signoff.strip()) < 20:
        raise FreezeRefused("a freeze needs a recorded human sign-off, not a placeholder")
    checks.append("signoff_present")

    check_weights(model.weights)
    checks.append("weights_valid")

    if not 0.0 < model.operating_threshold < 1.0:
        raise FreezeRefused("operating threshold out of range")
    checks.append("operating_threshold_in_range")

    if set(model.early_thresholds) != {0, 24, 96}:
        raise FreezeRefused(
            f"early thresholds must cover 0, 24 and 96 h, got {sorted(model.early_thresholds)}")
    checks.append("early_thresholds_complete")

    # D1 — Module A never emits a final disposition.
    if config.RUNTIME_CONTRACT.emits_reject:
        raise FreezeRefused("D1 violated: Module A must not emit REJECT")
    checks.append("D1_no_final_disposition")

    # D4 — no static limit is ever invented.
    if config.RUNTIME_CONTRACT.invents_static_limits:
        raise FreezeRefused("D4 violated: static limits must never be invented")
    checks.append("D4_no_invented_limits")

    # D5 — same-lot statistics require proved-complete lots.
    if not config.RUNTIME_CONTRACT.requires_complete_lots:
        raise FreezeRefused("D5 violated: same-lot statistics need complete lots")
    checks.append("D5_complete_lots_required")

    if not model.expected_lot_sizes:
        raise FreezeRefused("no external lot manifest embedded; completeness could not "
                            "be proved at serving time")
    checks.append("lot_manifest_embedded")

    if set(input_hashes) < {"train", "calibration"}:
        raise FreezeRefused("input hashes for train and calibration must be recorded")
    checks.append("input_hashes_recorded")

    if config.config_digest() != config.config_digest():   # pragma: no cover
        raise FreezeRefused("config digest is not stable")
    checks.append("config_digest_stable")

    return checks


def freeze(model, path: str | Path, signoff: str, input_hashes: dict,
           notes: dict | None = None) -> dict:
    checks = preflight(model, signoff, input_hashes)
    payload = {
        "model_version": config.MODEL_VERSION,
        "release_candidate": config.RELEASE_CANDIDATE,
        "dataset_id": config.DATASET_ID,
        "config": config.config_payload(),
        "config_digest": config.config_digest(),
        "runtime_contract": config.RUNTIME_CONTRACT.__dict__,
        "runtime_contract_digest": config.runtime_contract_digest(),
        "team_signoff": signoff,
        "input_hashes": input_hashes,
        "preflight_checks_passed": checks,
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model,
        "notes": notes or {},
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, path)
    receipt = {k: v for k, v in payload.items() if k != "model"}
    receipt["artifact_filename"] = path.name
    receipt["artifact_sha256"] = sha256_file(path)
    return receipt


def load(path: str | Path):
    payload = joblib.load(path)
    if payload["config_digest"] != config.config_digest():
        raise FreezeRefused(
            f"artifact was frozen under config digest {payload['config_digest'][:16]} "
            f"but the code now computes {config.config_digest()[:16]}. The artifact and "
            "the code are not the same release.")
    return payload["model"], payload
