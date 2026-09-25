"""
moduleb.serving — the request contract, and the proof that a lot is complete.

The problem this module fixes
-----------------------------
`MIN_LOT_COHORT = 30` was a size floor, and a size floor is not a completeness
proof. A lot of 82 components delivered with 61 of them present passes any floor
below 61 and still produces a different answer from the same lot delivered
whole: the timing models read own-lot medians and every evidence column ranks a
component against the others in the request. The output would look perfectly
well formed on the way out. That is the failure mode worth refusing.

So completeness must be *proved*, not assumed, and the proof has to come from
outside the rows themselves — counting the rows you were sent tells you nothing
about the rows you were not sent. Two sources of proof are accepted:

  request metadata   the caller states how many components each lot should
                     carry (`expected_lot_sizes`). This is the production route:
                     the lot traveller, the MES record or the test-floor request
                     knows the lot size, and Module B checks against it.

  delivery attestation
                     the custodian's manifest entry for a whole file — its
                     SHA-256, row count and lot count. This is the route for the
                     shipped FINAL-01 splits, where the file *is* the delivery
                     and its hash is what proves nothing was dropped in transit.

If neither is supplied the request is refused. `MIN_LOT_COHORT` survives as a
secondary sanity floor applied on top of whichever proof was given, never as the
proof itself.

`allow_partial_lot=True` remains, and remains the only way past this: an
explicit, recorded, degraded override. It never becomes the default and it
always makes the run report non-clean.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Mapping

import pandas as pd

from . import config, guards
from .constants import GROUP_KEY, ID_COLS, PREDICTOR_COLS, contract_columns

# Bumped whenever a rule in this module changes meaning. It is part of the
# runtime contract digest, so a consumer can tell two releases apart even when
# the fitted model is byte-identical.
SERVING_CONTRACT_VERSION = "mb-serving-2.0"

# The release decision this module implements (D12). Stated as data so
# moduleb.decisions can machine-check that the code still does what the decision
# log says it does.
REQUIRES_COMPLETENESS_PROOF = True
PARTIAL_LOT_DEFAULT = False


class IncompleteLotError(guards.DataQualityError):
    """A lot in this request was not proved complete.

    A subclass of DataQualityError so existing handlers still catch it, and its
    own type so a caller can distinguish "you sent me half a lot" from "this
    file is broken".
    """


@dataclass(frozen=True)
class DeliveryAttestation:
    """Whole-file completeness evidence issued by the data custodian.

    `source` is free text naming who attested it, and it is carried into the
    prediction receipt so provenance survives the run.
    """
    source: str
    sha256: str
    n_rows: int
    n_lots: int

    def as_dict(self) -> dict:
        return dict(source=self.source, sha256=self.sha256,
                    n_rows=self.n_rows, n_lots=self.n_lots)


@dataclass
class CompletenessReport:
    """What was checked, and what it proved. Goes into the run receipt."""
    proof: str                                    # "request_metadata" | "delivery_attestation" | "override"
    serving_contract_version: str = SERVING_CONTRACT_VERSION
    complete: bool = True
    override: bool = False
    hash_verified: bool | None = None       # None: no attestation was supplied
    observed: dict[str, int] = field(default_factory=dict)
    expected: dict[str, int | None] = field(default_factory=dict)
    offending_lots: list[str] = field(default_factory=list)
    attestation: dict | None = None

    def as_dict(self) -> dict:
        return dict(proof=self.proof,
                    serving_contract_version=self.serving_contract_version,
                    complete=self.complete, override=self.override,
                    hash_verified=self.hash_verified,
                    observed=dict(self.observed), expected=dict(self.expected),
                    offending_lots=list(self.offending_lots),
                    attestation=self.attestation)


def _observed(df: pd.DataFrame) -> dict[str, int]:
    return {str(k): int(v) for k, v in df.groupby(GROUP_KEY).size().items()}


def assert_delivery_complete(
    df: pd.DataFrame, *,
    expected_lot_sizes: Mapping[str, int] | None = None,
    attestation: DeliveryAttestation | None = None,
    file_sha256: str | None = None,
    allow_partial_lot: bool = PARTIAL_LOT_DEFAULT,
    min_rows: int = config.MIN_LOT_COHORT,
    name: str = "input",
) -> CompletenessReport:
    """Prove every lot in `df` is complete, or raise.

    Returns the report on success. On `allow_partial_lot=True` it returns a
    report marked override/incomplete instead of raising, having recorded which
    lots failed and by how much.
    """
    observed = _observed(df)

    if expected_lot_sizes is not None:
        rep = CompletenessReport(proof="request_metadata", observed=observed)
        exp = {str(k): int(v) for k, v in expected_lot_sizes.items()}
        rep.expected = {lot: exp.get(lot) for lot in observed}
        undeclared = sorted(lot for lot in observed if lot not in exp)
        mismatched = sorted(lot for lot in observed
                            if lot in exp and observed[lot] != exp[lot])
        rep.offending_lots = undeclared + mismatched
        if rep.offending_lots:
            rep.complete = False
            detail = "; ".join(
                f"{lot}: {observed[lot]} of "
                f"{exp[lot] if lot in exp else 'no declared size'}"
                for lot in rep.offending_lots)
            _refuse_or_override(rep, allow_partial_lot, name, detail,
                                undeclared=bool(undeclared))
    elif attestation is not None:
        rep = CompletenessReport(proof="delivery_attestation", observed=observed,
                                 attestation=attestation.as_dict())
        rep.expected = {lot: None for lot in observed}
        # Recorded rather than assumed: a caller that hands predict_frame a frame it
        # built itself has no file to hash, and the receipt must say so instead of
        # implying the delivery hash was checked.
        rep.hash_verified = bool(file_sha256 is not None
                                 and file_sha256 == attestation.sha256)
        problems = []
        if file_sha256 is not None and file_sha256 != attestation.sha256:
            problems.append(f"sha256 {file_sha256[:16]} != attested "
                            f"{attestation.sha256[:16]}")
        if len(df) != attestation.n_rows:
            problems.append(f"{len(df)} rows != attested {attestation.n_rows}")
        if df[GROUP_KEY].nunique() != attestation.n_lots:
            problems.append(f"{df[GROUP_KEY].nunique()} lots != attested "
                            f"{attestation.n_lots}")
        if problems:
            rep.complete = False
            rep.offending_lots = sorted(observed)
            _refuse_or_override(rep, allow_partial_lot, name,
                                "; ".join(problems), undeclared=False)
    else:
        rep = CompletenessReport(proof="none", observed=observed, complete=False,
                                 expected={lot: None for lot in observed},
                                 offending_lots=sorted(observed))
        if not allow_partial_lot:
            raise IncompleteLotError(
                f"[{name}] Module B scores whole lots, not individual components, and "
                "it cannot prove these lots are complete. A row count is not a proof: "
                "a lot delivered with components missing "
                "answers a different question and says nothing about it on the way "
                "out. Supply one of:\n"
                "  expected_lot_sizes={'LOT_ID': n, ...}  — the size each lot should "
                "carry, from the request metadata or lot traveller; or\n"
                "  attestation=DeliveryAttestation(...)   — the custodian's manifest "
                "entry for the whole file (sha256, rows, lots).\n"
                "If a partial cohort is genuinely intended, pass allow_partial_lot=True "
                "and read the warning it produces.")
        rep.override = True

    # Secondary sanity floor — the original F1 cohort guard, still enforced and
    # still raising its own message. It is never the completeness proof: a lot can
    # clear 30 rows and still be missing half of itself, which is what the checks
    # above are for.
    small = sorted(lot for lot, n in observed.items() if n < min_rows)
    if small and not allow_partial_lot:
        guards.assert_cohort_sufficient(df, min_rows=min_rows, name=name)
    if small:
        rep.complete = False
        rep.offending_lots = sorted(set(rep.offending_lots) | set(small))

    if allow_partial_lot:
        # The override is recorded as what it is — a caller asking to proceed on an
        # unproved cohort — without overstating the facts: if nothing was actually
        # short, `complete` stays True and says so. The run is still non-clean,
        # because PredictReport.clean refuses any request served under the override.
        rep.override = True
        rep.proof = "override"
        rep.complete = not rep.offending_lots
    return rep


def _refuse_or_override(rep: CompletenessReport, allow_partial_lot: bool,
                        name: str, detail: str, *, undeclared: bool) -> None:
    if allow_partial_lot:
        rep.override = True
        return
    extra = ("\nA lot with no declared size cannot be proved complete; declare it "
             "or send the delivery attestation." if undeclared else "")
    raise IncompleteLotError(
        f"[{name}] incomplete delivery — {detail}.{extra}\n"
        "Module B refuses an incomplete lot by default, whatever its row count: the "
        "timing forecasts and every evidence column are computed against the "
        "components present in the request. Send the complete lot, or pass "
        "allow_partial_lot=True to accept a recorded, degraded answer.")


def file_attestation(path, *, source: str, n_rows: int, n_lots: int) -> DeliveryAttestation:
    """Attestation built from a file on disk; hashes it without reading values."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return DeliveryAttestation(source=source, sha256=h.hexdigest(),
                               n_rows=n_rows, n_lots=n_lots)


