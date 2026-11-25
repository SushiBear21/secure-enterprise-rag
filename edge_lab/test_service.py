import json
import unittest
from pathlib import Path
from service import answer

class Contract(unittest.TestCase):
    def test_public(self):
        self.assertEqual(answer("readiness dashboard")["sources"][0]["document_id"], "EDGE-POL-001")
    def test_restricted(self):
        self.assertEqual(answer("restricted canary")["status"], "insufficient_evidence")
        self.assertNotIn("SYNTHETIC_RESTRICTED_CANARY", json.dumps(answer("restricted canary")))
    def test_unknown(self):
        self.assertEqual(answer("unrelated")["sources"], [])
    def test_manifest(self):
        items = {i["kind"]: i for i in json.loads((Path(__file__).parent / "k8s.json").read_text())["items"]}
        pod = items["Deployment"]["spec"]["template"]["spec"]
        c = pod["containers"][0]
        self.assertFalse(pod["automountServiceAccountToken"])
        self.assertTrue(c["securityContext"]["readOnlyRootFilesystem"])
        self.assertEqual(c["securityContext"]["capabilities"]["drop"], ["ALL"])
        self.assertEqual(c["imagePullPolicy"], "Never")
        self.assertEqual(items["Service"]["spec"]["type"], "ClusterIP")
        self.assertEqual(items["NetworkPolicy"]["spec"]["egress"], [])
        self.assertIn("limits", c["resources"])
        self.assertIn("readinessProbe", c)
        self.assertIn("livenessProbe", c)
        self.assertEqual(pod["volumes"][0]["persistentVolumeClaim"]["claimName"], "edge-state")
if __name__ == "__main__":
    unittest.main()
