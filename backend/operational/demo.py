"""Read-only demo using the same whole-lot inference path as the workspace.

The public training and frozen synthetic challenge fixtures are analysed in
in-memory databases. This does not add runs to the operator's database or
expose private holdout truth; the challenge's public injection label is explicit.
"""
import csv
import hashlib
import json
import sqlite3
from functools import lru_cache
from pathlib import Path
from statistics import median

from .inference import IDS, EPOCHS, PARAMS, analyze

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'data/operational/DEMO_A_168h.csv'
HISTORY_FIXTURE = ROOT / 'data/operational/DEMO_PRIOR_ALERT_168h.csv'
FROZEN_FOLDER = ROOT / 'data/challenge_frozen'
SCHEMA = Path(__file__).with_name('Operational_DB_Schema.sql')
CASES = [
    ('DEMO_C00001', 'Observed limit breach', 'An observed rise-time value already exceeds its specification at 24h.'),
    ('DEMO_C00024', 'Static-pass review', 'No observed specification breach at 24h; the forecast envelope triggers MONITOR.'),
    ('DEMO_C00002', 'Provisional pass', 'No configured warning at 24h. This is not a qualification certificate.'),
]


def frozen_static_pass_case():
    """A planted drift from the frozen challenge, scored by the real lot path."""
    manifest = json.loads((FROZEN_FOLDER / 'freeze_manifest.json').read_text(encoding='utf-8'))
    for name, key in (('challenge_measurements.csv', 'measurement_sha256'),
                      ('challenge_labels.csv', 'label_sha256')):
        if hashlib.sha256((FROZEN_FOLDER / name).read_bytes()).hexdigest() != manifest[key]:
            raise ValueError('Frozen challenge integrity check failed')
    with (FROZEN_FOLDER / 'challenge_measurements.csv').open(newline='', encoding='utf-8') as f:
        rows = [r for r in csv.DictReader(f) if r['lot_id'] == 'CH_static_pass_latent']
    with (FROZEN_FOLDER / 'challenge_labels.csv').open(newline='', encoding='utf-8') as f:
        labels = {r['component_id']: r for r in csv.DictReader(f) if r['lot_id'] == 'CH_static_pass_latent'}
    cid = 'CH_static_pass_latent_004'
    if len(rows) != 64 or labels[cid]['injected_defect'] != '1':
        raise ValueError('Frozen static-pass lot is incomplete or missing its injection label')
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript(SCHEMA.read_text(encoding='utf-8'))
        lot = {'lot_id': 'CH_static_pass_latent', 'device_variant': 'CMOS_A', 'expected_count': len(rows)}
        connection.execute('INSERT INTO lots(lot_id,device_variant,expected_count) VALUES(?,?,?)',
                           (lot['lot_id'], lot['device_variant'], len(rows)))
        connection.executemany('INSERT INTO components(component_id,lot_id,device_family,device_variant) VALUES(?,?,?,?)',
                               [tuple(row[k] for k in IDS) for row in rows])
        runs = {}
        for epoch in EPOCHS:
            connection.executemany('INSERT INTO measurements(component_id,epoch_h,' + ','.join(PARAMS) +
                                   ') VALUES(' + ','.join('?' for _ in range(2 + len(PARAMS))) + ')',
                                   [(row['component_id'], epoch, *(float(row[f'{p}_{epoch}h']) for p in PARAMS))
                                    for row in rows])
            if epoch in (24, 168):
                runs[epoch] = analyze(connection, lot, epoch)
        early = next(part for part in runs[24]['components'] if part['component_id'] == cid)
        later = next(part for part in runs[168]['components'] if part['component_id'] == cid)
        if early['disposition'] != 'PROVISIONAL_PASS' or later['disposition'] != 'MONITOR':
            raise ValueError('Frozen case no longer matches its expected observed decisions')
        if early['observed_breaches'] or later['observed_breaches']:
            raise ValueError('Static-pass demo unexpectedly breached a supplied limit')
        if runs[24]['forecast_receipt']['forecast_id'] != runs[168]['forecast_receipt']['forecast_id']:
            raise ValueError('The 24h forecast was not reused')
        parameters = {}
        for p in PARAMS:
            observed = later['parameters'][p]
            parameters[p] = {
                'unit': observed['unit'], 'limit': observed['limit'],
                'lot_median_24h': median(float(r[f'{p}_24h']) for r in rows),
                'observed_early': {e: observed['observed'][e] for e in ('0', '24')},
                'observed_retrospective': {e: observed['observed'][e] for e in ('96', '168')},
                'predicted_168h': observed['predicted_168h'], 'upper_168h': observed['upper_168h'],
            }
        return {'component_id': cid, 'title': 'Planted drift · missed at 24h',
                'description': 'Synthetic injected rise-time drift stays below the 15 ns static proxy at every checkpoint. The shipped policy misses this case at 24h, then sends it for review at 168h.',
                'synthetic_label': 'injected drift, not a verified hardware defect',
                'fixture_kind': 'frozen synthetic challenge', 'lot_size': len(rows),
                'primary_parameter': 'Output_Rise_Time', 'parameters': parameters,
                'at_24h': {'disposition': early['disposition'], 'reason': early['reason'],
                           'module_a_disposition': early['module_a']['module_a_disposition'],
                           'module_a_score': early['module_a']['module_a_score'],
                           'module_b_reason_codes': early['module_b'].get('module_b_reason_codes', ''),
                           'observed_breaches': early['observed_breaches']},
                'at_168h': {'disposition': later['disposition'], 'reason': later['reason'],
                            'prior_24h_alert': later['prior_24h_alert']}}
    finally:
        connection.close()


