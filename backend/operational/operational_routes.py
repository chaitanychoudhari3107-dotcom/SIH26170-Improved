"""Transactional lot ingestion, whole-lot inference, and append-only reviews."""
import csv
import io
import json
import sqlite3
from contextlib import closing
from typing import Literal
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field, FiniteFloat, ConfigDict
from .operational_db import get_connection
from .access import read_access, write_access, access_mode, has_access
from .inference import PARAMS, EPOCHS, IDS, runtime_status, analyze, attach_prior_alerts
from .demo import demo_result

router = APIRouter(prefix='/api', tags=['Operational workspace'])
VARIANTS = Literal['CMOS_A', 'CMOS_B', 'CMOS_C']
ID_PATTERN = r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$'


class StrictInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class MeasurementInput(StrictInput):
    component_id: str = Field(pattern=ID_PATTERN)
    lot_id: str = Field(pattern=ID_PATTERN)
    device_variant: VARIANTS
    epoch_h: Literal[0, 24, 96, 168]
    IDDQ: FiniteFloat = Field(gt=0)
    Input_Leakage_Current: FiniteFloat = Field(gt=0)
    Active_Supply_Current: FiniteFloat = Field(gt=0)
    Propagation_Delay: FiniteFloat = Field(gt=0)
    Output_Rise_Time: FiniteFloat = Field(gt=0)
    Output_Fall_Time: FiniteFloat = Field(gt=0)
    measured_at: datetime | None = None


class ImportInput(StrictInput):
    csv_text: str = Field(min_length=10, max_length=2_000_000)
    lot_id: str = Field(pattern=ID_PATTERN)
    device_variant: VARIANTS
    expected_count: int = Field(ge=30, le=1000, strict=True)
    epoch_h: Literal[0, 24, 96, 168]


class AnalyzeInput(StrictInput):
    epoch_h: Literal[0, 24, 96, 168]


class ReviewInput(StrictInput):
    component_id: str = Field(pattern=ID_PATTERN)
    action: Literal['ACKNOWLEDGE', 'REQUEST_RETEST', 'HOLD', 'REJECT', 'APPROVE']
    reason: str = Field(min_length=10, max_length=2000)


class FeedbackInput(StrictInput):
    component_id: str = Field(pattern=ID_PATTERN)
    suspected_reason: str = Field(min_length=10, max_length=2000)
    evidence_reference: str = Field(min_length=10, max_length=2000)


class FeedbackResolution(StrictInput):
    status: Literal['QA_REVIEWED_DEFECT', 'DISMISSED']
    resolution_reason: str = Field(min_length=10, max_length=2000)


def fetch_lot(connection, lot_id):
    lot = connection.execute('SELECT * FROM lots WHERE lot_id=?', (lot_id,)).fetchone()
    if lot is None:
        raise HTTPException(404, 'Lot not found')
    return lot


def store_measurement(connection, data, source='manual'):
    component = connection.execute('SELECT * FROM components WHERE component_id=?', (data.component_id,)).fetchone()
    if component is not None and (component['lot_id'] != data.lot_id or component['device_variant'] != data.device_variant):
        raise HTTPException(409, f'{data.component_id}: component identity conflicts with existing records')
    existing = connection.execute('SELECT * FROM measurements WHERE component_id=? AND epoch_h=?', (data.component_id, data.epoch_h)).fetchone()
    if existing:
        if source == 'csv' and all(existing[p] == getattr(data, p) for p in PARAMS):
            return False
        raise HTTPException(409, f'{data.component_id}@{data.epoch_h}h already exists; measurements are immutable')
    if component is None:
        lot = fetch_lot(connection, data.lot_id)
        n = connection.execute('SELECT COUNT(*) FROM components WHERE lot_id=?', (data.lot_id,)).fetchone()[0]
        if n >= lot['expected_count']:
            raise HTTPException(409, 'This lot already contains its declared number of components')
        connection.execute('INSERT INTO components(component_id,lot_id,device_variant) VALUES(?,?,?)', (data.component_id, data.lot_id, data.device_variant))
    names = ['component_id', 'epoch_h'] + PARAMS + ['source']
    values = [data.component_id, data.epoch_h] + [getattr(data, p) for p in PARAMS] + [source]
    if data.measured_at:
        names.append('measured_at')
        values.append(data.measured_at.isoformat())
    connection.execute(f"INSERT INTO measurements({','.join(names)}) VALUES({','.join('?' for _ in names)})", values)
    connection.execute('UPDATE components SET updated_at=CURRENT_TIMESTAMP WHERE component_id=?', (data.component_id,))
    return True


