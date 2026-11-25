"""Synthetic local extractive RAG companion. No AWS calls, models or credentials."""
import json
import os
import re
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from authorization import allowed_audiences

DOCS = (
    {"document_id": "EDGE-POL-001", "audience": "all_employees",
     "text": "The fictional mission operator checks the readiness dashboard before starting the exercise.",
     "tags": {"readiness", "dashboard", "operator"}},
    {"document_id": "EDGE-POL-002", "audience": "all_employees",
     "text": "The fictional support owner verifies the backup checksum before restoring service.",
     "tags": {"backup", "restore", "checksum"}},
    {"document_id": "EDGE-RESTRICTED-001", "audience": "soc_analysts",
     "text": "SYNTHETIC_RESTRICTED_CANARY", "tags": {"restricted", "canary"}},
)
# Fixed lab identity, never derived from a request. This is not real authentication.
AUDIENCES = allowed_audiences(["employees"])
STATE = Path(os.environ.get("EDGE_STATE", "/state")) / "requests"
def answer(question):
    words = set(re.findall(r"[a-z]+", question.lower()))
    ranked = [(len(words & d["tags"]), d) for d in DOCS if d["audience"] in AUDIENCES]
    score, doc = max(ranked, key=lambda x: x[0], default=(0, None))
    if not score:
        return {"status": "insufficient_evidence", "answer": "The accessible sources do not provide enough information.", "sources": []}
    return {"status": "answered", "answer": doc["text"] + " [1]",
            "sources": [{"source_number": 1, "document_id": doc["document_id"], "uri": "fixture://" + doc["document_id"]}]}
def count():
    return int(STATE.read_text()) if STATE.exists() else 0
def increment():
    # Single-process HTTPServer; atomic replace on the same PVC. No content stored.
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(str(count() + 1))
    tmp.replace(STATE)
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Do not emit raw paths, headers, queries, or request bodies.
    def send_json(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def do_GET(self):
        if self.path == "/healthz":
            self.send_json(200, {"status": "alive"})
        elif self.path == "/readyz":
            ok = os.environ.get("EDGE_READY", "1") == "1" and STATE.parent.is_dir() and os.access(STATE.parent, os.W_OK)
            self.send_json(200 if ok else 503, {"ready": ok})
        elif self.path == "/metrics":
            self.send_json(200, {"successful_requests_total": count(), "backend": "local_extractive_fixture"})
        else:
            self.send_json(404, {"error": "not_found"})
    def do_POST(self):
        if self.path != "/ask":
            return self.send_json(404, {"error": "not_found"})
        started = time.perf_counter()
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 1 <= length <= 4096:
                raise ValueError()
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict) or set(body) != {"question"} or not isinstance(body["question"], str) or not 1 <= len(body["question"].strip()) <= 1000:
                raise ValueError()
        except (ValueError, UnicodeError):
            return self.send_json(400, {"error": "invalid_question"})
        result = answer(body["question"])
        increment()
        print(json.dumps({"event": "edge_request", "status": result["status"], "latency_ms": round((time.perf_counter()-started)*1000, 3)}), flush=True)
        self.send_json(200, result)
if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
