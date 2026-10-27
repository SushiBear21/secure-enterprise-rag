import base64
import binascii
import json
import re

from botocore.exceptions import BotoCoreError, ClientError

from authorization import AccessDenied, allowed_audiences
from rag_service import answer_question


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(body),
    }


def parse_groups(value):
    if isinstance(value, list):
        return value

    if not isinstance(value, str) or not value.strip():
        raise AccessDenied("Missing groups.")

    value = value.strip()

    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        if value.startswith("[") and value.endswith("]"):
            value = value[1:-1]

        groups = [item.strip() for item in value.split(",")]

        if not all(
            re.fullmatch(r"[A-Za-z0-9_-]+", group)
            for group in groups
        ):
            raise AccessDenied("Malformed groups.")

        return groups

    if not isinstance(decoded, list):
        raise AccessDenied("Malformed groups.")

    return decoded


def lambda_handler(event, context):
    # Identity comes only from API Gateway's JWT authorizer.
    try:
        jwt = event["requestContext"]["authorizer"]["jwt"]
        claims = jwt["claims"]

        if claims.get("token_use") != "access":
            return response(401, {"error": "Access token required."})

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            return response(401, {"error": "Missing identity."})

        scopes = jwt.get("scopes", [])
        if not isinstance(scopes, list) or "secure-rag/ask" not in scopes:
            return response(403, {"error": "Required scope missing."})

        groups = parse_groups(claims.get("cognito:groups"))
        audiences = allowed_audiences(groups)

    except AccessDenied:
        return response(403, {"error": "No permitted document access."})
    except (KeyError, TypeError, AttributeError):
        return response(401, {"error": "Verified identity required."})

    route = event.get("routeKey")

    if route == "GET /whoami":
        return response(200, {
            "user_id": subject,
            "allowed_audiences": audiences,
        })

    if route != "POST /ask":
        return response(404, {"error": "Route not found."})

    try:
        body = event.get("body", "")

        if not isinstance(body, str) or len(body) > 16000:
            raise ValueError("Invalid request body.")

        if event.get("isBase64Encoded"):
            body = base64.b64decode(body, validate=True).decode("utf-8")

        payload = json.loads(body)

        # Reject attempts to supply audience, groups, or other settings.
        if not isinstance(payload, dict) or set(payload) != {"question"}:
            raise ValueError("Only a question is accepted.")

        question = payload["question"]
        if not isinstance(question, str):
            raise ValueError("Question must be text.")

        question = question.strip()
        if not 1 <= len(question) <= 1000:
            raise ValueError("Question must contain 1–1000 characters.")

    except (ValueError, UnicodeError, binascii.Error):
        return response(400, {
            "error": "Send only a question containing 1–1000 characters."
        })

    try:
        result = answer_question(question, audiences)
    except (BotoCoreError, ClientError, RuntimeError, ValueError, KeyError):
        # Do not log tokens, questions, or retrieved document content.
        return response(502, {
            "error": "Unable to produce a verified answer. Try again later."
        })

    return response(200, result)