def parse_import(data):
    reader = csv.DictReader(io.StringIO(data.csv_text.lstrip('\ufeff')))
    epochs = [e for e in EPOCHS if e <= data.epoch_h]
    columns = IDS + [f'{p}_{e}h' for p in PARAMS for e in epochs]
    headers = reader.fieldnames or []
    if len(headers) != len(set(headers)) or set(headers) != set(columns):
        raise HTTPException(422, {'message': 'CSV headers must match the selected epoch template exactly',
                                  'missing': sorted(set(columns) - set(headers)), 'unexpected': sorted(set(headers) - set(columns))})
    rows, measurements, seen = [], [], set()
    from pydantic import ValidationError
    for line, row in enumerate(reader, start=2):
        if len(rows) >= 1000 or len(row) != len(columns) or any(v is None for v in row.values()):
            raise HTTPException(422, f'Invalid CSV row or too many rows at line {line}')
        row = {k: v.strip() for k, v in row.items()}
        if row['lot_id'] != data.lot_id or row['device_variant'] != data.device_variant or row['device_family'] != 'DIGITAL_CMOS':
            raise HTTPException(422, f'Line {line}: lot, variant or device family differs from import declaration')
        if row['component_id'] in seen:
            raise HTTPException(422, f'Line {line}: duplicate component ID')
        seen.add(row['component_id'])
        try:
            for epoch in epochs:
                measurements.append(MeasurementInput(component_id=row['component_id'], lot_id=data.lot_id,
                    device_variant=data.device_variant, epoch_h=epoch, **{p: row[f'{p}_{epoch}h'] for p in PARAMS}))
        except ValidationError:
            raise HTTPException(422, f'Line {line}: IDs must be valid and measurements must be finite positive numbers')
        rows.append(row)
    if not rows or len(rows) > data.expected_count:
        raise HTTPException(422, 'Import must contain between one and the declared number of components')
    return rows, measurements


def ensure_lot(connection, data):
    existing = connection.execute('SELECT * FROM lots WHERE lot_id=?', (data.lot_id,)).fetchone()
    if existing and (existing['expected_count'] != data.expected_count or existing['device_variant'] != data.device_variant):
        raise HTTPException(409, 'Lot declaration conflicts with existing lot; use the original declared size and variant')
    if not existing:
        connection.execute('INSERT INTO lots(lot_id,device_variant,expected_count) VALUES(?,?,?)', (data.lot_id, data.device_variant, data.expected_count))


@router.get('/operational/config')
def configuration(request: Request):
    return {'mode': access_mode(), 'can_write': has_access(request), 'min_lot_size': 30,
            'parameters': PARAMS, 'epochs': EPOCHS, 'runtime': runtime_status()}


@router.get('/operational/demo')
def guided_demo():
    """Public read-only illustration of the real policy on a fixed training lot."""
    if not runtime_status()['ready']:
        raise HTTPException(503, 'Runtime models unavailable for the guided demo')
    return demo_result()


@router.get('/operational/access', dependencies=[Depends(write_access)])
def verify_access():
    return {'authorized': True, 'actor': 'shared_operator'}


@router.get('/operational/template')
def template(epoch_h: Literal[0, 24, 96, 168] = 24):
    columns = IDS + [f'{p}_{e}h' for p in PARAMS for e in EPOCHS if e <= epoch_h]
    return Response(','.join(columns) + '\n', media_type='text/csv', headers={'Content-Disposition': f'attachment; filename="measurements_{epoch_h}h.csv"'})


