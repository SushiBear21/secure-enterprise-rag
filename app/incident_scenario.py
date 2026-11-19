"""Run the RAG incident response exercise with fixture-bound AWS mocks."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from app import rag_service
from app.authorization import allowed_audiences
from app.incident_response import Incident, digest, verify_timeline


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "incident"
BASELINE_DOCUMENTS = ("remote-access-policy.txt", "incident-response-runbook.txt")
QUESTION = "What are the requirements in the selected training document?"
SUSPECT = "HR-LAB-IR-001"
BASELINE_CONFIG = {
    "revision": "lab-known-good-v1",
    "result_limit": 3,
    "policy": "audience_filter_with_pre_model_check",
}


def read_fixture(path):
    return json.loads(path.read_text(encoding="utf-8"))


def snapshots():
    documents = []
    for filename in BASELINE_DOCUMENTS:
        path = ROOT / "data" / "synthetic" / filename
        attributes = read_fixture(path.with_suffix(".txt.metadata.json"))["metadataAttributes"]
        documents.append({
            "id": attributes["document_id"]["value"]["stringValue"],
            "version": attributes["version"]["value"]["stringValue"],
            "audience": attributes["audience"]["value"]["stringValue"],
            "text": path.read_text(encoding="utf-8"),
        })
    known_good = {"config": BASELINE_CONFIG, "documents": documents}
    suspect = read_fixture(FIXTURES / "suspect-document.json")
    observed = {"config": {**BASELINE_CONFIG, "revision": "lab-observed-v2"}, "documents": [*documents, suspect]}
    return known_good, observed


class OfflineRag:
    """Synthetic index adapter. RAG authorization and response checks run as written."""
    def __init__(self, snapshot, retrieval_open):
        self.snapshot = snapshot
        self.retrieval_open = retrieval_open

    def ask(self, selected_id, groups, *, output="valid", inject_backend_fault=False):
        audiences = allowed_audiences(groups)
        retrieval, model = Mock(), Mock()
        observed_documents = []

        def retrieve(**request):
            if not self.retrieval_open:
                raise RuntimeError("Exercise retrieval paused")
            config = request["retrievalConfiguration"]["vectorSearchConfiguration"]
            if config["numberOfResults"] != self.snapshot["config"]["result_limit"]:
                raise RuntimeError("Fixture index configuration mismatch")
            spec = config["filter"]
            filtered = {item["equals"]["value"] for item in spec.get("orAll", [spec])}
            if filtered != set(audiences):
                raise RuntimeError("Unexpected audience filter")
            selected = [doc for doc in self.snapshot["documents"] if doc["id"] == selected_id
                        and (inject_backend_fault or doc["audience"] in filtered)]
            observed_documents.extend(doc["id"] for doc in selected)
            return {"retrievalResults": [{
                "content": {"text": doc["text"]},
                "metadata": {"document_id": doc["id"], "audience": doc["audience"]},
                "location": {"s3Location": {"uri": f"s3://fictional-incident-fixture/{doc['id']}.txt"}},
            } for doc in selected]}

        def converse(**request):
            if selected_id == SUSPECT:
                message = request["messages"][0]["content"][0]["guardContent"]["text"]["text"]
                if "IR-SIM-001" not in message:
                    raise RuntimeError("Exercise source marker missing from guarded context")
                return {"stopReason": "guardrail_intervened"}
            content = "Training requirements apply [1]." if output == "valid" else "Unverified statement [99]."
            return {"stopReason": "end_turn", "output": {"message": {"content": [{"text": content}]}}}

        def client(service, **kwargs):
            return {"bedrock-agent-runtime": retrieval, "bedrock-runtime": model}[service]

        retrieval.retrieve.side_effect = retrieve
        model.converse.side_effect = converse
        with patch.object(rag_service.boto3, "client", side_effect=client):
            try:
                response = rag_service.answer_question(QUESTION, audiences)
            except RuntimeError as error:
                return {"error": str(error), "model_boundary_calls": model.converse.call_count,
                        "retrieved_document_ids": observed_documents}
        return {"response": response, "model_boundary_calls": model.converse.call_count,
                "retrieved_document_ids": observed_documents}


def case_rag(lab, snapshot):
    case = lab.report()
    require(digest(snapshot) == case["active_snapshot_sha256"], "Requested snapshot is not active")
    return OfflineRag(snapshot, case["retrieval_open"])


def recovery_retests(snapshot):
    # Isolated validation against the recovered snapshot while public demo retrieval stays paused.
    rag = OfflineRag(snapshot, retrieval_open=True)
    public = rag.ask("HR-POL-001", ["employees"])["response"]
    soc = rag.ask("HR-SOC-001", ["soc_analysts"])["response"]
    denied = rag.ask("HR-SOC-001", ["employees"], inject_backend_fault=True)
    invalid = rag.ask("HR-POL-001", ["employees"], output="invalid")
    suspect = rag.ask(SUSPECT, ["employees"])
    return {
        "employee_public": public["status"] == "answered" and [s["document_id"] for s in public["sources"]] == ["HR-POL-001"],
        "soc_authorized": soc["status"] == "answered" and [s["document_id"] for s in soc["sources"]] == ["HR-SOC-001"],
        "restricted_rejected_before_model": denied.get("error") == "Retrieved document failed access check."
        and denied["retrieved_document_ids"] == ["HR-SOC-001"] and denied["model_boundary_calls"] == 0,
        "invalid_citation_rejected": invalid.get("error") == "Model returned invalid source references."
        and invalid["model_boundary_calls"] == 1,
        "suspect_absent": suspect["response"]["status"] == "insufficient_evidence"
        and not suspect["response"]["sources"] and not suspect["retrieved_document_ids"]
        and suspect["model_boundary_calls"] == 0,
        "snapshot_verified": digest(snapshot) == read_fixture(FIXTURES / "baseline.json")["snapshot_sha256"],
    }


def alert_for(snapshot):
    result = OfflineRag(snapshot, retrieval_open=True).ask(SUSPECT, ["employees"])
    response = result["response"]
    suspect = next(doc for doc in snapshot["documents"] if doc["id"] == SUSPECT)
    return {
        "synthetic": True, "alert_id": "RAG-IR-001", "request_id": "LAB-REQ-001",
        "signal": "suspected_indirect_prompt_injection", "guardrail_result": response["status"],
        "document_id": suspect["id"], "document_sha256": digest(suspect),
        "released_citations": len(response["sources"]),
    }


class ExerciseClock:
    def __init__(self):
        self.value = int(datetime(2026, 11, 19, 18, tzinfo=timezone.utc).timestamp())

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def rehearse(db_path):
    baseline, observed = snapshots()
    baseline_sha = read_fixture(FIXTURES / "baseline.json")["snapshot_sha256"]
    require(digest(baseline) == baseline_sha, "Committed baseline snapshot digest mismatch")
    clock = ExerciseClock()
    lab = Incident(db_path, clock, baseline_sha)
    alert = alert_for(observed)
    first = lab.ingest(alert, observed)
    duplicate = lab.ingest(alert, observed)
    require(first["created"] and not duplicate["created"] and first["case_id"] == duplicate["case_id"],
            "Duplicate delivery did not preserve the case")
    clock.advance(45)
    lab.triage()

    def authorize(action, rationale, snapshot=None):
        key = lab.propose(action)
        require(lab.execute(key, snapshot) == "denied", f"Unapproved {action} was not denied")
        clock.advance(5)
        lab.approve(key, key, rationale)
        require(lab.execute(key, snapshot) == "executed", f"Approved {action} failed")
        require(lab.execute(key, snapshot) == "already_executed", f"{action} replay was not idempotent")

    clock.advance(70)
    authorize("pause_retrieval", "Escalate to the RAG owner and pause retrieval while validating the index.")
    blocked = case_rag(lab, observed).ask("HR-POL-001", ["employees"])
    require(blocked.get("error") == "Exercise retrieval paused" and blocked["model_boundary_calls"] == 0,
            "A paused endpoint reached model inference")
    clock.advance(175)
    authorize("restore_snapshot", "Restore the pinned index membership and configuration while retrieval stays paused.", baseline)
    clock.advance(60)
    require(lab.validate_recovery(recovery_retests, baseline), "Recovery retests failed")
    clock.advance(10)
    authorize("resume_retrieval",
              "All retests passed. A changed snapshot or validation receipt invalidates this decision.")
    case = lab.report()
    verify_timeline(case["timeline"])
    resumed = case_rag(lab, baseline).ask("HR-POL-001", ["employees"])
    require(resumed["response"]["status"] == "answered", "Post-resume request failed")
    times = {row["kind"]: row["at_epoch"] for row in case["timeline"]}
    return {
        "scope": "offline_simulation", "approval_mode": "scripted_commander_roles", "aws_calls": 0,
        "time_basis": "scripted_scenario_clock", "case_count": 1, "duplicate_delivery": duplicate,
        "case": case, "phase_seconds": {
            "detection_to_triage": times["triaged"] - times["detected"],
            "detection_to_simulated_containment": times["paused"] - times["detected"],
            "containment_to_validated_recovery": times["validated"] - times["paused"],
            "validated_recovery_to_resume": times["resumed"] - times["validated"],
        },
        "paused_request_blocked_before_model": True, "post_resume_authorized_request_passed": True,
        "corrective_action": {
            "issue": "https://github.com/SushiBear21/secure-enterprise-rag/issues/3",
            "owner_role": "RAG ingestion owner", "status": "lab_retest_passed_owner_review_pending",
            "acceptance_test": "The recovered baseline must exclude the retired suspect document before model invocation.",
            "retest": case["retests"]["suspect_absent"],
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--response-lab", type=Path)
    parser.add_argument("--control-tower", type=Path)
    args = parser.parse_args()
    if bool(args.response_lab) != bool(args.control_tower):
        parser.error("Supply both companion checkout paths together")
    with TemporaryDirectory(prefix="rag-incident-") as work:
        evidence = rehearse(Path(work) / "case.sqlite")
    if args.response_lab:
        from app.incident_companions import integrate
        evidence["companion_checks"] = integrate(evidence["case"], args.response_lab, args.control_tower)
    body = json.dumps(evidence, indent=2) + "\n"
    if args.output:
        args.output.write_text(body, encoding="utf-8")
        print(f"Incident exercise passed. Evidence at {args.output}")
    else:
        print(body, end="")


if __name__ == "__main__":
    main()
