import json
import re
import sys
import time
from datetime import datetime, timezone

from evaluate_employee import PROJECT_ROOT, request_api
from login import login


def check_answer(body, document_id, required_terms):
    if body.get("status") != "answered":
        raise AssertionError("Expected an answered response")

    answer = body.get("answer", "")
    sources = body.get("sources", [])

    if not isinstance(answer, str) or not isinstance(sources, list):
        raise AssertionError("Invalid answer or sources")

    for term in required_terms:
        if term not in answer.lower():
            raise AssertionError(f"Expected answer term: {term}")

    if not sources or any(
        source.get("document_id") != document_id
        for source in sources
    ):
        raise AssertionError("Missing or unexpected source document")

    numbers = {source.get("source_number") for source in sources}
    cited = {int(value) for value in re.findall(r"\[(\d+)\]", answer)}

    if not cited or not cited.issubset(numbers):
        raise AssertionError("Missing or invalid citations")


def main():
    print("Sign in as soc-demo.")
    token = login()
    results = []

    try:
        code, identity = request_api("/whoami", token)
        if (
            code != 200
            or identity.get("allowed_audiences")
            != ["all_employees", "soc_analysts"]
        ):
            print("STOP: SOC identity required.")
            return 1

        cases = [
            {
                "id": "soc_closure",
                "question": (
                    "Who approves incident closure and "
                    "what documentation is required?"
                ),
                "document": "HR-SOC-001",
                "terms": ["incident manager", "documentation", "phase"],
            },
            {
                "id": "soc_general_policy",
                "question": "Who approves travel with equipment?",
                "document": "HR-POL-001",
                "terms": ["supervisor"],
            },
            {
                "id": "soc_acquisition_exclusion",
                "question": "Who approves vendor access and when does it expire?",
                "document": None,
                "terms": [],
            },
        ]

        for case in cases:
            started = time.perf_counter()
            failure = None

            try:
                code, body = request_api(
                    "/ask",
                    token,
                    {"question": case["question"]},
                )

                if code != 200:
                    raise AssertionError(f"Expected HTTP 200; got {code}")

                if case["document"]:
                    check_answer(body, case["document"], case["terms"])
                elif (
                    body.get("status") != "insufficient_evidence"
                    or body.get("sources") != []
                ):
                    raise AssertionError(
                        "Expected insufficient evidence and empty sources"
                    )

            except AssertionError as error:
                failure = str(error)
            except Exception as error:
                failure = f"Request failed: {type(error).__name__}"

            record = {
                "case": case["id"],
                "passed": failure is None,
                "duration_ms": round(
                    (time.perf_counter() - started) * 1000, 2
                ),
            }
            if failure:
                record["failure"] = failure

            results.append(record)
            print(
                f"{'PASS' if failure is None else 'FAIL'}: {case['id']}"
                + (f" | {failure}" if failure else "")
            )

    finally:
        del token

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "suite": "live_soc",
        "passed": sum(item["passed"] for item in results),
        "total": len(results),
        "results": results,
    }

    path = PROJECT_ROOT / "tests/evaluation/live-soc-results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\n{report['passed']}/{report['total']} passed")
    print(f"Report: {path}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    sys.exit(main())