@router.post('/operational/import/validate', dependencies=[Depends(write_access)])
def validate_import(data: ImportInput):
    rows, measurements = parse_import(data)
    with closing(get_connection()) as connection:
        # Exercise the same transactional path then roll back: conflict checks are identical.
        connection.execute('BEGIN IMMEDIATE')
        try:
            ensure_lot(connection, data)
            inserted = sum(store_measurement(connection, m, 'csv') for m in measurements)
            registered = connection.execute('SELECT COUNT(*) FROM components WHERE lot_id=?', (data.lot_id,)).fetchone()[0]
            return {'valid': True, 'rows': len(rows), 'new_measurements': inserted,
                    'registered_after_import': registered, 'expected_count': data.expected_count,
                    'preview': rows[:5], 'units': {p: 'µA' if p in PARAMS[:3] else 'ns' for p in PARAMS}}
        finally:
            connection.rollback()


@router.post('/operational/import', dependencies=[Depends(write_access)])
def import_measurements(data: ImportInput):
    rows, measurements = parse_import(data)
    with closing(get_connection()) as connection:
        with connection:
            connection.execute('BEGIN IMMEDIATE')
            ensure_lot(connection, data)
            inserted = sum(store_measurement(connection, m, 'csv') for m in measurements)
    return {'lot_id': data.lot_id, 'rows': len(rows), 'inserted_measurements': inserted, 'unchanged_measurements': len(measurements)-inserted}


@router.post('/measurements', dependencies=[Depends(write_access)])
def add_measurement(data: MeasurementInput):
    with closing(get_connection()) as connection:
        with connection:
            connection.execute('BEGIN IMMEDIATE')
            lot = fetch_lot(connection, data.lot_id)
            if lot['device_variant'] != data.device_variant:
                raise HTTPException(409, 'Variant differs from declared lot')
            store_measurement(connection, data)
            row = connection.execute('SELECT measurement_id FROM measurements WHERE component_id=? AND epoch_h=?', (data.component_id, data.epoch_h)).fetchone()
    return {'message': 'Measurement stored; analyze the complete lot to produce a result', 'measurement_id': row[0], 'component_id': data.component_id, 'epoch_h': data.epoch_h}


@router.get('/operational/lots', dependencies=[Depends(read_access)])
def list_lots():
    with closing(get_connection()) as connection:
        result = []
        for lot in connection.execute('SELECT * FROM lots ORDER BY created_at DESC LIMIT 200').fetchall():
            item = dict(lot)
            item['registered'] = connection.execute('SELECT COUNT(*) FROM components WHERE lot_id=?', (lot['lot_id'],)).fetchone()[0]
            item['epochs'] = {str(e): connection.execute('SELECT COUNT(*) FROM measurements m JOIN components c ON m.component_id=c.component_id WHERE c.lot_id=? AND m.epoch_h=?', (lot['lot_id'], e)).fetchone()[0] for e in EPOCHS}
            item['runs'] = [dict(r) for r in connection.execute('SELECT run_id,epoch_h,created_at FROM screening_runs WHERE lot_id=? ORDER BY run_id DESC', (lot['lot_id'],))]
            result.append(item)
        return result


@router.post('/operational/lots/{lot_id}/analyze', dependencies=[Depends(write_access)])
def analyze_lot(lot_id: str, data: AnalyzeInput):
    if not runtime_status()['ready']:
        raise HTTPException(503, 'Runtime models unavailable; an administrator must install the verified runtime bundle')
    with closing(get_connection()) as connection:
        with connection:
            connection.execute('BEGIN IMMEDIATE')
            lot = fetch_lot(connection, lot_id)
            try:
                return analyze(connection, lot, data.epoch_h)
            except ValueError as error:
                raise HTTPException(422, str(error))


def get_run(connection, run_id):
    record = connection.execute('SELECT * FROM screening_runs WHERE run_id=?', (run_id,)).fetchone()
    if record is None:
        raise HTTPException(404, 'Analysis run not found')
    result = {'run_id': record['run_id'], 'created_at': record['created_at'], **json.loads(record['payload']),
              'reviews': [dict(r) for r in connection.execute('SELECT * FROM review_actions WHERE run_id=? ORDER BY review_id', (run_id,))],
              'feedback': [dict(r) for r in connection.execute(
                  'SELECT f.* FROM missed_defect_feedback f JOIN screening_runs s ON s.run_id=f.run_id WHERE s.lot_id=? ORDER BY f.feedback_id',
                  (record['lot_id'],))]}
    return attach_prior_alerts(connection, fetch_lot(connection, record['lot_id']), result)


