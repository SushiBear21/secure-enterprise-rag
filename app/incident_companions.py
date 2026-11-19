"""Replay the exercise handoffs through pinned offline companion source."""
import json
import subprocess
import sys

from app.incident_response import SOURCE


RESPONSE_SHA = "7018def69bf97feda639e76cfc880e4f92f8b0f0"
TOWER_SHA = "a7f5c38ad62f14eddb298ca546abd76ddd6a82f8"

# Separate processes keep the three repositories' app module namespaces apart.
ROUTE = """
import hashlib
import json
import sys
from app.finding_router import routing_evidence
from app.response import canonical, require_approved_action, verify_payload

data = json.load(sys.stdin)
identity, event, _ = routing_evidence(data["alert"], data["finding"])
key = data["pause_digest"]
proposal = {"state": "PENDING", "payload_json": canonical(data["pause"]), "payload_sha256": key}
verify_payload(proposal)
try:
    require_approved_action(proposal, data["approval_at"], "triaged", "triaged")
except ValueError:
    pending_denied = True
else:
    raise RuntimeError("SOAR approval gate accepted unapproved request")
proposal.update(state="APPROVED", approved_sha256=key, expires_at=data["expires"])
require_approved_action(proposal, data["approval_at"], "triaged", "triaged")
print(json.dumps({"case_id": identity, "alert_sha256": hashlib.sha256(event).hexdigest(),
                  "pending_denied": pending_denied, "exact_approval_accepted": True}))
"""

TICKET = """
import json
import sys
from tower.core import empty, transition, verify

data = json.load(sys.stdin)
at = data["at"]
state, _ = transition(empty(), "ingest", {"findings": [data["finding"]]}, "lab-analyst", at)
state, key = transition(state, "propose", {
    "id": data["finding"]["id"], "draft": data["draft"], "provider": "reference_fixture",
}, "lab-rag-owner", at)
try:
    transition(state, "execute", {"id": key}, "lab-operator", at)
except ValueError:
    pending_denied = not state["tickets"]
else:
    raise RuntimeError("Control Tower created a ticket before approval")
state, _ = transition(state, "approve", {
    "id": key, "sha256": key, "effort_seconds": 0,
}, "lab-incident-commander", at + 1)
state, created = transition(state, "execute", {"id": key}, "lab-operator", at + 2)
state, replay = transition(state, "execute", {"id": key}, "lab-operator", at + 3)
verify(state)
print(json.dumps({"ticket_id": key, "ticket_count": len(state["tickets"]), "status": state["tickets"][key]["status"],
                  "pending_denied": pending_denied, "result": created, "replay": replay}))
"""


def replay(repo, sha, script, payload):
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True, text=True,
                          capture_output=True, timeout=10).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=repo, check=True, text=True,
                           capture_output=True, timeout=10).stdout
    if head != sha or dirty:
        raise ValueError(f"Expected a clean companion checkout at {sha}")
    result = subprocess.run([sys.executable, "-B", "-c", script], cwd=repo, input=json.dumps(payload),
                            text=True, capture_output=True, timeout=30)
    if result.returncode:
        raise RuntimeError(f"Companion exercise failed at {sha}: {result.stderr.strip()}")
    return {"source_revision": sha, **json.loads(result.stdout)}


def integrate(case, response_lab, control_tower):
    key, pause = next((key, p) for key, p in case["proposals"].items() if p["payload"]["action"] == "pause_retrieval")
    alert = case["alert"]
    router = replay(response_lab, RESPONSE_SHA, ROUTE, {
        "alert": alert, "finding": {"source": SOURCE, "finding_id": alert["alert_id"]},
        "pause": pause["payload"], "pause_digest": key, "approval_at": pause["approval"]["at"],
        "expires": pause["approval"]["expires"],
    })
    if (router["case_id"], router["alert_sha256"]) != (case["case_id"], case["alert_sha256"]):
        raise RuntimeError("Companion router did not match the case or alert digest")

    finding = {
        "id": alert["alert_id"], "synthetic": True, "kind": "security", "category": "benign",
        "title": "Verify retired RAG document is excluded after recovery", "owner": "RAG ingestion owner",
        "likelihood": 2, "impact": 3, "milestone": "Exercise follow-up", "due": "2026-12-03",
        "dependencies": [], "evidence": f"Offline RAG case {case['case_id']}, alert SHA-256 {case['alert_sha256']}",
        "expected_positive": False,
    }
    ticket = replay(control_tower, TOWER_SHA, TICKET, {
        "finding": finding, "at": case["timeline"][-1]["at_epoch"],
        "draft": "Retest the restored index with the retired document ID. Require zero model calls and no source citations.",
    })
    if (ticket["ticket_count"], ticket["pending_denied"], ticket["result"], ticket["replay"]) != (
            1, True, "executed", "already_executed"):
        raise RuntimeError("Companion ticket approval or replay did not match expectations")
    return {"soar_router": router, "control_tower": ticket}
