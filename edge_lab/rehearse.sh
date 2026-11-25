#!/usr/bin/env bash
set -Eeuo pipefail
# CI only: all resources are in the uniquely named, disposable kind cluster.
cd "$(git rev-parse --show-toplevel)"
OUT="$PWD/edge-evidence"
BUNDLE="$RUNNER_TEMP/edge29-bundle"
mkdir -p "$OUT" "$BUNDLE"
K=(kubectl --context kind-edge29 -n edge-lab)
PF=""
stop_pf() { if [[ -n "$PF" ]]; then kill "$PF" 2>/dev/null || true; wait "$PF" 2>/dev/null || true; PF=""; fi; }
cleanup() {
  stop_pf
  "${K[@]}" get pods,svc,pvc -o wide > "$OUT/final-resources.txt" 2>&1 || true
  "${K[@]}" logs deploy/edge-rag > "$OUT/final-sanitized.log" 2>&1 || true
  kind delete cluster --name edge29 || true
}
trap cleanup EXIT
exec > >(tee "$OUT/exercise.log") 2>&1
git rev-parse HEAD > "$OUT/revision.txt"
kind version | tee "$OUT/kind-version.txt"
docker version > "$OUT/docker-version.txt"
uname -m > "$OUT/architecture.txt"
nproc > "$OUT/runner-logical-cpus.txt"
PYTHONPATH=app:edge_lab python -m unittest discover -s edge_lab -p 'test_*.py' -v 2>&1 | tee "$OUT/unit-tests.txt"
docker pull python:3.13-slim
BASE=$(docker image inspect python:3.13-slim --format '{{index .RepoDigests 0}}')
printf '%s\n' "$BASE" > "$OUT/base-image-digest.txt"
docker build --build-arg "BASE_IMAGE=$BASE" -f edge_lab/Dockerfile -t edge-rag:lab .
docker image inspect edge-rag:lab --format '{{.Id}}' > "$OUT/workload-image-id.txt"
docker save edge-rag:lab -o "$BUNDLE/image.tar"
cp edge_lab/k8s.json "$BUNDLE/k8s.json"
(cd "$BUNDLE"; sha256sum image.tar k8s.json > SHA256SUMS; sha256sum -c SHA256SUMS)
cp "$BUNDLE/SHA256SUMS" "$OUT/bundle-sha256.txt"
docker pull kindest/node:v1.32.2
NODE=$(docker image inspect kindest/node:v1.32.2 --format '{{index .RepoDigests 0}}')
printf '%s\n' "$NODE" > "$OUT/node-image-digest.txt"
cluster() {
  kind create cluster --name edge29 --image "$NODE" --wait 120s
  kubectl --context kind-edge29 version -o yaml > "$OUT/kubernetes-version.txt"
  (cd "$BUNDLE"; sha256sum -c SHA256SUMS)
  kind load image-archive "$BUNDLE/image.tar" --name edge29
  "${K[@]}" apply -f "$BUNDLE/k8s.json"
  "${K[@]}" rollout status deployment/edge-rag --timeout=180s
}
forward() {
  stop_pf
  "${K[@]}" port-forward --address 127.0.0.1 svc/edge-rag 18080:8080 > "$OUT/port-forward.log" 2>&1 &
  PF=$!
}
start=$(date +%s)
cluster
forward
python edge_lab/probe.py
printf '%s\n' "$(( $(date +%s) - start ))" > "$OUT/initial-cluster-to-ready-seconds.txt"
"${K[@]}" get deploy,pod,svc,pvc,networkpolicy -o wide > "$OUT/baseline-resources.txt"
"${K[@]}" get pods -l app=edge-rag -o jsonpath='{.items[0].status.containerStatuses[0].imageID}' > "$OUT/deployed-image-id.txt"
if "${K[@]}" auth can-i list secrets --as=system:serviceaccount:edge-lab:edge-rag; then echo "Unexpected secrets permission"; exit 1; fi
"${K[@]}" exec deploy/edge-rag -- python -c 'import os; assert os.getuid()==10001; assert not os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token"); print("nonroot and no mounted API token")'
"${K[@]}" exec deploy/edge-rag -- cat /sys/fs/cgroup/cpu.stat > "$OUT/cpu-before.txt"
python edge_lab/probe.py "$OUT/benchmark.json"
"${K[@]}" exec deploy/edge-rag -- cat /sys/fs/cgroup/cpu.stat > "$OUT/cpu-after.txt"
# An absent loopback dependency is a synthetic upstream outage, NOT an enforced network isolation test.
"${K[@]}" exec deploy/edge-rag -- python -c 'import socket; s=socket.socket(); s.settimeout(1); assert s.connect_ex(("127.0.0.1",9)) != 0; print("synthetic upstream unavailable")'
python edge_lab/probe.py
echo "local extraction continues while synthetic upstream is unavailable"
"${K[@]}" exec deploy/edge-rag -- cat /state/requests > "$OUT/counter.backup"
(cd "$OUT"; sha256sum counter.backup > counter.sha256; sha256sum -c counter.sha256)
# Single-writer Recreate policy intentionally allows interruption. Bad readiness must fail.
stop_pf
"${K[@]}" logs deploy/edge-rag > "$OUT/baseline-sanitized.log"
"${K[@]}" set env deploy/edge-rag EDGE_READY=0
if "${K[@]}" rollout status deployment/edge-rag --timeout=100s; then echo "bad candidate unexpectedly ready"; exit 1; fi
# Confirm actual zero ready endpoints before rollback.
"${K[@]}" get endpoints edge-rag -o json > "$OUT/bad-candidate-endpoints.json"
python -c 'import json; d=json.load(open("edge-evidence/bad-candidate-endpoints.json")); assert not any(s.get("addresses") for s in d.get("subsets",[]))'
start=$(date +%s)
"${K[@]}" rollout undo deployment/edge-rag
"${K[@]}" rollout status deployment/edge-rag --timeout=180s
actual=$("${K[@]}" exec deploy/edge-rag -- cat /state/requests)
test "$actual" = "$(cat "$OUT/counter.backup")"
forward
python edge_lab/probe.py
printf '%s\n' "$(( $(date +%s) - start ))" > "$OUT/rollback-to-ready-seconds.txt"
stop_pf
"${K[@]}" logs deploy/edge-rag > "$OUT/rollback-sanitized.log"
# Recreate the cluster and reinstall the saved application bundle (no application image pull).
kind delete cluster --name edge29
start=$(date +%s)
cluster
forward
python edge_lab/probe.py
(cd "$OUT"; sha256sum -c counter.sha256)
stop_pf
# No traffic during restore: this service is exposed only by our loopback port-forward.
"${K[@]}" exec -i deploy/edge-rag -- python -c 'from pathlib import Path; import sys; v=sys.stdin.read().strip(); assert v.isdecimal(); p=Path("/state/restore.tmp"); p.write_text(v); p.replace("/state/requests")' < "$OUT/counter.backup"
actual=$("${K[@]}" exec deploy/edge-rag -- cat /state/requests)
test "$actual" = "$(cat "$OUT/counter.backup")"
forward
python edge_lab/probe.py
printf '%s\n' "$(( $(date +%s) - start ))" > "$OUT/reinstall-restore-seconds.txt"
"${K[@]}" get --raw /version > "$OUT/api-version.json"
echo "PASS: cluster deploy, HTTP contracts, denied API access, synthetic unavailable upstream, bad readiness, rollback/PVC persistence, archive reinstall and counter restore" | tee "$OUT/result.txt"
