"""Optional strict provenance gate for Bedrock retrieval results.

The ingestion owner must pin a trusted manifest outside model/retrieval control.
Retrieved metadata alone never proves that a document is authoritative.
"""
import hashlib
import json
from pathlib import Path


class ProvenanceDenied(RuntimeError):
    pass


def content_hash(text):
    if not isinstance(text, str):
        raise ProvenanceDenied("retrieved text must be a string")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_manifest(path):
    """Load a host-operated snapshot. Never accept this path from a user query."""
    file = Path(path)
    if not file.is_file() or file.stat().st_size > 1024 * 1024:
        raise ProvenanceDenied("trusted manifest unavailable or too large")
    try:
        manifest = json.loads(file.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError, OSError) as exc:
        raise ProvenanceDenied("invalid trusted manifest") from exc
    if not isinstance(manifest, dict) or manifest.get("schema") != "rag-trust-manifest-v1":
        raise ProvenanceDenied("unsupported trusted manifest schema")
    docs = manifest.get("documents")
    if not isinstance(docs, dict) or not docs:
        raise ProvenanceDenied("trusted manifest has no document entries")
    return docs


def verify_retrieved(item, trusted_docs):
    """Return a source receipt only if identity, scope, URI and text match."""
    if not isinstance(item, dict):
        raise ProvenanceDenied("retrieval result must be a dictionary")
    metadata = item.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise ProvenanceDenied("invalid retrieval metadata")
    document_id = metadata.get("document_id")
    if not isinstance(document_id, str) or document_id not in trusted_docs:
        raise ProvenanceDenied("document missing from trusted manifest")
    trusted = trusted_docs[document_id]
    if not isinstance(trusted, dict) or set(trusted) != {"uri", "audience", "content_sha256"}:
        raise ProvenanceDenied("invalid trusted document entry")
    uri = (item.get("location") or {}).get("s3Location", {}).get("uri")
    text = (item.get("content") or {}).get("text")
    actual = content_hash(text)
    if (uri != trusted["uri"] or metadata.get("audience") != trusted["audience"] or
            not isinstance(trusted["content_sha256"], str) or
            actual != trusted["content_sha256"]):
        raise ProvenanceDenied("retrieved evidence differs from trusted ingestion snapshot")
    return {"document_id": document_id, "uri": uri, "content_sha256": actual,
            "source_authority": "evidence_only", "manifest_verified": True}
