# Foundation log

## Session 1 — 2026-10-26
Status: Storage foundation deployed and configuration verified.

## Current architecture
Operator -> IAM Identity Center -> temporary administrator role
         -> Terraform / AWS CLI -> sandbox S3 bucket -> KMS key

The management account hosts organization administration.
Project resources reside in Portfolio-Sandbox.
No application, model, or retrieval service is deployed yet.

## Decisions
- Use a member account to isolate project resources from management.
- Use SSO temporary credentials rather than static access keys.
- Restrict the Terraform provider to the intended sandbox account ID.
- Use a customer-managed KMS key for explicit key-policy control.
- Enable S3 Bucket Keys to reduce KMS request volume.
- Disable ACLs and block public access.
- Enable versioning; do not automatically empty the bucket on destroy.
- Keep local Terraform state out of Git for initial development.
- AdministratorAccess is for bootstrap; application roles will be narrower.

## Initial threat model
| Threat | Current control | Evidence / limitation |
|---|---|---|
| Accidental public exposure | Four public-access blocks; ACLs disabled | Live settings checked |
| Wrong-account deployment | Provider account allowlist | Sandbox identity verified |
| Unencrypted default uploads | Default SSE-KMS | Synthetic object metadata checked |
| HTTP access | Explicit bucket-policy deny | Policy inspected; request test pending |
| Document deletion or overwrite | Versioning | Enabled; not immutable protection |
| Excessive permissions | Dedicated sandbox boundary | Admin role remains broad |
| Sensitive content in logs | Synthetic data only at this stage | Application logging design pending |

## Verification completed
- Eight Terraform resources created.
- Public-access block, ownership, versioning, and encryption checked.
- Synthetic upload confirmed expected KMS key and object version.
- TLS bucket policy inspected.
- Terraform plan reported no changes.

## Remaining controls and work
- Test actual HTTP denial and unauthorized access.
- Enforce approved encryption choices for ingestion.
- Add least-privilege workload roles and document authorization.
- Design audit logging, monitoring, and private connectivity.
- Move Terraform state to a protected remote backend before collaboration.
- Add ingestion, retrieval, Bedrock, guardrails, and evaluation.
- Implement lifecycle and cleanup procedures.

## Interview question
Why does KMS encryption not prevent a broadly authorized role
from reading documents, and where should document authorization occur?

## Session 2 progress — 2026-10-27
- Created three synthetic Harbor Research documents and metadata files.
- Defined audiences: all_employees, soc_analysts, acquisition_team.
- Checked file presence, JSON syntax, and document ID/audience fields.
- Metadata labels do not enforce access; authorization is still pending.
- Documents remain local; S3 upload and Bedrock ingestion are pending.
- Next: define evaluation questions, explain chunking, and upload documents.