@router.get('/operational/runs/{run_id}', dependencies=[Depends(read_access)])
def run_detail(run_id: int):
    with closing(get_connection()) as connection:
        return get_run(connection, run_id)


@router.get('/operational/runs/{run_id}/export', dependencies=[Depends(read_access)])
def export_run(run_id: int, format: Literal['json', 'csv'] = 'json'):
    with closing(get_connection()) as connection:
        data = get_run(connection, run_id)
    if format == 'json':
        text = json.dumps(data, indent=2, allow_nan=False)
    else:
        stream = io.StringIO()
        columns = ['component_id', 'disposition', 'reason', 'lot_id', 'epoch_h', 'run_id', 'runtime_version', 'input_hash']
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in data['components']:
            writer.writerow({**{k: row[k] for k in columns[:3]}, **{k: data[k] for k in columns[3:]}})
        text = stream.getvalue()
    return Response(text, media_type='application/json' if format == 'json' else 'text/csv',
                    headers={'Content-Disposition': f'attachment; filename="screening_run_{run_id}.{format}"'})


@router.post('/operational/runs/{run_id}/reviews', dependencies=[Depends(write_access)])
def review(run_id: int, data: ReviewInput, request: Request):
    with closing(get_connection()) as connection:
        with connection:
            run = get_run(connection, run_id)
            if data.component_id not in {r['component_id'] for r in run['components']}:
                raise HTTPException(422, 'Component is not part of this run')
            if data.action == 'APPROVE' and run['epoch_h'] != 168:
                raise HTTPException(422, 'Release approval requires the complete 168h run')
            if data.action == 'APPROVE' and next(r for r in run['components'] if r['component_id'] == data.component_id)['disposition'] != 'PASS':
                raise HTTPException(422, 'Release approval requires a 168h PASS decision; record a hold or rejection instead')
            if data.action == 'APPROVE' and any(r['component_id'] == data.component_id and r['status'] != 'DISMISSED' for r in run['feedback']):
                raise HTTPException(409, 'An active missed-defect report blocks approval; investigate or dismiss it with evidence first')
            actor = 'shared_operator' if access_mode() == 'protected' else 'local_demo_operator'
            cur = connection.execute('INSERT INTO review_actions(run_id,component_id,action,reason,actor) VALUES(?,?,?,?,?)',
                                     (run_id, data.component_id, data.action, data.reason, actor))
    return {'review_id': cur.lastrowid, 'message': 'Review recorded; model output is preserved'}


@router.post('/operational/runs/{run_id}/feedback', dependencies=[Depends(write_access)])
def report_miss(run_id: int, data: FeedbackInput):
    with closing(get_connection()) as connection:
        with connection:
            connection.execute('BEGIN IMMEDIATE')
            run = get_run(connection, run_id)
            part = next((p for p in run['components'] if p['component_id'] == data.component_id), None)
            if part is None:
                raise HTTPException(422, 'Component is not part of this run')
            if part['disposition'] not in {'PASS', 'PROVISIONAL_PASS'}:
                raise HTTPException(422, 'Suspected miss reports apply to PASS or PROVISIONAL_PASS; use a standard review for an alerted part')
            if any(f['component_id'] == data.component_id and f['status'] != 'DISMISSED' for f in run['feedback']):
                raise HTTPException(409, 'This component already has an active missed-defect report in its lot')
            try:
                cur = connection.execute('INSERT INTO missed_defect_feedback(run_id,component_id,reported_disposition,suspected_reason,evidence_reference,actor) VALUES(?,?,?,?,?,?)',
                                         (run_id, data.component_id, part['disposition'], data.suspected_reason,
                                          data.evidence_reference, 'shared_operator' if access_mode() == 'protected' else 'local_demo_operator'))
            except sqlite3.IntegrityError:
                raise HTTPException(409, 'This run and component already have a missed-defect report')
    return {'feedback_id': cur.lastrowid, 'status': 'SUSPECTED',
            'message': 'Suspected miss recorded for QA; frozen model output and training artifacts were not changed'}