def history_case():
    """A fourth, separate 50-part lot with a reproducible earlier-alert case."""
    with HISTORY_FIXTURE.open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    lot_id = 'PEER_BASELINE_CORRUPTION'
    if len(rows) != 50 or {r['lot_id'] for r in rows} != {lot_id}:
        raise ValueError('History demo fixture is incomplete or changed')
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript(SCHEMA.read_text(encoding='utf-8'))
        lot = {'lot_id': lot_id, 'device_variant': 'CMOS_A', 'expected_count': len(rows)}
        connection.execute('INSERT INTO lots(lot_id,device_variant,expected_count) VALUES(?,?,?)',
                           (lot_id, 'CMOS_A', len(rows)))
        connection.executemany('INSERT INTO components(component_id,lot_id,device_family,device_variant) VALUES(?,?,?,?)',
                               [tuple(row[k] for k in IDS) for row in rows])
        runs = {}
        for epoch in EPOCHS:
            connection.executemany('INSERT INTO measurements(component_id,epoch_h,' + ','.join(PARAMS) +
                                   ') VALUES(' + ','.join('?' for _ in range(2 + len(PARAMS))) + ')',
                                   [(row['component_id'], epoch, *(float(row[f'{p}_{epoch}h']) for p in PARAMS))
                                    for row in rows])
            if epoch in (24, 168):
                runs[epoch] = analyze(connection, lot, epoch)
        cid = 'PEER_BASELINE_CORRUPTION_001'
        early = next(r for r in runs[24]['components'] if r['component_id'] == cid)
        later = next(r for r in runs[168]['components'] if r['component_id'] == cid)
        if (early['disposition'], later['disposition']) != ('MONITOR', 'PASS') or not later['prior_24h_alert']:
            raise ValueError('History demo case no longer matches its label')
        if runs[24]['forecast_receipt']['forecast_id'] != runs[168]['forecast_receipt']['forecast_id']:
            raise ValueError('The early forecast was not reused at 168h')
        parameters = {}
        for p in PARAMS:
            observed = later['parameters'][p]
            parameters[p] = {
                'unit': observed['unit'], 'limit': observed['limit'],
                'lot_median_24h': median(float(r[f'{p}_24h']) for r in rows),
                'observed_early': {e: observed['observed'][e] for e in ('0', '24')},
                'observed_retrospective': {e: observed['observed'][e] for e in ('96', '168')},
                'predicted_168h': observed['predicted_168h'],
                'upper_168h': observed['upper_168h'],
            }
        return {'component_id': cid, 'title': 'Earlier alert → PASS',
                'description': 'Constructed common drift: half the lot is shifted at 24h. This part is MONITOR at 24h but the later snapshot says PASS.',
                'lot_size': len(rows), 'fixture_kind': 'constructed stress case, not independent accuracy evidence',
                'primary_parameter': 'IDDQ', 'parameters': parameters,
                'at_24h': {'disposition': early['disposition'], 'reason': early['reason'],
                           'module_a_disposition': early['module_a']['module_a_disposition'],
                           'module_a_score': early['module_a']['module_a_score'],
                           'module_b_reason_codes': early['module_b'].get('module_b_reason_codes', ''),
                           'observed_breaches': early['observed_breaches']},
                'at_168h': {'disposition': later['disposition'], 'reason': later['reason'],
                            'prior_24h_alert': later['prior_24h_alert']}}
    finally:
        connection.close()


