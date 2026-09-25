"""
Module B — 168h electrical-parameter forecasting from 0h + 24h.
SIH 26170 · dataset SIH26170-FINAL-01 · owner: Nirmik

Import order is deliberate and shallow: constants -> config -> guards ->
dataio/features -> featureset -> models/baselines -> metrics/cv -> envelope ->
reason_codes -> serving -> contract -> holdout_manifest -> decisions ->
freeze/predict. Nothing imports upward, so any module can be read on its own.
"""
from . import (  # noqa: F401
    baselines, config, constants, contract, cv, dataio, decisions, envelope,
    features, featureset, freeze, guards, holdout_manifest, metrics, models,
    predict, reason_codes, serving,
)

__all__ = [
    "baselines", "config", "constants", "contract", "cv", "dataio", "decisions",
    "envelope", "features", "featureset", "freeze", "guards", "holdout_manifest",
    "metrics", "models", "predict", "reason_codes", "serving",
]

# Release identity. The version moves when the package's behaviour moves, which
# includes runtime-contract changes that leave every fitted parameter alone.
__version__ = "final01.2.0"
RELEASE_CANDIDATE = "ModuleB-FINAL01-RC2"