@router.post('/operational/feedback/{feedback_id}/resolve', dependencies=[Depends(write_access)])
def resolve_feedback(feedback_id: int, data: FeedbackResolution):
    with closing(get_connection()) as connection:
        with connection:
            connection.execute('BEGIN IMMEDIATE')
            record = connection.execute('SELECT * FROM missed_defect_feedback WHERE feedback_id=?', (feedback_id,)).fetchone()
            if record is None:
                raise HTTPException(404, 'Feedback report not found')
            if record['status'] != 'SUSPECTED':
                raise HTTPException(409, 'This report has already been reviewed')
            connection.execute('UPDATE missed_defect_feedback SET status=?,resolution_reason=?,resolved_at=CURRENT_TIMESTAMP WHERE feedback_id=?',
                               (data.status, data.resolution_reason, feedback_id))
    return {'feedback_id': feedback_id, 'status': data.status,
            'message': 'QA annotation saved; no automatic model retraining occurred'}


@router.get('/operational/feedback/export', dependencies=[Depends(read_access)])
def export_feedback():
    with closing(get_connection()) as connection:
        rows = connection.execute('SELECT f.feedback_id,f.run_id,s.lot_id,s.epoch_h,f.component_id,f.reported_disposition,f.status,f.suspected_reason,f.evidence_reference,f.resolution_reason,f.actor,f.created_at,f.resolved_at FROM missed_defect_feedback f JOIN screening_runs s ON s.run_id=f.run_id ORDER BY f.feedback_id').fetchall()
    output = io.StringIO()
    fields = ['feedback_id','run_id','lot_id','epoch_h','component_id','reported_disposition','status',
              'suspected_reason','evidence_reference','resolution_reason','actor','created_at','resolved_at']
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows([dict(r) for r in rows])
    return Response(output.getvalue(), media_type='text/csv',
                    headers={'Content-Disposition': 'attachment; filename="qa_feedback_reports.csv"'})


@router.get('/components/{component_id}', dependencies=[Depends(read_access)])
def component_detail(component_id: str):
    with closing(get_connection()) as connection:
        component = connection.execute('SELECT * FROM components WHERE component_id=?', (component_id,)).fetchone()
        if component is None:
            raise HTTPException(404, 'Operational component not found')
        measurements = [dict(m) for m in connection.execute('SELECT * FROM measurements WHERE component_id=? ORDER BY epoch_h', (component_id,))]
    return {'component': dict(component), 'measurements': measurements, 'measurement_count': len(measurements)}


@router.get('/components/{component_id}/trajectory', dependencies=[Depends(read_access)])
def trajectory(component_id: str):
    detail = component_detail(component_id)
    return {'component_id': component_id, 'measurement_count': detail['measurement_count'], 'trajectory': {
        p: [{'epoch_h': m['epoch_h'], 'value': m[p], 'measured_at': m['measured_at']} for m in detail['measurements']] for p in PARAMS}}


@router.get('/dashboard/summary', dependencies=[Depends(read_access)])
def dashboard_summary():
    with closing(get_connection()) as connection:
        recent = [dict(m) for m in connection.execute('SELECT measurement_id, component_id, epoch_h, measured_at, source FROM measurements ORDER BY measurement_id DESC LIMIT 10')]
        return {'total_components': connection.execute('SELECT COUNT(*) FROM components').fetchone()[0],
                'total_measurements': connection.execute('SELECT COUNT(*) FROM measurements').fetchone()[0],
                'latest_measurement': recent[0] if recent else None, 'recent_measurements': recent,
                'recently_updated_components': [dict(c) for c in connection.execute('SELECT component_id,lot_id,device_variant,updated_at AS latest_measurement_at FROM components ORDER BY updated_at DESC LIMIT 10')]}
