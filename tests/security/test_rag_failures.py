import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2] / "app"),
)

import rag_service


class RagFailureTests(unittest.TestCase):
    def setUp(self):
        self.retrieval = Mock()
        self.model = Mock()

        self.retrieval.retrieve.return_value = {
            "retrievalResults": [{
                "content": {
                    "text": "Supervisor approval is required for travel."
                },
                "metadata": {
                    "document_id": "HR-POL-001",
                    "audience": "all_employees",
                },
                "location": {
                    "s3Location": {
                        "uri": "s3://synthetic-test-only/policy.txt"
                    }
                },
            }]
        }

        def client_for_test(service_name, **kwargs):
            if service_name == "bedrock-agent-runtime":
                return self.retrieval
            if service_name == "bedrock-runtime":
                return self.model
            raise AssertionError("Unexpected AWS service.")

        patcher = patch.object(
            rag_service.boto3,
            "client",
            side_effect=client_for_test,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def ask(self):
        return rag_service.answer_question(
            "Who approves travel?",
            ["all_employees"],
        )

    def set_model_answer(self, text, stop_reason="end_turn"):
        self.model.converse.return_value = {
            "stopReason": stop_reason,
            "output": {
                "message": {
                    "content": [{"text": text}]
                }
            },
        }

    def test_guardrail_block_returns_no_sources(self):
        self.set_model_answer(
            "Blocked content must not be returned.",
            "guardrail_intervened",
        )

        result = self.ask()

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["sources"], [])
        self.assertNotIn(
            "Blocked content must not be returned.",
            result["answer"],
        )

    def test_model_service_failure_has_no_unguarded_retry(self):
        self.model.converse.side_effect = ClientError(
            {
                "Error": {
                    "Code": "AccessDeniedException",
                    "Message": "Synthetic test failure",
                }
            },
            "Converse",
        )

        with self.assertRaises(ClientError):
            self.ask()

        self.model.converse.assert_called_once()
        request = self.model.converse.call_args.kwargs
        self.assertEqual(
            request["guardrailConfig"]["guardrailIdentifier"],
            rag_service.GUARDRAIL_ID,
        )
        self.assertEqual(
            request["guardrailConfig"]["guardrailVersion"],
            rag_service.GUARDRAIL_VERSION,
        )

    def test_retrieval_failure_never_calls_model(self):
        self.retrieval.retrieve.side_effect = ClientError(
            {
                "Error": {
                    "Code": "InternalServerException",
                    "Message": "Synthetic retrieval failure",
                }
            },
            "Retrieve",
        )

        with self.assertRaises(ClientError):
            self.ask()

        self.model.converse.assert_not_called()

    def test_empty_retrieval_skips_model(self):
        self.retrieval.retrieve.return_value = {
            "retrievalResults": []
        }

        result = self.ask()

        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["sources"], [])
        self.model.converse.assert_not_called()

    def test_truncated_answer_is_rejected(self):
        self.set_model_answer(
            "Supervisor approval [1]",
            "max_tokens",
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "did not finish normally",
        ):
            self.ask()

    def test_nonexistent_citation_is_rejected(self):
        self.set_model_answer("Supervisor approval is required [99].")

        with self.assertRaisesRegex(
            RuntimeError,
            "invalid source references",
        ):
            self.ask()


if __name__ == "__main__":
    unittest.main()