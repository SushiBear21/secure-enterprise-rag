# Secure Enterprise RAG Assistant

AWS Bedrock portfolio project using synthetic, unclassified data.

## Implemented
- Dedicated sandbox, Identity Center access, and budget alert.
- Terraform-managed KMS-encrypted document bucket and S3 vector index.
- Scoped Bedrock service role and knowledge-base-specific trust policy.
- Titan Text Embeddings V2: 1024 dimensions.
- Fixed-size chunking: 300 tokens, 20 percent overlap.
- Three synthetic documents with audience metadata.
- Python retrieval and answer generation using Amazon Nova Lite.
- Source references mapped by the application to retrieved evidence.
- Checks for account identity, returned audience, and citation numbers.

## Run locally in PowerShell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
aws sso login --profile portfolio-sandbox
.\.venv\Scripts\python.exe .\app\ask.py "Who approves incident closure?" --audience soc_analysts

The portfolio-sandbox SSO profile must already be configured.
Model invocation and retrieval incur AWS usage charges.

## Manual checks observed
- Correct cited answers for travel, incident closure, and vendor access.
- Insufficient-evidence response for an unspecified hotel rate.
- Employee filter excluded SOC information in a targeted question.
- Vendor-access answer preserved ambiguity in the source.

## Current limitations
This is a development CLI using administrator credentials.
Audience selection is manual, not authenticated authorization.
Citation checks validate references, not factual support for every claim.
Prompt instructions are not complete prompt-injection defenses.
Guardrails, automated evaluation, and production operations remain pending.

See docs/foundation.md for implementation history and decisions.
