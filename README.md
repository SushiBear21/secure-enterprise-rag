# Secure Enterprise RAG Assistant

AWS Bedrock portfolio project using synthetic, unclassified data.

## Implemented
- Dedicated sandbox, Identity Center access, and budget alert.
- Terraform-managed KMS-encrypted document bucket and S3 vector index.
- Scoped Bedrock service role and knowledge-base-specific trust policy.
- Titan Text Embeddings V2 with 1024-dimensional vectors.
- Fixed-size chunking: 300 tokens, 20 percent overlap.
- Three synthetic documents with audience metadata.
- Knowledge base and S3 data-source connection.

## Verified
- Initial ingestion: 3 documents indexed, 0 failures.
- Updated runbook: 1 modified document indexed, 0 failures.
- Retrieved relevant evidence for employee, SOC, and acquisition queries.
- Employee metadata filter excluded the SOC runbook in a targeted test.

## Limits
CLI tests use administrator access and manually supplied filters.
End-user authorization, generated answers, guardrails, and automated
evaluation are not implemented. Similarity scores are not confidence
probabilities. The vendor-access source has an ambiguous one-year start date.

See docs/foundation.md for progress and security decisions.
