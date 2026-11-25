"""Actual HTTP requests through loopback port-forward, not model benchmarks."""
import json
import math
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
BASE = "http://127.0.0.1:18080"
def call(path, payload=None):
    request = urllib.request.Request(BASE + path, data=None if payload is None else json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=4) as response:
        return json.load(response)
def wait():
    end = time.monotonic() + 30
    while time.monotonic() < end:
        try:
            if call("/readyz")["ready"]:
                return
        except (OSError, ValueError):
            pass
        time.sleep(0.5)
    raise RuntimeError("port-forward readiness timed out")
def check():
    assert call("/ask", {"question":"readiness dashboard"})["sources"][0]["document_id"] == "EDGE-POL-001"
    result = call("/ask", {"question":"restricted canary"})
    assert result["status"] == "insufficient_evidence" and not result["sources"]
    try:
        call("/ask", {"question":"restricted canary", "audiences":["soc_analysts"]})
    except urllib.error.HTTPError as err:
        assert err.code == 400
    else:
        raise AssertionError("audience override accepted")
def benchmark(path):
    latencies, failures = [], 0
    started = time.perf_counter()
    for _ in range(100):
        t = time.perf_counter()
        try:
            result = call("/ask", {"question":"backup checksum"})
            assert result["sources"][0]["document_id"] == "EDGE-POL-002"
            latencies.append((time.perf_counter()-t)*1000)
        except (OSError, ValueError, AssertionError, KeyError, IndexError):
            failures += 1
    duration = time.perf_counter()-started
    values = sorted(latencies)
    record = {"workload":"100 serial local extractive HTTP requests (no model)", "attempts":100,
              "successes":len(values), "failures":failures, "duration_s":duration,
              "successful_requests_per_s":len(values)/duration,
              "median_ms":statistics.median(values) if values else None,
              "p95_ms":values[math.ceil(.95*len(values))-1] if values else None}
    Path(path).write_text(json.dumps(record, indent=2)+"\n")
    print(json.dumps(record))
    assert failures == 0
if __name__ == "__main__":
    wait()
    check()
    if len(sys.argv) == 2:
        benchmark(sys.argv[1])