# ------------------------------------------------------------------ digest
def runtime_contract_payload() -> dict:
    """Every release-affecting behaviour that is NOT a fitted parameter.

    Kept separate from `config.frozen_config_digest()` on purpose (P0-B4): a
    change to the serving rules must not silently claim to be a different fitted
    model, and a change to the fitted model must not hide behind unchanged
    serving rules. Two digests, two questions.
    """
    tau_pct = int(round(config.ENVELOPE_TAU * 100))
    return dict(
        serving_contract_version=SERVING_CONTRACT_VERSION,
        requires_completeness_proof=REQUIRES_COMPLETENESS_PROOF,
        accepted_completeness_proofs=["request_metadata", "delivery_attestation"],
        partial_lot_default=PARTIAL_LOT_DEFAULT,
        partial_lot_override=("explicit allow_partial_lot=True; recorded in the "
                              "report with the offending lots and counts; "
                              "report.clean is False"),
        min_lot_cohort=config.MIN_LOT_COHORT,
        min_lot_cohort_role="secondary sanity floor, never a completeness proof",
        input_contract=list(ID_COLS) + list(PREDICTOR_COLS),
        output_contract=contract_columns(tau_pct),
        envelope_tau=config.ENVELOPE_TAU,
        reason_code_thresholds=dict(
            high_drift_z=config.FLAG_HIGH_DRIFT_Z,
            wide_envelope_pctl=config.FLAG_WIDE_ENVELOPE_PCTL,
            lot_z=config.FLAG_LOT_Z,
            no_early_signal="delta below NOISE_CV * sqrt(2) for that parameter",
            noise_cv=config.NOISE_CV,
        ),
        static_limit_policy=("no limit is invented; the seven empty "
                             "Device_Specs cells never fire a limit-based code"),
        clipping_semantics=dict(
            nonpositive_forecast="replaced by the 24h reading, counted in the report",
            envelope_below_point="raised to the point forecast, counted in the report",
            rel_delta_cap=config.FORECAST_REL_DELTA_CAP,
            rel_delta_cap_order="applied before the positivity fallback",
        ),
        emits_disposition=False,
    )


def runtime_contract_digest() -> str:
    payload = json.dumps(runtime_contract_payload(), sort_keys=True,
                         separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()
