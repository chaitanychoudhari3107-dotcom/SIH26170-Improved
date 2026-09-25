import csv
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from operational import operational_db

ROOT = Path(__file__).resolve().parents[1]
class OperationalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = patch.object(operational_db, 'DATABASE_PATH', Path(self.temp.name)/'test.db'); self.db.start()
        self.env = patch.dict('os.environ', {'SIH26170_OPERATOR_KEY':'test-operator','SIH26170_ENABLE_DEMO_WRITES':'0'}); self.env.start()
        self.client=TestClient(app, headers={'Authorization':'Bearer test-operator'})
    def tearDown(self):
        self.env.stop(); self.db.stop(); self.temp.cleanup()
    def payload(self, epoch=24):
        text=(ROOT/f'frontend/public/demo/DEMO_A_{epoch}h.csv').read_text()
        return dict(csv_text=text,lot_id='DEMO_A',device_variant='CMOS_A',expected_count=len(list(csv.DictReader(io.StringIO(text)))),epoch_h=epoch)
    def post(self,url,data,status=200):
        r=self.client.post('/api/operational/'+url,json=data)
        self.assertEqual(r.status_code,status,r.text[:1500]);return r.json()
    def test_read_only_default_blocks_writes(self):
        with patch.dict('os.environ', {'SIH26170_OPERATOR_KEY':'','SIH26170_ENABLE_DEMO_WRITES':'0'}):
            self.assertEqual(self.client.get('/api/operational/config').json()['mode'],'read_only')
            self.post('import',self.payload(),403)
    def test_request_limit_and_readiness(self):
        result=self.client.post('/api/operational/import',content=b'x'*2_100_001,headers={'Content-Type':'application/json'})
        self.assertEqual(result.status_code,413)
        self.assertEqual(self.client.get('/api/health').status_code,200)
    def test_historical_breach_is_not_erased(self):
        p=self.payload(168)
        rows=list(csv.DictReader(io.StringIO(p['csv_text'])))
        rows[0]['IDDQ_0h']='1000'
        stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
        self.post('import',{**p,'csv_text':stream.getvalue()})
        result=self.post('lots/DEMO_A/analyze',{'epoch_h':168})
        row=next(r for r in result['components'] if r['component_id']==rows[0]['component_id'])
        self.assertEqual(row['disposition'],'REJECT')
        self.assertIn('IDDQ',row['observed_breaches'])
    def test_auth_and_preview_rollback(self):
        self.assertEqual(TestClient(app).get('/api/operational/lots').status_code,401)
        self.assertEqual(TestClient(app).post('/api/operational/import',json=self.payload()).status_code,401)
        self.post('import/validate',self.payload())
        self.assertEqual(self.client.get('/api/operational/lots').json(),[])
    def test_incomplete_and_conflicting_imports(self):
        p=self.payload();p['csv_text']='\n'.join(p['csv_text'].splitlines()[:3])+'\n'
        self.post('import',p)
        self.post('lots/DEMO_A/analyze',{'epoch_h':24},422)
        original=self.payload();self.post('import',original)
        self.assertEqual(self.post('import',original)['inserted_measurements'],0)
        lines=original['csv_text'].splitlines();cells=lines[1].split(',');cells[4]='1234';lines[1]=','.join(cells)
        self.post('import',{**original,'csv_text':'\n'.join(lines)},409)
        self.post('import',{**original,'expected_count':original['expected_count']+1},409)
    def test_schema_future_labels_nonfinite(self):
        p=self.payload();self.post('import',{**p,'epoch_h':0},422)
        lines=p['csv_text'].splitlines();cells=lines[1].split(',');cells[4]='NaN';lines[1]=','.join(cells)
        self.post('import',{**p,'csv_text':'\n'.join(lines)},422)
        self.assertEqual(self.client.get('/api/operational/lots').json(),[])
    def test_complete_lifecycle_immutable_forecast_review_export(self):
        p=self.payload();self.post('import',p)
        first=self.post('lots/DEMO_A/analyze',{'epoch_h':24})
        again=self.post('lots/DEMO_A/analyze',{'epoch_h':24});self.assertEqual(first['run_id'],again['run_id'])
        self.assertTrue(again['reused'])
        cid=first['components'][0]['component_id']
        self.post(f"runs/{first['run_id']}/reviews",dict(component_id=cid,action='APPROVE',reason='Review at early epoch'),422)
        self.post('import',self.payload(168))
        last=self.post('lots/DEMO_A/analyze',{'epoch_h':168})
        self.assertEqual(first['forecast_receipt']['forecast_id'],last['forecast_receipt']['forecast_id'])
        self.assertEqual(first['components'][0]['module_b'],last['components'][0]['module_b'])
        self.post(f"runs/{last['run_id']}/reviews",dict(component_id=cid,action='ACKNOWLEDGE',reason='Reviewed full measurement evidence'))
        exported=self.client.get(f"/api/operational/runs/{last['run_id']}/export").json()
        self.assertEqual(len(exported['reviews']),1)
        self.assertEqual(len(exported['components']),p['expected_count'])
        self.assertEqual(exported['model_provenance']['release_state'],'RESEARCH_PROTOTYPE')
        self.assertEqual(self.client.get(f"/api/operational/runs/{last['run_id']}/export?format=csv").status_code,200)
