"""
moduleb.predict — inference, and the two clip guards that sit in front of it.

This is the function Anushka's backend calls. It takes a frame of components
carrying context plus the six parameters at 0h and 24h, and returns the contract
frame. It never requires a 168h column, and it refuses to run if one is present
(`allow_target` exists solely so the calibration re-score can reuse this path).

Two guards clip rather than raise, and both print what they did:

* non-positive point forecast -> replaced by the 24h reading. All six parameters
  are magnitudes; a negative forecast is meaningless, and falling back to "no
  drift" is the conservative answer. If this fires on more than a handful of
  rows, the model is wrong and the count in the log is the evidence.
* envelope below the point forecast -> raised to it. An upper bound beneath its
  own central estimate is incoherent; clipping keeps the contract honest.

Neither guard is allowed to be silent, because a quiet repair is how a real
problem reaches the fusion layer wearing a clean face.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config, contract, envelope as envmod, guards, models, serving
from .constants import PARAMS
from .features import add_features


@dataclass
class PredictReport:
    n_rows: int
    n_lots: int = 0
    partial_lot_override: bool = False
    completeness: dict | None = None
    serving_contract_version: str = serving.SERVING_CONTRACT_VERSION
    runtime_contract_digest: str = ""
    nonpositive_clipped: dict[str, int] = field(default_factory=dict)
    envelope_clipped: dict[str, int] = field(default_factory=dict)
    rel_delta_capped: dict[str, int] = field(default_factory=dict)

    @property
    def clean(self) -> bool:
        complete = (self.completeness or {}).get("complete", True)
        return (not self.partial_lot_override
                and bool(complete)
                and not any(self.nonpositive_clipped.values())
                and not any(self.envelope_clipped.values())
                and not any(self.rel_delta_capped.values()))

    def as_dict(self) -> dict:
        """Everything a run receipt needs from the prediction side."""
        return dict(n_rows=self.n_rows, n_lots=self.n_lots,
                    partial_lot_override=self.partial_lot_override,
                    completeness=self.completeness,
                    serving_contract_version=self.serving_contract_version,
                    runtime_contract_digest=self.runtime_contract_digest,
                    nonpositive_clipped=dict(self.nonpositive_clipped),
                    envelope_clipped=dict(self.envelope_clipped),
                    rel_delta_capped=dict(self.rel_delta_capped),
                    clean=self.clean)

    def lines(self) -> list[str]:
        out = [f"rows predicted: {self.n_rows} across {self.n_lots} lot(s)"]
        c = self.completeness or {}
        if c:
            out.append(f"  lot completeness proved by: {c.get('proof')} "
                       f"(serving contract {self.serving_contract_version})")
        if self.partial_lot_override:
            out.append("  WARNING partial-lot override in use: the timing forecasts and "
                       "every evidence column were computed against this partial cohort "
                       "and are NOT comparable to full-lot output")
            if c.get("offending_lots"):
                for lot in c["offending_lots"]:
                    exp = (c.get("expected") or {}).get(lot)
                    out.append(f"    override lot {lot}: {c['observed'].get(lot)} rows "
                               f"delivered, expected {exp if exp is not None else 'undeclared'}")
        for p, n in self.nonpositive_clipped.items():
            if n:
                out.append(f"  WARNING {p}: {n} non-positive forecasts replaced by the 24h value")
        for p, n in self.rel_delta_capped.items():
            if n:
                out.append(f"  WARNING {p}: {n} forecasts hit the relative-delta cap "
                           f"({config.FORECAST_REL_DELTA_CAP:+.3f}); the model was extrapolating")
        for p, n in self.envelope_clipped.items():
            if n:
                out.append(f"  WARNING {p}: {n} envelope values raised to the point forecast")
        if self.clean:
            out.append("  no clipping required")
        return out


def predict_frame(artifact: dict, raw: pd.DataFrame, *, allow_target: bool = False,
                  expected_lot_sizes=None,
                  delivery: "serving.DeliveryAttestation | None" = None,
                  file_sha256: str | None = None,
                  allow_partial_lot: bool = False,
                  name: str = "input") -> tuple[pd.DataFrame, PredictReport]:
    """Run the frozen artifact over `raw` and return (contract frame, report).

    `raw` is a COHORT of COMPLETE lots. The timing models read own-lot medians
    and the evidence layer ranks each component against the others in the
    request, so a lot delivered with components missing answers a different
    question (review finding F1). Completeness is proved rather than assumed —
    pass either:

        expected_lot_sizes={lot_id: n, ...}   request metadata / lot traveller
        delivery=serving.DeliveryAttestation(...)  the custodian's file manifest

    and see moduleb.serving for what each one proves. Neither is refused.
    `allow_partial_lot=True` proceeds anyway, records which lots were short and
    by how much, and makes the report non-clean.
    """
    guards.assert_input_clean(raw, allow_target=allow_target, name=name)
    guards.assert_data_quality(raw, name=name, expect_targets=allow_target)
    comp = serving.assert_delivery_complete(
        raw, expected_lot_sizes=expected_lot_sizes, attestation=delivery,
        file_sha256=file_sha256, allow_partial_lot=allow_partial_lot,
        min_rows=config.MIN_LOT_COHORT, name=name)

    feat = add_features(raw, artifact["base"])
    rep = PredictReport(n_rows=len(feat), n_lots=int(raw.lot_id.nunique()),
                        partial_lot_override=bool(comp.override),
                        completeness=comp.as_dict(),
                        runtime_contract_digest=serving.runtime_contract_digest())

    preds = {p: models.predict_one(artifact["models"][p], feat, p) for p in PARAMS}
    for p in PARAMS:
        v = np.asarray(preds[p], float)
        if not np.isfinite(v).all():
            raise guards.DataQualityError(
                f"{p}: {int((~np.isfinite(v)).sum())} non-finite forecasts; refusing to write a file")
        # extrapolation guard, OFF unless the team turns it on (see stage 7)
        cap = config.FORECAST_REL_DELTA_CAP
        rep.rel_delta_capped[p] = 0
        if cap is not None:
            x24 = feat[f"{p}_24h"].to_numpy(float)
            rel = (v - x24) / x24
            over = np.abs(rel) > cap
            rep.rel_delta_capped[p] = int(over.sum())
            if over.any():
                v = x24 * (1.0 + np.clip(rel, -cap, cap))
        neg = v <= 0
        rep.nonpositive_clipped[p] = int(neg.sum())
        preds[p] = np.where(neg, feat[f"{p}_24h"].to_numpy(float), v)

    env = None
    if artifact.get("envelopes"):
        env = {p: envmod.predict_envelope(artifact["envelopes"][p], feat, p) for p in PARAMS}
        for p in PARAMS:
            bad = env[p] < preds[p]
            rep.envelope_clipped[p] = int(bad.sum())
            if bad.any():
                env[p] = np.maximum(env[p], preds[p])

    out = contract.build_output(feat, preds, artifact["limits"], env)
    return out, rep


def predict_csv(artifact: dict, in_path, out_path, *, allow_target: bool = False,
                expected_lot_sizes=None,
                delivery: "serving.DeliveryAttestation | None" = None,
                allow_partial_lot: bool = False):
    """File front end for `predict_frame`, with the same completeness contract.

    When a delivery attestation is supplied the file is hashed and checked
    against it, so a truncated or re-issued CSV is refused rather than scored.
    """
    from .dataio import file_sha256 as _sha
    raw = pd.read_csv(in_path)
    out, rep = predict_frame(artifact, raw, allow_target=allow_target,
                             expected_lot_sizes=expected_lot_sizes,
                             delivery=delivery,
                             file_sha256=_sha(in_path) if delivery is not None else None,
                             allow_partial_lot=allow_partial_lot, name=str(in_path))
    out.to_csv(out_path, index=False)
    return out, rep
