import json
import time

from api_handler import lambda_handler as handle_request
from api_handler import response


def lambda_handler(event, context):
    started = time.perf_counter()
    error_type = None

    try:
        result = handle_request(event, context)
    except Exception as error:
        # Record the exception class, not its potentially sensitive message.
        error_type = type(error).__name__
        result = response(500, {"error": "Internal application error."})

    status_code = result["statusCode"]

    if status_code >= 500:
        outcome = "application_error"
    elif status_code == 401:
        outcome = "unauthorized"
    elif status_code == 403:
        outcome = "forbidden"
    elif status_code == 400:
        outcome = "invalid_request"
    elif status_code == 404:
        outcome = "not_found"
    else:
        outcome = "success"
        try:
            body = json.loads(result["body"])
            candidate = body.get("status")
            if candidate in {
                "answered",
                "blocked",
                "insufficient_evidence",
            }:
                outcome = candidate
        except (ValueError, TypeError, AttributeError):
            pass

    request_context = event.get("requestContext", {})
    route = event.get("routeKey")
    if route not in {"GET /whoami", "POST /ask"}:
        route = "unknown"

    record = {
        "event": "request_completed",
        "lambda_request_id": context.aws_request_id,
        "api_request_id": request_context.get("requestId"),
        "route": route,
        "status_code": status_code,
        "outcome": outcome,
        "duration_ms": round(
            (time.perf_counter() - started) * 1000, 2
        ),
    }

    if error_type:
        record["error_type"] = error_type

    print(json.dumps(record))
    return result