"""
moduleb.freeze — turn a configuration into an immutable artifact.

Freezing means two things here. The obvious one: fit the six models and six
envelopes on train + calibration and serialise them. The one that actually
matters: write down enough to prove later which code, which files and whose
approval produced them — the SHA-256 of every input CSV, the digest of the
FROZEN_V1 config block, the digest of the runtime contract, the digest of the
source tree, the library versions, the seed, the feature contract, and the team
sign-off itself.

Three rules this module enforces, each of them a fix for a way the old version
could have shipped something indefensible:

1. **The manifest is complete before the artifact is serialised.** Sign-off used
   to be written to a sidecar *after* `joblib.dump` had already run, so the
   pickled artifact carried a manifest with no approval in it and the only
   record of who signed lived in a file anyone could edit. Now the manifest —
   sign-off included — is built first, embedded, and the sidecar is written from
   the same dict. `load_frozen` compares the two and refuses a mismatch.

2. **Two digests, not one.** `frozen_config_digest()` covers the fitted model.
   `serving.runtime_contract_digest()` covers everything that changes what a
   caller gets without changing a fitted parameter — lot completeness, the
   partial-lot override, the output contract, the reason-code thresholds, the
   clipping semantics. A runtime change used to be invisible to a consumer
   holding the model digest. Now it is not.

3. **A rehearsal is never a production artifact.** Stage 10 freezes with a dummy
   sign-off into a temporary directory to prove the code path works. That
   artifact is stamped `release_state="REHEARSAL"` and `load_frozen` refuses it
   for anything that matters.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import config, dataio, decisions, envelope, guards, holdout_manifest, models, serving
from .constants import DATASET_ID, ID_COLS, PARAMS, PREDICTOR_COLS

PRODUCTION = "PRODUCTION"
REHEARSAL = "REHEARSAL"
REHEARSAL_SIGNOFF = "REHEARSAL — not a production sign-off"

_PKG = Path(__file__).resolve().parent


def source_tree_digest() -> str:
    """SHA-256 over every module in the package, by name and content.

    Covers the code that a manifest's other digests do not: a change to
    features.py alters no config number and no runtime constant, but it is still
    a different Module B.
    """
    h = hashlib.sha256()
    for p in sorted(_PKG.glob("*.py")):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def _digest_of(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                     default=str).encode()).hexdigest()


def manifest_digest(manifest: dict) -> str:
    """Digest of the manifest itself, minus any digest-of-itself field."""
    m = {k: v for k, v in manifest.items() if k != "manifest_digest"}
    return _digest_of(m)


def build_manifest(full: pd.DataFrame, sources: dict, specs_path, envelopes: dict,
                   *, team_signoff: str, release_state: str,
                   refreeze_reason: str | None = None) -> dict:
    """The complete manifest. Built BEFORE serialisation — see rule 1 above."""
    import sklearn
    import scipy

    if not team_signoff or not str(team_signoff).strip():
        raise guards.LeakageError(
            "a freeze manifest cannot be built without a team sign-off. Module B "
            "does not manufacture approval: obtain it, then pass it in.")
    if release_state not in (PRODUCTION, REHEARSAL):
        raise ValueError(f"release_state must be {PRODUCTION!r} or {REHEARSAL!r}")
    if release_state == PRODUCTION and str(team_signoff).strip() == REHEARSAL_SIGNOFF:
        raise guards.LeakageError(
            "the rehearsal placeholder is not a production sign-off.")

    man = dict(
        module="B",
        dataset=DATASET_ID,
        release_state=release_state,
        frozen_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        team_signoff=str(team_signoff),
        refreeze_reason=refreeze_reason or None,
        frozen_config_digest=config.frozen_config_digest(),
        runtime_contract_digest=serving.runtime_contract_digest(),
        source_tree_digest=source_tree_digest(),
        input_contract_digest=_digest_of(list(ID_COLS) + list(PREDICTOR_COLS)),
        output_contract_digest=_digest_of(
            serving.runtime_contract_payload()["output_contract"]),
        serving_contract=dict(
            version=serving.SERVING_CONTRACT_VERSION,
            requires_completeness_proof=serving.REQUIRES_COMPLETENESS_PROOF,
            partial_lot_default=serving.PARTIAL_LOT_DEFAULT,
            min_lot_cohort=config.MIN_LOT_COHORT,
        ),
        release_decisions=decisions.decision_state(),
        holdout_access_provenance=dict(holdout_manifest.PROVENANCE),
        holdout_prediction_state="UNSPENT",
        config={p: config.RECOMMENDED[p] for p in PARAMS},
        hyperparameters=dict(Huber=config.HUBER, Ridge=config.RIDGE, GBR=config.GBR),
        seed=config.GLOBAL_SEED,
        n_folds=config.N_FOLDS,
        target_parameterisation=("relative delta from 24h; "
                                 "prediction = x24 * (1 + f(features))"),
        n_train_rows=int(len(full)),
        n_train_lots=int(full.lot_id.nunique()),
        train_lots=sorted(full.lot_id.unique().tolist()),
        sources=sources,
        specs=dict(path=str(specs_path), sha256=dataio.file_sha256(specs_path)),
        feature_contract=("0h and 24h measurements, own-lot medians of those, "
                          "Device_Specs 0h baseline, device_variant one-hot. "
                          "No 96h. No 168h. No hidden labels."),
        envelope=dict(
            method="conformalised GBR quantile regression (CQR)",
            tau=config.ENVELOPE_TAU,
            conformal_lots=config.ENVELOPE_CONF_LOTS,
            offsets={p: round(float(envelopes[p].offset), 8) for p in PARAMS},
            conformal_lot_ids={p: envelopes[p].conformal_lots for p in PARAMS},
            caveat=("marginal coverage is calibrated; conditional coverage on the "
                    "worst-drifting decile is far below nominal. Evidence, not a screen."),
        ),
        emits_disposition=False,
        environment=dict(python=sys.version.split()[0], platform=platform.platform(),
                         numpy=np.__version__, pandas=pd.__version__,
                         scikit_learn=sklearn.__version__, scipy=scipy.__version__),
    )
    man["manifest_digest"] = manifest_digest(man)
    return man


def freeze(train_split, calibration_split, specs, limits, out_path: str | Path,
           *, team_signoff: str, release_state: str = PRODUCTION,
           refreeze_reason: str | None = None, fit_envelopes: bool = True) -> dict:
    """Fit on train (+ calibration when supplied) and write the joblib artifact.

    The freeze preflight runs first: a release decision that no longer holds
    stops the freeze here, not in a review three days later.
    """
    import joblib
    from .features import add_features

    failures = decisions.check_release_decisions()
    if failures:
        raise guards.LeakageError(
            "freeze preflight failed — a recorded release decision no longer holds:\n  "
            + "\n  ".join(failures)
            + "\nReconcile moduleb.config with docs/DECISION_LOG.md, or record a new "
              "decision, before freezing.")

    frames, sources = [], {}
    tr = add_features(train_split.frame, specs)
    frames.append(tr)
    sources["train"] = dict(path=str(train_split.path), sha256=train_split.sha256,
                            rows=int(len(tr)), lots=int(tr.lot_id.nunique()))

    if calibration_split is not None:
        guards.assert_lots_disjoint(train_split.frame, calibration_split.frame,
                                    name_a="train", name_b="calibration")
        ca = add_features(calibration_split.frame, specs)
        frames.append(ca)
        sources["calibration"] = dict(path=str(calibration_split.path),
                                      sha256=calibration_split.sha256,
                                      rows=int(len(ca)), lots=int(ca.lot_id.nunique()))

    full = pd.concat(frames, ignore_index=True)
    fitted = {p: models.fit_one(full, p, config.RECOMMENDED[p]) for p in PARAMS}
    envs = ({p: envelope.fit_envelope(full, p, config.RECOMMENDED[p]) for p in PARAMS}
            if fit_envelopes else {})
    for_manifest = envs or {
        p: envelope.EnvelopeModel(p, "", [], None, 0.0, config.ENVELOPE_TAU, 0, [])
        for p in PARAMS}

    # Rule 1: the manifest is finished here, before anything is serialised.
    manifest = build_manifest(full, sources, dataio.PATHS["specs"], for_manifest,
                              team_signoff=team_signoff, release_state=release_state,
                              refreeze_reason=refreeze_reason)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(dict(models=fitted, envelopes=envs, limits=limits, base=specs,
                     manifest=manifest), out_path)
    out_path.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def load_frozen(path: str | Path, *, require_production: bool = True,
                check_sidecar: bool = True) -> dict:
    """Load an artifact and refuse it unless everything still agrees.

    Refuses on: a different fitted config, a different runtime contract, a
    different dataset, a missing or placeholder sign-off, a manifest whose own
    digest does not verify, and a sidecar that disagrees with the embedded copy.
    """
    import joblib
    art = joblib.load(path)
    man = art.get("manifest", {})

    if man.get("frozen_config_digest") != config.frozen_config_digest():
        raise guards.LeakageError(
            "the frozen artifact was produced by a different moduleb.config than the one "
            "loaded now. Refusing to predict: re-freeze, or check out the matching code.\n"
            f"  artifact: {man.get('frozen_config_digest')}\n"
            f"  current : {config.frozen_config_digest()}")
    if man.get("runtime_contract_digest") != serving.runtime_contract_digest():
        raise guards.LeakageError(
            "the runtime contract has changed since this artifact was frozen. The fitted "
            "model may be identical, but what a caller gets is not — serving rules, the "
            "output contract or the evidence thresholds have moved.\n"
            f"  artifact: {man.get('runtime_contract_digest')}\n"
            f"  current : {serving.runtime_contract_digest()}")
    if man.get("dataset") != DATASET_ID:
        raise guards.LeakageError(
            f"artifact was frozen on {man.get('dataset')}, this code targets {DATASET_ID}")

    if man.get("manifest_digest") and manifest_digest(man) != man["manifest_digest"]:
        raise guards.LeakageError(
            "the embedded manifest does not match its own digest; it has been edited "
            "after the freeze.")

    signoff = str(man.get("team_signoff") or "").strip()
    if not signoff:
        raise guards.LeakageError(
            "the artifact carries no team sign-off. A frozen model without recorded "
            "approval cannot be used for the one-shot holdout run.")
    if require_production:
        if man.get("release_state") != PRODUCTION:
            raise guards.LeakageError(
                f"this artifact is stamped {man.get('release_state')!r}, not {PRODUCTION!r}. "
                "A rehearsal artifact is for exercising the code path, never for a run "
                "that anyone will act on.")
        if signoff == REHEARSAL_SIGNOFF:
            raise guards.LeakageError("the rehearsal placeholder is not a sign-off.")

    if check_sidecar:
        side = Path(path).with_suffix(".manifest.json")
        if not side.exists():
            raise guards.LeakageError(
                f"the sidecar manifest {side.name} is missing. The embedded and sidecar "
                "manifests are written together and are meant to be compared.")
        on_disk = json.loads(side.read_text())
        if on_disk != man:
            differing = sorted({k for k in set(on_disk) | set(man)
                                if on_disk.get(k) != man.get(k)})
            raise guards.LeakageError(
                "the sidecar manifest disagrees with the manifest embedded in the "
                f"artifact; fields: {differing}. One of them has been edited.")
    return art