@lru_cache(maxsize=1)
def demo_result():
    with FIXTURE.open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 78 or {r['lot_id'] for r in rows} != {'DEMO_A'}:
        raise ValueError('Demo fixture is incomplete or changed')
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript(SCHEMA.read_text(encoding='utf-8'))
        lot = {'lot_id': 'DEMO_A', 'device_variant': 'CMOS_A', 'expected_count': len(rows)}
        connection.execute('INSERT INTO lots(lot_id,device_variant,expected_count) VALUES(?,?,?)',
                           (lot['lot_id'], lot['device_variant'], len(rows)))
        connection.executemany('INSERT INTO components(component_id,lot_id,device_family,device_variant) VALUES(?,?,?,?)',
                               [tuple(row[k] for k in IDS) for row in rows])
        runs = {}
        for epoch in EPOCHS:
            connection.executemany('INSERT INTO measurements(component_id,epoch_h,' + ','.join(PARAMS) +
                                   ') VALUES(' + ','.join('?' for _ in range(2 + len(PARAMS))) + ')',
                                   [(row['component_id'], epoch, *(float(row[f'{p}_{epoch}h']) for p in PARAMS))
                                    for row in rows])
            if epoch in (24, 168):
                runs[epoch] = analyze(connection, lot, epoch)
        by_epoch = {epoch: {part['component_id']: part for part in run['components']}
                    for epoch, run in runs.items()}
        cases = []
        expected_decisions = ('REJECT', 'MONITOR', 'PROVISIONAL_PASS')
        for (cid, title, description), expected in zip(CASES, expected_decisions):
            early, later = by_epoch[24][cid], by_epoch[168][cid]
            if early['disposition'] != expected:
                raise ValueError('Demo case no longer matches its label')
            primary = ('Output_Rise_Time' if cid == 'DEMO_C00001' else
                       'Propagation_Delay' if cid == 'DEMO_C00024' else 'IDDQ')
            parameters = {}
            for p in PARAMS:
                observed = later['parameters'][p]
                parameters[p] = {
                    'unit': observed['unit'], 'limit': observed['limit'],
                    'lot_median_24h': median(float(r[f'{p}_24h']) for r in rows),
                    'observed_early': {e: observed['observed'][e] for e in ('0', '24')},
                    'observed_retrospective': {e: observed['observed'][e] for e in ('96', '168')},
                    'predicted_168h': observed['predicted_168h'],
                    'upper_168h': observed['upper_168h'],
                }
            cases.append({'component_id': cid, 'title': title, 'description': description,
                          'primary_parameter': primary, 'parameters': parameters,
                          'at_24h': {'disposition': early['disposition'], 'reason': early['reason'],
                                     'module_a_disposition': early['module_a']['module_a_disposition'],
                                     'module_a_score': early['module_a']['module_a_score'],
                                     'module_b_reason_codes': early['module_b'].get('module_b_reason_codes', ''),
                                     'observed_breaches': early['observed_breaches']},
                          'at_168h': {'disposition': later['disposition'], 'reason': later['reason']}})
        cases.append(history_case())
        cases.append(frozen_static_pass_case())
        return {'fixture': 'DEMO_A · public synthetic training fixture', 'lot_size': len(rows),
                'policy_version': runs[24]['policy_version'],
                'module_b_release_state': runs[24]['forecast_receipt']['release_state'],
                'early_counts': runs[24]['counts'], 'later_counts': runs[168]['counts'],
                'forecast_reused_at_168h': runs[24]['forecast_receipt']['forecast_id'] == runs[168]['forecast_receipt']['forecast_id'],
                'cases': cases,
                'limitations': 'The training and constructed examples have no independently verified hardware defect labels. The frozen example has a synthetic injection label; none establishes real-world accuracy.'}
    finally:
        connection.close()
