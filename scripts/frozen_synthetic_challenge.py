"""Generate and evaluate a fixed synthetic challenge without touching model training.

Generate first; keep the CSV and manifest unchanged. Evaluate separately with the
same shipped operational policy. Labels are injection truth, not hardware truth.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from operational.inference import EPOCHS, IDS, PARAMS, POLICY_VERSION, analyze

SEED = 26170
N = 64
CASES = ('static_pass_latent', 'low_start_late_drifter', 'benign_high_baseline',
         'whole_lot_shift', 'peer_baseline_corruption')
FIELDS = IDS + [f'{p}_{e}h' for p in PARAMS for e in EPOCHS]
REVIEW = {'REJECT', 'HOLD', 'MONITOR'}
SCHEMA = ROOT / 'backend/operational/Operational_DB_Schema.sql'
# Fresh independent draws anchored to published synthetic CMOS_A specification
# baselines, rather than copying any row from the training or holdout fixtures.
BASE = {'IDDQ': (1.5, .16), 'Input_Leakage_Current': (.02, .004),
        'Active_Supply_Current': (90., 4.), 'Propagation_Delay': (9., .7),
        'Output_Rise_Time': (8., .65), 'Output_Fall_Time': (7.5, .6)}


def sha(path: Path) -> str:
    # Freeze CSVs were written with CRLF. Git can check them out as LF on
    # Linux; reconstruct the original line endings before checking the hash.
    payload = path.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
    return hashlib.sha256(payload).hexdigest()


def rows_for(case: str, seed: int) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    rows, labels = [], []
    for i in range(N):
        row = dict(zip(IDS, (f'CH_{case}_{i+1:03d}', f'CH_{case}', 'DIGITAL_CMOS', 'CMOS_A')))
        for p, (mu, sigma) in BASE.items():
            base = max(mu * .25, rng.gauss(mu, sigma))
            for e in EPOCHS:
                row[f'{p}_{e}h'] = round(max(.0001, base * (1 + .025 * e / 168) + rng.gauss(0, sigma * .12)), 6)
        injected = False
        role = 'ordinary_control'
        if case == 'static_pass_latent' and i < 8:
            injected, role = True, 'static_pass_early_drift'
            for e, v in zip(EPOCHS, (7.8, 9.3, 12.2, 14.7)):
                row[f'Output_Rise_Time_{e}h'] = v + rng.uniform(-.04, .04)
        elif case == 'low_start_late_drifter' and i < 8:
            injected, role = True, 'late_onset_drift'
            for e, v in zip(EPOCHS, (1.10, 1.12, 1.15, 8.0)):
                row[f'IDDQ_{e}h'] = v + rng.uniform(-.025, .025)
        elif case == 'benign_high_baseline' and i < 8:
            role = 'stable_high_baseline_control'
            for e, v in zip(EPOCHS, (4.0, 4.02, 4.05, 4.08)):
                row[f'IDDQ_{e}h'] = v + rng.uniform(-.018, .018)
        elif case == 'whole_lot_shift':
            role = 'common_mode_shift_control'
            for e in EPOCHS:
                row[f'IDDQ_{e}h'] *= 1.5
        elif case == 'peer_baseline_corruption' and i < 32:
            injected, role = True, 'peer_corrupting_early_drift'
            start = row['IDDQ_0h']
            for e, v in zip(EPOCHS, (start, 4.0, 5.5, 8.0)):
                row[f'IDDQ_{e}h'] = v + (0 if e == 0 else rng.uniform(-.03, .03))
        rows.append({k: (round(v, 6) if isinstance(v, float) else v) for k, v in row.items()})
        labels.append({'component_id': row['component_id'], 'lot_id': row['lot_id'],
                       'injected_defect': int(injected), 'scenario_role': role})
    return rows, labels


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def generate(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    paths = [folder / name for name in ('challenge_measurements.csv', 'challenge_labels.csv', 'freeze_manifest.json')]
    if any(p.exists() for p in paths):
        raise SystemExit('Freeze already exists. Use the existing files; never overwrite them after evaluation.')
    data, labels = [], []
    for index, case in enumerate(CASES):
        a, b = rows_for(case, SEED + index)
        data.extend(a)
        labels.extend(b)
    write_csv(paths[0], FIELDS, data)
    write_csv(paths[1], ['component_id', 'lot_id', 'injected_defect', 'scenario_role'], labels)
    manifest = {
        'purpose': 'pre-specified new synthetic challenge; no sampled rows from model training fixtures',
        'seed': SEED, 'components_per_lot': N, 'variant': 'CMOS_A', 'cases': CASES,
        'case_definitions': {
            'static_pass_latent': '8 injected rise-time drifters, final 14.7 ns below 15 ns proxy',
            'low_start_late_drifter': '8 injected IDDQ drifters that emerge after 24h',
            'benign_high_baseline': '8 stable elevated-IDDQ controls; all 64 healthy by construction',
            'whole_lot_shift': 'all 64 controls have 1.5x IDDQ at every epoch',
            'peer_baseline_corruption': '32 injected IDDQ drifters among 32 controls',
        },
        'generation': 'seeded independent Gaussian draws around data/reference/Device_Specs.csv synthetic CMOS_A baselines; hard-case patterns explicitly injected',
        'truth': 'synthetic injection labels; not observed hardware defects or verified real healthy parts',
        'measurement_sha256': sha(paths[0]), 'label_sha256': sha(paths[1]),
        'policy_at_freeze': POLICY_VERSION,
    }
    paths[2].write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'frozen': str(folder), 'hashes': [manifest['measurement_sha256'], manifest['label_sha256']]}, indent=2))


def evaluate(folder: Path) -> None:
    manifest = json.loads((folder / 'freeze_manifest.json').read_text())
    measurements = folder / 'challenge_measurements.csv'
    labels_path = folder / 'challenge_labels.csv'
    if sha(measurements) != manifest['measurement_sha256'] or sha(labels_path) != manifest['label_sha256']:
        raise SystemExit('Frozen data or labels have changed; refusing to evaluate.')
    if manifest['policy_at_freeze'] != POLICY_VERSION:
        raise SystemExit('Policy version differs from the frozen manifest.')
    with measurements.open(newline='', encoding='utf-8') as f:
        data = list(csv.DictReader(f))
    with labels_path.open(newline='', encoding='utf-8') as f:
        labels = {r['component_id']: r for r in csv.DictReader(f)}
    assert len(data) == len(labels) == N * len(CASES)
    output = []
    for case in CASES:
        lot_id = f'CH_{case}'
        rows = [r for r in data if r['lot_id'] == lot_id]
        connection = sqlite3.connect(':memory:')
        connection.row_factory = sqlite3.Row
        try:
            connection.executescript(SCHEMA.read_text())
            connection.execute('INSERT INTO lots(lot_id,device_variant,expected_count) VALUES(?,?,?)', (lot_id, 'CMOS_A', N))
            connection.executemany('INSERT INTO components(component_id,lot_id,device_family,device_variant) VALUES(?,?,?,?)',
                                   [tuple(r[k] for k in IDS) for r in rows])
            for epoch in EPOCHS:
                connection.executemany('INSERT INTO measurements(component_id,epoch_h,' + ','.join(PARAMS) +
                                       ') VALUES(' + ','.join('?' for _ in range(2 + len(PARAMS))) + ')',
                                       [(r['component_id'], epoch, *(float(r[f'{p}_{epoch}h']) for p in PARAMS)) for r in rows])
                if epoch not in (24, 168):
                    continue
                run = analyze(connection, {'lot_id': lot_id, 'device_variant': 'CMOS_A', 'expected_count': N}, epoch)
                parts = {r['component_id']: r for r in run['components']}
                injected = {cid for cid in parts if labels[cid]['injected_defect'] == '1'}
                control = set(parts) - injected
                flagged = {cid for cid, part in parts.items() if part['disposition'] in REVIEW}
                high = {cid for cid in control if labels[cid]['scenario_role'] == 'stable_high_baseline_control'}
                output.append({'case': case, 'epoch_h': epoch, 'injected_n': len(injected),
                               'injected_reviewed': len(injected & flagged), 'injected_missed': len(injected - flagged),
                               'control_n': len(control), 'control_reviewed': len(control & flagged),
                               'high_baseline_reviewed': len(high & flagged) if high else None,
                               'dispositions': run['counts'],
                               'missed_injected_ids': sorted(injected - flagged)})
        finally:
            connection.close()
    result = {'policy': POLICY_VERSION, 'measurement_sha256': sha(measurements),
              'label_sha256': sha(labels_path), 'monitor_treatment': 'MONITOR, HOLD, REJECT = sent for review; PASS/PROVISIONAL_PASS = not reviewed',
              'scope': 'newly generated labelled synthetic challenge; distinct rows and lot IDs from training fixtures; designed injections and healthy controls',
              'limitation': 'not independently observed hardware truth or an unbiased deployment false-negative/false-positive estimate; challenge design can differ from real failure distributions',
              'results': output}
    report = folder / 'baseline_report.json'
    if report.exists():
        raise SystemExit('Baseline report already exists; refusing to overwrite it.')
    report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['generate', 'evaluate'])
    parser.add_argument('--folder', type=Path, default=ROOT / 'data/challenge_frozen')
    args = parser.parse_args()
    (generate if args.action == 'generate' else evaluate)(args.folder)
