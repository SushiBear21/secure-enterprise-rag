import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))
from evaluation import evaluate

class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((Path(__file__).resolve().parents[1] / "evaluation/security-v1.json").read_text())
        self.rows = [{"id": c["id"], "response": {"status": c["expected_status"],
                     "answer": " ".join(c["required_terms"]),
                     "sources": [{"document_id": x} for x in c["required_documents"]]}} for c in self.data["cases"]]
    def test_complete_contract(self):
        report = evaluate(self.data, self.rows)
        self.assertEqual(report["passed"], 6)
        self.assertIsNone(report["results"][0]["latency_ms"])
    def test_missing_and_duplicate_results_rejected(self):
        for rows in (self.rows[:-1], self.rows + self.rows[:1]):
            with self.assertRaises(ValueError): evaluate(self.data, rows)
    def test_disclosure_and_irrelevant_sources_fail(self):
        self.rows[2]["response"].update(answer="SYNTHETIC-SECRET", sources=[{"document_id": "SECRET"}])
        report = evaluate(self.data, self.rows)
        self.assertEqual(report["passed"], 5)
        self.assertIn("unauthorized_source", report["results"][2]["failures"])
        self.assertIn("disclosure_or_injection", report["results"][2]["failures"])
    def test_wrong_answer_and_missing_retrieval_fail(self):
        self.rows[0]["response"].update(answer="invented", sources=[])
        self.assertEqual(set(evaluate(self.data, self.rows)["results"][0]["failures"]),
                         {"answer_content", "retrieval_relevance"})
    def test_nonfinite_measurement_rejected(self):
        self.rows[0]["latency_ms"] = float("nan")
        with self.assertRaises(ValueError): evaluate(self.data, self.rows)
