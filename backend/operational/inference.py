"""Whole-lot serving with immutable 24h forecasts and explicit policy evidence."""
from pathlib import Path
from functools import lru_cache
from copy import copy
import hashlib
import json
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend/runtime'))
PARAMS = ['IDDQ', 'Input_Leakage_Current', 'Active_Supply_Current',
          'Propagation_Delay', 'Output_Rise_Time', 'Output_Fall_Time']
EPOCHS = [0, 24, 96, 168]
IDS = ['component_id', 'lot_id', 'device_family', 'device_variant']
POLICY_VERSION = 'prototype-review-policy-1'


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [clean(v) for v in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def digest(value):
    return hashlib.sha256(json.dumps(clean(value), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


@lru_cache(maxsize=1)
def load_models():
    from modulea.freeze import load
    from moduleb.freeze import load_frozen
    folder = ROOT / 'data/runtime'
    manifest = json.loads((folder / 'runtime_manifest.json').read_text())
    for name, expected in manifest['artifact_hashes'].items():
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Runtime artifact integrity check failed')
    if hashlib.sha256((ROOT / 'data/reference/Device_Specs.csv').read_bytes()).hexdigest() != manifest['spec_sha256']:
        raise ValueError('Specification file no longer matches the runtime manifest')
    a, _ = load(folder / 'module_a.joblib')
    # The missing original B artifact is explicitly rebuilt as REHEARSAL.
    b = load_frozen(folder / 'module_b.joblib', require_production=False)
    return a, b, manifest


def runtime_status():
    try:
        _, _, manifest = load_models()
        return {'ready': True, **manifest}
    except Exception:
        import logging
        logging.getLogger(__name__).exception('Model runtime failed to load')
        return {'ready': False, 'version': 'unavailable',
                'limitations': 'Runtime unavailable. Run scripts/build_runtime.py with the pinned dependencies; inspect server logs.'}


def frame_for_lot(connection, lot, epoch):
    components = connection.execute('SELECT * FROM components WHERE lot_id=? ORDER BY component_id', (lot['lot_id'],)).fetchall()
    if len(components) != lot['expected_count']:
        raise ValueError(f"Incomplete lot: {len(components)} of {lot['expected_count']} components registered")
    rows = []
    missing = []
    for c in components:
        row = {k: c[k] for k in IDS}
        measured = {m['epoch_h']: m for m in connection.execute('SELECT * FROM measurements WHERE component_id=?', (c['component_id'],))}
        for e in EPOCHS:
            if e > epoch:
                continue
            if e not in measured:
                missing.append(f"{c['component_id']}@{e}h")
                continue
            for p in PARAMS:
                row[f'{p}_{e}h'] = measured[e][p]
        rows.append(row)
    if missing:
        raise ValueError(f"Waiting for {len(missing)} measurement records: {', '.join(missing[:5])}")
    return pd.DataFrame(rows)


def analyze(connection, lot, epoch):
    original_a, b, manifest = load_models()
    frame = frame_for_lot(connection, lot, epoch)
    version = digest({'artifacts': manifest['artifact_hashes'], 'policy': POLICY_VERSION})
    input_hash = digest(frame.to_dict('records'))
    existing = connection.execute('SELECT run_id, payload FROM screening_runs WHERE lot_id=? AND epoch_h=? AND input_hash=? AND runtime_version=?',
                                  (lot['lot_id'], epoch, input_hash, version)).fetchone()
    if existing:
        return {'run_id': existing['run_id'], **json.loads(existing['payload']), 'reused': True}
    a = copy(original_a)
    a.expected_lot_sizes = {lot['lot_id']: lot['expected_count']}
    a_out = a.predict(frame, epoch=epoch).set_index('component_id')
    forecasts = {}
    forecast_receipt = None
    if epoch >= 24:
        from moduleb.predict import predict_frame
        early = frame[IDS + [f'{p}_{e}h' for p in PARAMS for e in (0, 24)]]
        early_hash = digest(early.to_dict('records'))
        saved = connection.execute('SELECT * FROM forecast_runs WHERE lot_id=? AND input_hash=? AND runtime_version=?',
                                   (lot['lot_id'], early_hash, version)).fetchone()
        if saved:
            pack = json.loads(saved['payload'])
            forecast_receipt = {'forecast_id': saved['forecast_id'], 'created_at': saved['created_at'], 'reused': True, **pack['receipt']}
        else:
            predictions, report = predict_frame(b, early, expected_lot_sizes={lot['lot_id']: lot['expected_count']})
            pack = {'rows': clean(predictions.to_dict('records')), 'receipt': {
                'input_hash': early_hash, 'input_epochs': [0, 24], 'generated_when_epoch_h': epoch,
                'report': report.as_dict(), 'release_state': 'REHEARSAL_REBUILD'}}
            cursor = connection.execute('INSERT INTO forecast_runs(lot_id,input_hash,runtime_version,payload) VALUES(?,?,?,?)',
                                        (lot['lot_id'], early_hash, version, json.dumps(pack, allow_nan=False)))
            saved = connection.execute('SELECT * FROM forecast_runs WHERE forecast_id=?', (cursor.lastrowid,)).fetchone()
            forecast_receipt = {'forecast_id': saved['forecast_id'], 'created_at': saved['created_at'], 'reused': False, **pack['receipt']}
        forecasts = {r['component_id']: r for r in pack['rows']}
    output = []
    for raw in frame.to_dict('records'):
        cid = raw['component_id']
        observed = clean(a_out.loc[cid].to_dict())
        forecast = forecasts.get(cid)
        breaches, forecast_risks, parameters = [], [], {}
        for p in PARAMS:
            limit = a.specs.limit(lot['device_variant'], p)
            limit = float(limit) if np.isfinite(limit) else None
            point = forecast.get(f'predicted_{p}_168h') if forecast else None
            upper = forecast.get(f'module_b_p95_{p}_168h') if forecast else None
            if limit is not None and any(raw[f'{p}_{e}h'] > limit for e in EPOCHS if e <= epoch):
                breaches.append(p)
            if limit is not None and forecast and ((point is not None and point > limit) or (upper is not None and upper > limit)):
                forecast_risks.append(p)
            parameters[p] = {'unit': 'µA' if p in PARAMS[:3] else 'ns', 'limit': limit,
                             'observed': {str(e): raw[f'{p}_{e}h'] for e in EPOCHS if e <= epoch},
                             'predicted_168h': point, 'upper_168h': upper,
                             'absolute_error': abs(raw[f'{p}_168h'] - point) if epoch == 168 and point is not None else None}
        codes = str(forecast.get('module_b_reason_codes', '')) if forecast else ''
        if breaches:
            disposition, reason = 'REJECT', 'Observed specification breach: ' + ', '.join(breaches)
        elif forecast_risks:
            disposition, reason = 'HOLD', 'Forecast or upper bound crosses a limit: ' + ', '.join(forecast_risks)
        elif observed['module_a_disposition'] == 'MONITOR' or any(c in codes for c in ['B_HIGH_FORECAST_DRIFT', 'B_WIDE_ENVELOPE', 'B_LOT_OUTLIER_24H']):
            disposition, reason = 'MONITOR', 'Statistical or forecast evidence requires review'
        else:
            disposition = 'PASS' if epoch == 168 else 'PROVISIONAL_PASS'
            reason = 'No configured alert at this epoch; this is not a qualification certificate'
        output.append({'component_id': cid, 'disposition': disposition, 'reason': reason,
                       'module_a': observed, 'module_b': forecast, 'parameters': parameters,
                       'observed_breaches': breaches, 'forecast_risks': forecast_risks})
    from collections import Counter
    payload = clean({'lot_id': lot['lot_id'], 'device_variant': lot['device_variant'], 'epoch_h': epoch,
                     'input_hash': input_hash, 'runtime_version': version, 'policy_version': POLICY_VERSION,
                     'model_provenance': manifest, 'forecast_receipt': forecast_receipt,
                     'counts': dict(Counter(r['disposition'] for r in output)), 'components': output})
    cursor = connection.execute('INSERT INTO screening_runs(lot_id,epoch_h,input_hash,runtime_version,payload) VALUES(?,?,?,?,?)',
                                (lot['lot_id'], epoch, input_hash, version, json.dumps(payload, allow_nan=False)))
    return {'run_id': cursor.lastrowid, **payload, 'reused': False}
