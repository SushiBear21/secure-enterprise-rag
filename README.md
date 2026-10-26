# Secure Enterprise RAG Assistant

An AWS/Bedrock portfolio project using only synthetic, unclassified data.

## Current implementation
- Dedicated AWS sandbox account and Identity Center CLI authentication.
- Monthly budget alert.
- Terraform-managed S3 document storage.
- Customer-managed KMS encryption with key rotation.
- S3 Block Public Access, disabled ACLs, and versioning.
- Bucket policy denying insecure transport for non-service principals.

## Verification
Live settings checked, a synthetic upload confirmed SSE-KMS encryption
with the expected key, and Terraform reported no configuration drift.
TLS policy inspected; an HTTP denial test remains pending.

## Next milestone
Document ingestion, metadata, and retrieval design.
Bedrock, application authorization, and AI defenses are not implemented yet.

See docs/foundation.md for architecture, decisions, and remaining work.
