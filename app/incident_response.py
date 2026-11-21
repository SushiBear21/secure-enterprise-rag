"""SQLite case and approval workflow for a single offline RAG exercise."""
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import json
import sqlite3


SOURCE = "rag-incident-lab"
APPROVAL_TTL = 600
TRANSITIONS = {
    "pause_retrieval": ("triaged", "paused"),
    "restore_snapshot": ("paused", "recovered"),
    "resume_retrieval": ("validated", "resumed"),
}
REQUIRED_RETESTS = {
    "employee_public", "soc_authorized", "restricted_rejected_before_model",
    "invalid_citation_rejected", "suspect_absent", "snapshot_verified",
}
ACTORS = {
    "analyst": "lab-analyst",
    "commander": "lab-incident-commander",
    "operator": "lab-operator",
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def route_id(alert):
    return hashlib.sha256(f"{SOURCE}|{alert['alert_id']}".encode()).hexdigest()


def event(state, kind, actor, at, details):
    timeline = state["timeline"]
    if timeline and at < timeline[-1]["at_epoch"]:
        raise ValueError("Exercise time cannot move backward")
    row = {
        "sequence": len(timeline), "kind": kind, "actor": actor, "at_epoch": at,
        "at": datetime.fromtimestamp(at, timezone.utc).isoformat(),
        "details": details, "previous": timeline[-1]["sha256"] if timeline else "0" * 64,
    }
    timeline.append({**row, "sha256": digest(row)})


def verify_timeline(timeline):
    previous = "0" * 64
    for index, row in enumerate(timeline):
        body = {key: value for key, value in row.items() if key != "sha256"}
        if row["sequence"] != index or row["previous"] != previous or digest(body) != row["sha256"]:
            raise ValueError("Case timeline integrity mismatch")
        previous = row["sha256"]


class Incident:
    def __init__(self, path, clock, baseline_sha256):
        self.path = path
        self.clock = clock
        self.baseline_sha256 = baseline_sha256
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS incident (slot INTEGER PRIMARY KEY CHECK(slot=1), state TEXT NOT NULL)")

    @contextmanager
    def transaction(self):
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT state FROM incident WHERE slot=1").fetchone()
            state = json.loads(row[0]) if row else {}
            if state:
                verify_timeline(state["timeline"])
                if digest(state["alert"]) != state["alert_sha256"]:
                    raise ValueError("Alert digest mismatch")
                if state["baseline_sha256"] != self.baseline_sha256:
                    raise ValueError("Exercise baseline changed")
            yield state
            if state:
                db.execute("INSERT INTO incident VALUES (1, ?) ON CONFLICT(slot) DO UPDATE SET state=excluded.state",
                           (canonical(state),))

    def ingest(self, alert, snapshot):
        snapshot_sha256 = digest(snapshot)
        with self.transaction() as state:
            if state:
                if state["alert_sha256"] != digest(alert) or snapshot_sha256 != state["observed_snapshot_sha256"]:
                    raise ValueError("Conflicting delivery for this exercise case")
                return {"case_id": state["case_id"], "created": False}
            doc = next((doc for doc in snapshot["documents"] if doc["id"] == alert["document_id"]), None)
            if (alert["synthetic"] is not True or alert["signal"] != "suspected_indirect_prompt_injection"
                    or alert["guardrail_result"] != "blocked" or alert["released_citations"] != 0
                    or doc is None or digest(doc) != alert["document_sha256"]):
                raise ValueError("Alert and retrieved document evidence do not match the exercise")
            state.update(case_id=route_id(alert), alert=alert, alert_sha256=digest(alert),
                         stage="detected", retrieval_open=True, active_snapshot_sha256=snapshot_sha256,
                         observed_snapshot_sha256=snapshot_sha256, baseline_sha256=self.baseline_sha256,
                         proposals={}, timeline=[])
            now = self.clock()
            event(state, "document_version_indexed", "lab-fixture", now - 60, {
                "document_id": doc["id"], "version": doc["version"], "document_sha256": digest(doc),
                "index_sha256": snapshot_sha256,
            })
            event(state, "request_guardrail_blocked", "lab-mocked-rag", now - 1, {
                "request_id": alert["request_id"], "document_sha256": alert["document_sha256"],
                "released_citations": 0, "guardrail_result": "blocked",
            })
            event(state, "detected", ACTORS["analyst"], now, {"alert_sha256": state["alert_sha256"]})
            return {"case_id": state["case_id"], "created": True}

    def triage(self):
        with self.transaction() as state:
            if state.get("stage") != "detected":
                raise ValueError("Triage requires a detected case")
            state["impact"] = {
                "known": "The mocked request retrieved one suspect synthetic version and the guarded path returned a block with no citations.",
                "unknown": "Prior exposure, other queries, live model behavior and any real disclosure were outside the exercise.",
            }
            state["stage"] = "triaged"
            event(state, "triaged", ACTORS["commander"], self.clock(), {
                "severity": "high (exercise)", "escalated_to": ["lab-rag-owner", "lab-soc"],
                "rationale": "Treat the source as untrusted until its index version and controls are validated.",
                "impact": state["impact"],
            })

    def propose(self, action):
        with self.transaction() as state:
            if state.get("stage") != TRANSITIONS[action][0]:
                raise ValueError("Action unavailable in this stage")
            payload = {
                "case_id": state["case_id"], "scope": "offline_simulation", "action": action,
                "expected_stage": state["stage"], "active_snapshot_sha256": state["active_snapshot_sha256"],
                "baseline_sha256": self.baseline_sha256, "alert_sha256": state["alert_sha256"],
                "retest_sha256": digest(state["retests"]) if "retests" in state else None,
            }
            key = digest(payload)
            if key not in state["proposals"]:
                state["proposals"][key] = {"payload": payload, "state": "PENDING"}
                event(state, action + "_proposed", ACTORS["operator"], self.clock(), {"payload_sha256": key})
            return key

    def approve(self, key, confirmed_digest, rationale):
        with self.transaction() as state:
            proposal = state["proposals"].get(key)
            if (not proposal or proposal["state"] != "PENDING" or key != confirmed_digest
                    or digest(proposal["payload"]) != key or not rationale.strip()):
                raise ValueError("Pending exact-payload approval and rationale required")
            now = self.clock()
            proposal.update(state="APPROVED", approval={
                "sha256": key, "at": now, "expires": now + APPROVAL_TTL,
                "actor": ACTORS["commander"], "rationale": rationale,
            })
            event(state, proposal["payload"]["action"] + "_approved", ACTORS["commander"], now,
                  {"payload_sha256": key, "rationale": rationale})

    def execute(self, key, snapshot=None):
        with self.transaction() as state:
            proposal = state["proposals"].get(key)
            if not proposal or digest(proposal["payload"]) != key:
                raise ValueError("Unknown proposal or payload digest mismatch")
            if proposal["state"] == "EXECUTED":
                return "already_executed"
            payload = proposal["payload"]
            action = payload["action"]
            approval = proposal.get("approval")
            at = self.clock()
            failed = (
                proposal["state"] != "APPROVED" or not approval or approval["sha256"] != key
                or approval["actor"] != ACTORS["commander"] or not approval["at"] <= at < approval["expires"]
                or (state["stage"], state["active_snapshot_sha256"]) != (
                    payload["expected_stage"], payload["active_snapshot_sha256"]
                )
                or (action == "restore_snapshot" and (snapshot is None or digest(snapshot) != self.baseline_sha256))
                or (action == "resume_retrieval" and digest(state.get("retests")) != payload["retest_sha256"])
            )
            if failed:
                event(state, "execution_denied", ACTORS["operator"], at, {"payload_sha256": key, "action": action})
                return "denied"
            if action == "restore_snapshot":
                state["active_snapshot_sha256"] = self.baseline_sha256
            state["stage"] = TRANSITIONS[action][1]
            state["retrieval_open"] = action == "resume_retrieval"
            proposal["state"] = "EXECUTED"
            event(state, state["stage"], ACTORS["operator"], at, {
                "payload_sha256": key, "active_snapshot_sha256": state["active_snapshot_sha256"],
                "retrieval_open": state["retrieval_open"],
            })
            return "executed"

    def validate_recovery(self, verify_snapshot, snapshot):
        with self.transaction() as state:
            if state.get("stage") != "recovered" or state["retrieval_open"]:
                raise ValueError("Retest requires a recovered snapshot with retrieval paused")
            if digest(snapshot) != state["active_snapshot_sha256"]:
                raise ValueError("Retest snapshot digest mismatch")
            results = verify_snapshot(snapshot)
            state["retests"] = results
            if set(results) != REQUIRED_RETESTS or any(status is not True for status in results.values()):
                event(state, "retests_failed", ACTORS["analyst"], self.clock(), {"retest_sha256": digest(results)})
                return False
            state["stage"] = "validated"
            event(state, "validated", ACTORS["analyst"], self.clock(), {"retest_sha256": digest(results)})
            return True

    def report(self):
        with self.transaction() as state:
            return state
