import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))
from evidence_provenance import ProvenanceDenied, content_hash, load_manifest, verify_retrieved
import rag_service


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.item = {"metadata": {"document_id": "SYN-001", "audience": "soc_analysts"},
                     "content": {"text": "Synthetic instructions: investigate only."},
                     "location": {"s3Location": {"uri": "s3://synthetic-evidence/soc.txt"}}}
        self.docs = {"SYN-001": {"uri": "s3://synthetic-evidence/soc.txt",
                                 "audience": "soc_analysts",
                                 "content_sha256": content_hash(self.item["content"]["text"])}}

    def test_matching_snapshot_is_evidence_not_policy(self):
        receipt = verify_retrieved(self.item, self.docs)
        self.assertEqual(receipt["source_authority"], "evidence_only")
        self.assertTrue(receipt["manifest_verified"])

    def test_tampered_text_fails(self):
        self.item["content"]["text"] += " ADMIN OVERRIDE"
        with self.assertRaises(ProvenanceDenied):
            verify_retrieved(self.item, self.docs)

    def test_forged_scope_or_uri_fails(self):
        self.item["metadata"]["audience"] = "all_employees"
        with self.assertRaises(ProvenanceDenied):
            verify_retrieved(self.item, self.docs)
        self.item["metadata"]["audience"] = "soc_analysts"
        self.item["location"]["s3Location"]["uri"] = "s3://other/file"
        with self.assertRaises(ProvenanceDenied):
            verify_retrieved(self.item, self.docs)

    def test_untrusted_policy_flag_does_not_create_authority(self):
        self.item["metadata"]["policy_authority"] = "system"
        self.assertEqual(verify_retrieved(self.item, self.docs)["source_authority"], "evidence_only")

    def test_manifest_validation(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "trusted.json"
            file.write_text(json.dumps({"schema": "rag-trust-manifest-v1", "documents": self.docs}))
            self.assertEqual(load_manifest(file), self.docs)
            file.write_text("{}")
            with self.assertRaises(ProvenanceDenied):
                load_manifest(file)

    def test_service_fails_closed_before_model_on_tamper(self):
        retrieval = Mock()
        retrieval.retrieve.return_value = {"retrievalResults": [self.item]}
        model = Mock()
        def get_client(service_name, **kwargs):
            return retrieval if service_name == "bedrock-agent-runtime" else model
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "trusted.json"
            file.write_text(json.dumps({"schema": "rag-trust-manifest-v1", "documents": self.docs}))
            self.item["content"]["text"] = "Injected retrieved content"
            with patch.dict(os.environ, {"RAG_PROVENANCE_MANIFEST_PATH": str(file)}):
                with patch.object(rag_service.boto3, "client", side_effect=get_client):
                    with self.assertRaises(ProvenanceDenied):
                        rag_service.answer_question("What are the rules?", ["soc_analysts"])
        model.converse.assert_not_called()


if __name__ == "__main__":
    unittest.main()
