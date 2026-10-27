import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2] / "app"),
)

import rag_service


class RetrievalBoundaryTests(unittest.TestCase):
    def test_employee_cannot_pass_soc_evidence_to_model(self):
        retrieval_client = Mock()
        retrieval_client.retrieve.return_value = {
            "retrievalResults": [{
                "content": {"text": "Restricted synthetic SOC content."},
                "metadata": {
                    "document_id": "HR-SOC-001",
                    "audience": "soc_analysts",
                },
                "location": {
                    "s3Location": {
                        "uri": "s3://synthetic-test-only/soc.txt"
                    }
                },
            }]
        }

        model_client = Mock()

        def client_for_test(service_name, **kwargs):
            if service_name == "bedrock-agent-runtime":
                return retrieval_client
            if service_name == "bedrock-runtime":
                return model_client
            raise AssertionError("Unexpected AWS service.")

        with patch.object(
            rag_service.boto3,
            "client",
            side_effect=client_for_test,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "Retrieved document failed access check",
            ):
                rag_service.answer_question(
                    "Who approves incident closure?",
                    ["all_employees"],
                )

        model_client.converse.assert_not_called()


if __name__ == "__main__":
    unittest.main()