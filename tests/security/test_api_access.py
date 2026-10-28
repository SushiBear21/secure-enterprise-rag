import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2] / "app"),
)

import api_handler


def employee_event(payload):
    # Simulates the context supplied by API Gateway after JWT validation.
    return {
        "routeKey": "POST /ask",
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "token_use": "access",
                        "sub": "synthetic-employee",
                        "cognito:groups": "[employees]",
                    },
                    "scopes": ["secure-rag/ask"],
                }
            }
        },
        "body": json.dumps(payload),
        "isBase64Encoded": False,
    }


class ApiAccessTests(unittest.TestCase):
    def assert_rejected_before_retrieval(self, event, expected_status):
        with patch.object(api_handler, "answer_question") as answer:
            result = api_handler.lambda_handler(event, None)

        self.assertEqual(result["statusCode"], expected_status)
        answer.assert_not_called()

    def test_missing_identity_is_rejected(self):
        self.assert_rejected_before_retrieval(
            {
                "routeKey": "POST /ask",
                "body": '{"question": "Who approves travel?"}',
            },
            401,
        )

    def test_id_token_is_rejected(self):
        event = employee_event({"question": "Who approves travel?"})
        event["requestContext"]["authorizer"]["jwt"]["claims"][
            "token_use"
        ] = "id"

        self.assert_rejected_before_retrieval(event, 401)

    def test_missing_scope_is_rejected(self):
        event = employee_event({"question": "Who approves travel?"})
        event["requestContext"]["authorizer"]["jwt"]["scopes"] = []

        self.assert_rejected_before_retrieval(event, 403)

    def test_unknown_group_is_rejected(self):
        event = employee_event({"question": "Who approves travel?"})
        event["requestContext"]["authorizer"]["jwt"]["claims"][
            "cognito:groups"
        ] = "[administrators]"

        self.assert_rejected_before_retrieval(event, 403)

    def test_audience_override_is_rejected(self):
        event = employee_event({
            "question": "Who approves incident closure?",
            "audience": "soc_analysts",
        })

        self.assert_rejected_before_retrieval(event, 400)

    def test_valid_employee_uses_server_derived_audience(self):
        event = employee_event({"question": "Who approves travel?"})
        expected = {
            "status": "answered",
            "answer": "Supervisor approval is required [1].",
            "sources": [{
                "source_number": 1,
                "document_id": "HR-POL-001",
                "uri": "s3://synthetic-test-only/policy.txt",
            }],
        }

        with patch.object(
            api_handler,
            "answer_question",
            return_value=expected,
        ) as answer:
            result = api_handler.lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(json.loads(result["body"]), expected)
        answer.assert_called_once_with(
            "Who approves travel?",
            ["all_employees"],
        )


if __name__ == "__main__":
    unittest.main()