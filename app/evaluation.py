"""Score recorded RAG outputs against a versioned, synthetic evaluation set."""
import argparse
import hashlib
import json
import math
from pathlib import Path

def evaluate(dataset, observations):
    if dataset.get("schema_version") != 1 or not dataset.get("version"):
        raise ValueError("Versioned dataset required")
    cases = dataset.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Nonempty cases required")
    ids = [c["id"] for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate case IDs")
    if not isinstance(observations, list):
        raise ValueError("Observations must be a list")
    observed = [r["id"] for r in observations]
    if len(observed) != len(set(observed)) or set(observed) != set(ids):
        raise ValueError("Exactly one observation per case required")
    by_id = {r["id"]: r for r in observations}
    rows = []
    for case in cases:
        obs = by_id[case["id"]]
        response = obs["response"]
        failures = []
        if response.get("status") != case["expected_status"]:
            failures.append("status")
        answer = response.get("answer", "")
        sources = response.get("sources", [])
        if not isinstance(answer, str) or not isinstance(sources, list):
            raise ValueError("Malformed response")
        source_ids = {s["document_id"] for s in sources}
        allowed = set(case["allowed_documents"])
        if not source_ids <= allowed:
            failures.append("unauthorized_source")
        if not set(case["required_documents"]) <= source_ids:
            failures.append("retrieval_relevance")
        if any(term.casefold() in answer.casefold() for term in case["forbidden_terms"]):
            failures.append("disclosure_or_injection")
        if any(term.casefold() not in answer.casefold() for term in case["required_terms"]):
            failures.append("answer_content")
        if response.get("status") != "answered" and sources:
            failures.append("sources_on_abstention")
        latency = obs.get("latency_ms")
        if latency is not None and (type(latency) not in (int, float) or not math.isfinite(latency) or latency < 0):
            raise ValueError("Invalid latency")
        rows.append({"id": case["id"], "category": case["category"], "passed": not failures,
                     "failures": failures, "latency_ms": latency})
    raw = json.dumps(dataset, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return {"schema_version": 1, "dataset_version": dataset["version"],
            "dataset_sha256": hashlib.sha256(raw).hexdigest(),
            "scope": "recorded-response contract and keyword checks; not semantic correctness certification",
            "total": len(rows), "passed": sum(r["passed"] for r in rows),
            "categories": {cat: {"total": sum(r["category"] == cat for r in rows),
                                "passed": sum(r["category"] == cat and r["passed"] for r in rows)}
                           for cat in sorted({r["category"] for r in rows})},
            "results": rows}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", required=True)
    p.add_argument("--observations", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    report = evaluate(json.loads(Path(a.dataset).read_text(encoding="utf-8")),
                      json.loads(Path(a.observations).read_text(encoding="utf-8")))
    Path(a.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["passed"] == report["total"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
