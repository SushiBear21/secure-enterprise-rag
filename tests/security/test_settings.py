import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))
from rag_service import load_settings

class SettingsTests(unittest.TestCase):
    def test_defaults_and_override(self):
        self.assertEqual(load_settings({})["AWS_REGION"], "us-east-1")
        self.assertEqual(load_settings({"RAG_MODEL_ID": "synthetic-model"})["RAG_MODEL_ID"], "synthetic-model")
    def test_empty_and_unpublished_guardrail_rejected(self):
        for env in ({"RAG_KNOWLEDGE_BASE_ID": ""}, {"RAG_MODEL_ID": " bad "}, {"RAG_GUARDRAIL_VERSION": "DRAFT"}, {"RAG_GUARDRAIL_VERSION": "0"}):
            with self.assertRaises(ValueError): load_settings(env)
