# RAG trusted-source provenance — synthetic security extension

This repository now includes a **strict opt-in** source verification boundary. Its purpose is to verify that retrieved RAG chunks match an **independently managed ingestion snapshot**, not to infer that retrieved text can command an agent.

## Enabling the optional gate

Set `RAG_PROVENANCE_MANIFEST_PATH` in the trusted service environment to an administrator-managed, read-only JSON manifest accessible to the RAG runtime (for AWS Lambda, package/mount it securely). **Do not derive this path or manifest from user input, LLM output, or retrieved documents.** Without the variable, the existing audience filter and audience cross-check remain, but the new digest-based provenance verification is inactive.

The manifest is a JSON object with `schema: "rag-trust-manifest-v1"` and a `documents` object keyed by the source `document_id`. Each value contains **exactly** `uri`, `audience` and `content_sha256` (hex SHA-256 of the **exact retrieval chunk text**, not necessarily the full source file).

Example (replace the hash with the actual approved ingestion digest):

```json
{
  "schema": "rag-trust-manifest-v1",
  "documents": {
    "SYN-001": {
      "uri": "s3://synthetic-evidence/soc.txt",
      "audience": "soc_analysts",
      "content_sha256": "REPLACE_WITH_64_CHARACTER_SHA256"
    }
  }
}
```

The runtime verifies the document ID, audience, S3 URI, and SHA-256 of the retrieved text **before passing the evidence to Bedrock Converse**. On mismatch or missing trusted manifest, it raises a `ProvenanceDenied` exception, with no unguarded retry. Strict and non-strict responses label their source receipts with `provenance_verified`.

**Warning:** Real Bedrock Knowledge Base retrieval may return changed chunks after re-indexing, document updates, or tokenizer changes. Generate and rotate trusted manifests from a reproducible approved ingestion/retrieval snapshot. This first prototype stores one chunk digest per document ID, which may fail for multi-chunk documents. Do not enable strict mode in an existing deployed knowledge base until the ingestion contract and rotation lifecycle are addressed.

## Tested boundaries

`app/evidence_provenance.py` validates trusted manifest syntax and source match. `tests/security/test_evidence_provenance.py` exercises matching evidence, changed text, forged audience/URI, spoofed policy-authority metadata, bad manifests, and a mocked service test verifying that tampered evidence never reaches model inference.

```bash
python -m unittest discover -s tests/security -p 'test_*.py' -v
```

This is a **pre-inference source integrity check**, not a semantic fact verifier, prompt-injection classifier, production signed-ingestion pipeline, or replacement for group authorization. Even correctly pinned malicious documents remain untrusted instructions; the RAG system must keep authorization and action policy outside retrieved text.

Companion action-approval and workflow safety lab: [agentic-security-workflow](https://github.com/SushiBear21/agentic-security-workflow/blob/feature/agent-execution-integrity-20261123/docs/portfolio/agent-execution-integrity.md). Related governance evidence remains separate from this implementation.
