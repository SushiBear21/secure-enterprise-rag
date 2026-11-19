from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.incident_response import APPROVAL_TTL, Incident, digest, verify_timeline
from app.incident_scenario import ExerciseClock, alert_for, case_rag, rehearse, recovery_retests, snapshots


class IncidentResponseTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "case.sqlite"
        self.clock = ExerciseClock()
        self.baseline, self.observed = snapshots()
        self.alert = alert_for(self.observed)
        self.case = Incident(self.path, self.clock, digest(self.baseline))

    def ingest(self):
        return self.case.ingest(self.alert, self.observed)

    def authorize(self, action, snapshot=None):
        proposal = self.case.propose(action)
        self.case.approve(proposal, proposal, "Lab decision with supporting evidence.")
        self.assertEqual("executed", self.case.execute(proposal, snapshot))
        return proposal

    def recovered(self):
        self.ingest()
        self.case.triage()
        self.authorize("pause_retrieval")
        self.authorize("restore_snapshot", self.baseline)

    def test_end_to_end_report(self):
        result = rehearse(self.path)
        case = result["case"]
        self.assertEqual("resumed", case["stage"])
        self.assertEqual(1, result["case_count"])
        self.assertFalse(result["duplicate_delivery"]["created"])
        self.assertEqual({"EXECUTED"}, {record["state"] for record in case["proposals"].values()})
        self.assertEqual(3, sum(row["kind"] == "execution_denied" for row in case["timeline"]))
        self.assertEqual(6, sum(case["retests"].values()))
        self.assertEqual(120, result["phase_seconds"]["detection_to_simulated_containment"])
        self.assertEqual(240, result["phase_seconds"]["containment_to_validated_recovery"])
        self.assertTrue(result["corrective_action"]["retest"])
        self.assertEqual(0, result["aws_calls"])
        verify_timeline(case["timeline"])

    def test_duplicate_after_reopen_and_conflicting_delivery(self):
        result = self.ingest()
        self.case = Incident(self.path, self.clock, digest(self.baseline))
        self.assertEqual({"case_id": result["case_id"], "created": False}, self.ingest())
        with self.assertRaisesRegex(ValueError, "Conflicting delivery"):
            self.case.ingest({**self.alert, "request_id": "different"}, self.observed)
        self.assertEqual(3, len(self.case.report()["timeline"]))

    def test_wrong_document_hash_rejected(self):
        with self.assertRaisesRegex(ValueError, "evidence do not match"):
            self.case.ingest({**self.alert, "document_sha256": "0" * 64}, self.observed)
        self.assertEqual({}, self.case.report())

    def test_retrieval_pause_approval_expiration_and_exact_digest(self):
        self.ingest()
        self.case.triage()
        proposal = self.case.propose("pause_retrieval")
        self.assertEqual(proposal, self.case.propose("pause_retrieval"))
        self.assertEqual("denied", self.case.execute(proposal))
        with self.assertRaisesRegex(ValueError, "exact-payload"):
            self.case.approve(proposal, "0" * 64, "Incorrect confirmation.")
        self.case.approve(proposal, proposal, "Pause pending investigation.")
        self.clock.advance(APPROVAL_TTL)
        self.assertEqual("denied", self.case.execute(proposal))
        self.assertTrue(self.case.report()["retrieval_open"])

    def test_modified_snapshot_rejected_without_reopening_retrieval(self):
        self.ingest()
        self.case.triage()
        self.authorize("pause_retrieval")
        self.assertEqual("Exercise retrieval paused",
                         case_rag(self.case, self.observed).ask("HR-POL-001", ["employees"])["error"])
        restore = self.case.propose("restore_snapshot")
        self.case.approve(restore, restore, "Restore the verified baseline only.")
        self.assertEqual("denied", self.case.execute(restore, self.observed))
        self.assertEqual("paused", self.case.report()["stage"])
        self.assertEqual("executed", self.case.execute(restore, self.baseline))
        self.assertFalse(self.case.report()["retrieval_open"])
        with self.assertRaisesRegex(RuntimeError, "not active"):
            case_rag(self.case, self.observed)

    def test_failed_retest_prevents_resume_then_pass_requires_approval(self):
        self.recovered()
        self.assertFalse(self.case.validate_recovery(lambda snapshot: {"snapshot_verified": True}, self.baseline))
        with self.assertRaisesRegex(ValueError, "unavailable"):
            self.case.propose("resume_retrieval")
        self.assertTrue(self.case.validate_recovery(recovery_retests, self.baseline))
        resume = self.case.propose("resume_retrieval")
        self.assertEqual("denied", self.case.execute(resume))
        self.assertFalse(self.case.report()["retrieval_open"])
        self.case.approve(resume, resume, "Reviewed exact retest receipt.")
        self.assertEqual("executed", self.case.execute(resume))
        self.assertEqual("already_executed", self.case.execute(resume))
        self.assertTrue(self.case.report()["retrieval_open"])

    def test_case_evidence_detects_edited_timeline(self):
        self.ingest()
        timeline = deepcopy(self.case.report()["timeline"])
        timeline[1]["details"]["released_citations"] = 1
        with self.assertRaisesRegex(ValueError, "timeline integrity"):
            verify_timeline(timeline)
