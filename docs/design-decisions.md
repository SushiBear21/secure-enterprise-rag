# Design decisions and tradeoffs

## Managed AWS services

Decision:
Use Cognito, API Gateway, Lambda, Bedrock Knowledge Bases, and
S3 Vectors rather than operate servers and a separate vector database.

Reason:
This keeps the sandbox focused on identity, retrieval, AI security,
testing, and infrastructure automation.

Tradeoff:
The application depends on AWS-specific APIs and service behavior.
A larger deployment would require workload-based cost, latency,
availability, quota, and portability assessments.

## Application-enforced document access

Decision:
Derive audiences from verified Cognito groups, filter retrieval,
and check every returned document's audience before model invocation.

Reason:
The model should receive only evidence the user is permitted to access.
Requests cannot choose their own audience.

Tradeoff:
The Lambda role can retrieve across the knowledge base. User-level
separation therefore depends on correct application enforcement and
trusted document metadata. It is not separate AWS storage isolation
for each audience.

For stronger isolation, evaluate separate knowledge bases, storage,
and execution roles for different security boundaries.

## Guardrails plus authorization

Decision:
Apply prompt-attack detection to the question and authorized evidence
through Bedrock Converse guardContent.

Reason:
Both user questions and retrieved documents can contain instructions
that attempt to override application behavior.

Tradeoff:
Detection can miss attacks or block legitimate content. It supplements
authorization and does not prove factual correctness.

The application does not retry without the guardrail when a guarded
request fails.

## Explicit retrieval and generation

Decision:
Retrieve evidence first, validate its audience and metadata, then call
the generation model.

Reason:
This creates an application checkpoint before evidence reaches the model.
It also lets the application map citations to retrieved source records.

Tradeoff:
More application code must handle retrieval, model failures, citation
validation, and insufficient-evidence responses.

Valid citation numbers do not prove that the cited text supports
every generated claim.

## Shared KMS key for documents and vectors

Decision:
Use one customer-managed KMS key for the synthetic document bucket
and vector storage, with scoped service permissions.

Reason:
This demonstrates key policies and encrypted storage with fewer
resources to manage in a learning sandbox.

Tradeoff:
A shared key creates a shared dependency and couples administration.
Separate keys may be appropriate for independent data boundaries
or lifecycle requirements.

The Terraform state bucket uses S3-managed encryption separately.

## Public authenticated API

Decision:
Use a public API Gateway endpoint with Cognito JWT authorization.
Lambda has no customer VPC attachment.

Reason:
This supports a small browser-login demonstration without adding
private-network connectivity requirements.

Tradeoff:
The endpoint is internet-reachable. Authentication, authorization,
throttling, monitoring, and secure application handling remain essential.

Private endpoints, network egress controls, and additional edge
protection require a separate production design.

## Safe operational logs

Decision:
Log request IDs, outcomes, status codes, and duration while omitting
questions, answers, tokens, and retrieved document text.

Reason:
This supports troubleshooting while reducing sensitive content in logs.

Tradeoff:
Investigating model-quality failures requires controlled reproduction
with synthetic data rather than reading full conversations from logs.

Detailed dependency-error classification remains an improvement area.

## Remote application state and separate bootstrap

Decision:
Store application state in encrypted, versioned S3 with native locking.
Manage the bucket through a separate bootstrap configuration.

Reason:
This separates application teardown from state-storage management and
provides version history for recovery.

Tradeoff:
Bootstrap state remains local and needs protected backups.
State recovery has not yet been rehearsed.
Terraform prevent_destroy is a configuration safeguard, not an
AWS-level prohibition against deletion.

## Local tests and live evaluations

Decision:
Run deterministic unit tests in GitHub Actions and run authenticated
AWS evaluations separately.

Reason:
Local tests exercise security boundaries and failure handling without
AWS credentials. Live checks exercise deployed behavior.

Tradeoff:
Mocks cannot establish that AWS integrations behave correctly.
Live model outputs can vary, and keyword checks are incomplete.

The current evidence is 17 passing local tests, 6 passing employee
checks, and 3 passing SOC checks. Acquisition-user, deployed
multi-group, and broader invalid-token cases remain future work.

## Production readiness

Before handling real organizational data, assess:
- Data classification, retention, and model-use requirements.
- Ingestion ownership and metadata integrity.
- Identity lifecycle and group-change behavior.
- Stronger isolation where required.
- Broader adversarial and answer-quality evaluations.
- Recovery, load, availability, and real failure-trigger alert tests.
- Deployment reproducibility and environment-specific configuration.
- Cost controls and operational ownership.

This portfolio demonstrates selected controls and their tests.
It is not a production certification or compliance assessment.