"""
test_integration.py — Complete test suite for SIH26170 application backend.
"""
import sys
import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app
import data_loader

class TestSIH26170Integration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_health_check(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json().get("status"), "ok")

    def test_02_system_status(self):
        res = self.client.get("/api/system/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("fusion_records"), 1343)
        self.assertEqual(data.get("module_a_records_168h"), 1343)
        self.assertEqual(data.get("module_b_records"), 1343)

    def test_03_analysis_summary(self):
        res = self.client.get("/api/analysis/summary")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("total"), 1343)
        self.assertIn("PASS", data.get("by_disposition", {}))
        self.assertIn("MONITOR", data.get("by_disposition", {}))

    def test_04_analysis_search(self):
        res = self.client.get("/api/analysis/search?q=C00158")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(len(data), 1)
        first = data[0]
        self.assertEqual(first.get("component_id"), "C00158")
        self.assertIn("disposition", first)
        self.assertEqual(first.get("fused_verdict"), "PASS")

        # A forecast-only rejection must show the final verdict even when Module A passes.
        forecast = self.client.get("/api/analysis/search?q=C05046").json()[0]
        self.assertEqual(forecast["disposition"], "PASS")
        self.assertEqual(forecast["fused_verdict"], "REJECT")

    def test_05_component_detail_full(self):
        res = self.client.get("/api/analysis/C00158")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("component_id"), "C00158")
        
        # Module A
        mod_a = data.get("module_a", {})
        self.assertIn("disposition", mod_a)
        self.assertIn("score", mod_a)
        self.assertIn("evidence_tier", mod_a)
        
        # Module B
        mod_b = data.get("module_b", {})
        self.assertIn("predictions", mod_b)
        self.assertIn("predicted_IDDQ_168h", mod_b)
        self.assertIn("primary_parameter", mod_b)
        
        # Evidence & Explanation
        evidence = data.get("evidence", {})
        self.assertIn("explanation", evidence)
        self.assertTrue(len(evidence.get("explanation", "")) > 10)
        
        # Historical measurements
        hist = data.get("historical_measurements", [])
        self.assertEqual([row["epoch_h"] for row in hist], [0, 24, 96, 168])
        self.assertAlmostEqual(hist[-1]["IDDQ"], data_loader.holdout_measurements_df.loc["C00158", "IDDQ_168h"])

    def test_06_components_pagination(self):
        res = self.client.get("/api/components?page=1&per_page=20")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("page"), 1)
        self.assertEqual(data.get("per_page"), 20)
        self.assertEqual(len(data.get("data", [])), 20)

    def test_07_models_info(self):
        res = self.client.get("/api/models/info")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("module_a", data)
        self.assertIn("module_b", data)
        self.assertIn("integration", data)
        self.assertEqual(data["integration"].get("status"), "VERIFIED_PASS")

    def test_08b_bounded_literal_search(self):
        self.assertEqual(self.client.get("/api/analysis/search?q=%5B").status_code, 200)
        self.assertEqual(self.client.get("/api/components?q=%5B").status_code, 200)
        self.assertEqual(self.client.get("/api/components?per_page=1000000").status_code, 422)
        self.assertEqual(self.client.get("/api/components?page=0").status_code, 422)

    def test_09_reference_endpoints(self):
        specs_res = self.client.get("/api/reference/specs")
        self.assertEqual(specs_res.status_code, 200)
        
        dict_res = self.client.get("/api/reference/dictionary")
        self.assertEqual(dict_res.status_code, 200)

    def test_10_models_evaluation(self):
        res = self.client.get("/api/models/evaluation")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("baseline", data)
        base = data["baseline"]
        self.assertEqual(base.get("tp"), 65)
        self.assertEqual(base.get("tn"), 1240)
        self.assertEqual(base.get("fp"), 13)
        self.assertEqual(base.get("fn"), 25)
        self.assertAlmostEqual(base.get("f2"), 0.7420, places=3)
        
        self.assertIn("Module A only", base["description"])
        self.assertNotIn("relaxed", data)
        forecasts = data["module_b_forecasts"]
        self.assertEqual(len(forecasts), 6)
        self.assertTrue(all(row["n"] == 1343 for row in forecasts))
        self.assertTrue(all(row["mae"] < row["unchanged_24h_mae"] for row in forecasts))
        self.assertLess(forecasts[0]["upper_coverage"], 0.95)

    def test_11_lots_summary(self):
        res = self.client.get("/api/lots")
        self.assertEqual(res.status_code, 200)
        lots = res.json()
        self.assertEqual(len(lots), 18)
        self.assertEqual(lots[0].get("lot_id"), "A_L03")

    def test_12_pipeline_architecture(self):
        res = self.client.get("/api/pipeline/architecture")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data.get("stages", [])), 7)


if __name__ == "__main__":
    unittest.main()
