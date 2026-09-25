"""The serving contract: a lot is complete because it was proved complete.

P0-B1. Every test here is about the same failure: a lot delivered with
components missing produces a well-formed, confident, different answer. A row
count cannot detect it, so the contract asks for a proof and refuses without
one.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from conftest import expected_sizes

from moduleb import config, models, predict, serving
from moduleb.constants import PARAMS, TARGET_COLS

ROOT = Path(__file__).resolve().parent.parent


def _artifact(synth_feat, specs):
    from moduleb.envelope import fit_envelope
    base, lim = specs
    return dict(models={p: models.fit_one(synth_feat, p, config.RECOMMENDED[p]) for p in PARAMS},
                envelopes={p: fit_envelope(synth_feat, p, config.RECOMMENDED[p]) for p in PARAMS},
                limits=lim, base=base, manifest={})


@pytest.fixture(scope="module")
def art(synth, specs):
    from moduleb.features import add_features
    return _artifact(add_features(synth, specs[0]).assign(fold=0), specs)


def _raw(frame):
    return frame.drop(columns=[c for c in TARGET_COLS if c in frame.columns]).reset_index(drop=True)


# ---------------------------------------------------------------- accepted
def test_complete_lot_is_accepted_on_request_metadata(art, synth):
    raw = _raw(synth)
    out, rep = predict.predict_frame(art, raw, expected_lot_sizes=expected_sizes(raw),
                                     name="complete")
    assert len(out) == len(raw)
    assert rep.clean and not rep.partial_lot_override
    assert rep.completeness["proof"] == "request_metadata"
    assert rep.completeness["offending_lots"] == []


def test_complete_delivery_is_accepted_on_an_attestation(art, synth, tmp_path):
    raw = _raw(synth)
    path = tmp_path / "delivery.csv"
    raw.to_csv(path, index=False)
    att = serving.file_attestation(path, source="test custodian", n_rows=len(raw),
                                   n_lots=int(raw.lot_id.nunique()))
    out, rep = predict.predict_csv(art, path, tmp_path / "out.csv", delivery=att)
    assert len(out) == len(raw)
    assert rep.completeness["proof"] == "delivery_attestation" and rep.clean


# ---------------------------------------------------------------- refused
def test_incomplete_lot_above_the_floor_is_rejected(art, synth):
    """The case a size floor cannot see: 30 of 35 rows clears MIN_LOT_COHORT."""
    raw = _raw(synth)
    sizes = expected_sizes(raw)
    lot = sorted(raw.lot_id.unique())[0]
    short = pd.concat([raw[raw.lot_id == lot].iloc[:30], raw[raw.lot_id != lot]],
                      ignore_index=True)
    assert (short.lot_id == lot).sum() > config.MIN_LOT_COHORT - 1
    with pytest.raises(serving.IncompleteLotError, match="incomplete delivery"):
        predict.predict_frame(art, short, expected_lot_sizes=sizes, name="short")


def test_incomplete_lot_below_the_floor_is_rejected(art, synth):
    raw = _raw(synth)
    sizes = expected_sizes(raw)
    lot = sorted(raw.lot_id.unique())[0]
    tiny = pd.concat([raw[raw.lot_id == lot].iloc[:5], raw[raw.lot_id != lot]],
                     ignore_index=True)
    with pytest.raises(serving.IncompleteLotError):
        predict.predict_frame(art, tiny, expected_lot_sizes=sizes, name="tiny")


def test_expected_count_mismatch_is_rejected_in_both_directions(art, synth):
    raw = _raw(synth[synth.lot_id == sorted(synth.lot_id.unique())[0]])
    too_big = {str(raw.lot_id.iloc[0]): len(raw) + 1}
    with pytest.raises(serving.IncompleteLotError):
        predict.predict_frame(art, raw, expected_lot_sizes=too_big, name="mismatch")


def test_a_lot_with_no_declared_size_is_rejected(art, synth):
    raw = _raw(synth)
    sizes = expected_sizes(raw)
    dropped = sorted(sizes)[0]
    sizes.pop(dropped)
    with pytest.raises(serving.IncompleteLotError, match="no declared size"):
        predict.predict_frame(art, raw, expected_lot_sizes=sizes, name="undeclared")


def test_no_proof_at_all_is_rejected(art, synth):
    raw = _raw(synth)
    with pytest.raises(serving.IncompleteLotError, match="cannot prove"):
        predict.predict_frame(art, raw, name="no-proof")


def test_attestation_mismatch_is_rejected(art, synth, tmp_path):
    raw = _raw(synth)
    path = tmp_path / "delivery.csv"
    raw.to_csv(path, index=False)
    good = serving.file_attestation(path, source="t", n_rows=len(raw),
                                    n_lots=int(raw.lot_id.nunique()))
    wrong_rows = serving.DeliveryAttestation(good.source, good.sha256,
                                             good.n_rows - 7, good.n_lots)
    with pytest.raises(serving.IncompleteLotError):
        predict.predict_csv(art, path, tmp_path / "o1.csv", delivery=wrong_rows)
    wrong_hash = serving.DeliveryAttestation(good.source, "0" * 64, good.n_rows,
                                             good.n_lots)
    with pytest.raises(serving.IncompleteLotError):
        predict.predict_csv(art, path, tmp_path / "o2.csv", delivery=wrong_hash)


# ---------------------------------------------------------------- override
def test_override_works_and_is_recorded(art, synth):
    raw = _raw(synth)
    sizes = expected_sizes(raw)
    lot = sorted(raw.lot_id.unique())[0]
    short = pd.concat([raw[raw.lot_id == lot].iloc[:30], raw[raw.lot_id != lot]],
                      ignore_index=True)
    out, rep = predict.predict_frame(art, short, expected_lot_sizes=sizes,
                                     allow_partial_lot=True, name="override")
    assert len(out) == len(short)
    c = rep.completeness
    assert rep.partial_lot_override and c["override"] is True
    assert c["complete"] is False
    assert lot in c["offending_lots"]
    assert c["observed"][lot] == 30 and c["expected"][lot] == 35
    assert c["serving_contract_version"] == serving.SERVING_CONTRACT_VERSION
    assert rep.runtime_contract_digest == serving.runtime_contract_digest()


def test_override_makes_the_report_non_clean(art, synth):
    raw = _raw(synth)
    sizes = expected_sizes(raw)
    lot = sorted(raw.lot_id.unique())[0]
    short = pd.concat([raw[raw.lot_id == lot].iloc[:30], raw[raw.lot_id != lot]],
                      ignore_index=True)
    _, rep = predict.predict_frame(art, short, expected_lot_sizes=sizes,
                                   allow_partial_lot=True, name="override")
    assert not rep.clean
    assert any("partial-lot override" in line for line in rep.lines())
    assert any("override lot" in line for line in rep.lines())


# ---------------------------------------------------------------- unchanged
def test_complete_lot_predictions_are_unchanged_by_the_new_contract(art, synth, tmp_path):
    """The guard converts a silently wrong answer into an error. It must not
    move a single forecast that was already valid: both proofs, same numbers."""
    raw = _raw(synth)
    path = tmp_path / "d.csv"
    raw.to_csv(path, index=False)
    att = serving.file_attestation(path, source="t", n_rows=len(raw),
                                   n_lots=int(raw.lot_id.nunique()))

    a, _ = predict.predict_frame(art, raw, expected_lot_sizes=expected_sizes(raw),
                                 name="meta")
    b, _ = predict.predict_frame(art, raw, delivery=att, file_sha256=att.sha256,
                                 name="attested")
    num = a.select_dtypes("number").columns.tolist()
    assert len(num) >= 12
    # Same frame, two different proofs: bit-identical. Which proof was used
    # changes what is recorded, never what is computed.
    np.testing.assert_allclose(a[num].to_numpy(float), b[num].to_numpy(float),
                               rtol=0, atol=0)

    # Through the file front end the numbers survive a CSV round trip to within
    # float text precision, which is a property of the file, not of the contract.
    c, _ = predict.predict_csv(art, path, tmp_path / "o.csv", delivery=att)
    np.testing.assert_allclose(a[num].to_numpy(float), c[num].to_numpy(float),
                               rtol=1e-9, atol=0)
    assert (a.module_b_reason_codes == b.module_b_reason_codes).all()
    assert (a.module_b_primary_parameter == b.module_b_primary_parameter).all()


# ---------------------------------------------------------------- no bypass
def test_predict_frame_always_runs_the_completeness_check():
    """Unconditional, not behind an `if`. The old cohort guard was skipped when
    allow_partial_lot was set, which meant the override path recorded nothing."""
    src = (ROOT / "moduleb" / "predict.py").read_text()
    call = re.search(r"comp = serving\.assert_delivery_complete\(", src)
    assert call, "predict_frame no longer calls the serving contract"
    before = src[:call.start()].rsplit("\n", 2)[-2]
    assert not before.strip().startswith("if "), "the completeness check is conditional"


def test_no_shipped_prediction_path_skips_the_proof():
    """Every predict_frame / predict_csv call in the shipped stages and notebooks
    must state how completeness was proved, or explicitly take the override."""
    offenders = []
    for path in sorted((ROOT / "scripts").glob("*.py")) + \
            sorted((ROOT / "notebooks").glob("*.ipynb")):
        text = path.read_text()
        for m in re.finditer(r"predict\.predict_(frame|csv)\(", text):
            window = text[m.start(): m.start() + 500]
            if not any(k in window for k in ("expected_lot_sizes", "delivery=",
                                             "allow_partial_lot")):
                offenders.append(f"{path.name}@{m.start()}")
    assert not offenders, f"prediction calls with no completeness proof: {offenders}"
