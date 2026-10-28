# Evaluation guide

## Verified results

- Local security unit tests: 17 passed.
- Live employee evaluation: 6/6 passed.
- Live SOC evaluation: 3/3 passed.
- GitHub Actions security-test workflow: passed.

See the live evaluation JSON reports for execution timestamps
and individual case results.

## Local tests

From the repository root:

    .\.venv\Scripts\python.exe -m unittest discover -s tests/security -p "test_*.py" -v

These tests mock AWS calls and require no AWS credentials.

Coverage includes:
- Group-to-audience mapping.
- Rejection of missing identity, ID tokens, missing scope,
  unknown groups, and client-supplied audience overrides.
- Server-derived employee permissions.
- Unauthorized evidence rejected before model invocation.
- Guardrail intervention returning no sources.
- Model service failure without an unguarded retry.
- Retrieval failure and empty retrieval.
- Rejection of truncated answers and nonexistent citations.

## Live evaluations

The AWS application must be deployed.

Employee suite:

    .\.venv\Scripts\python.exe .\app\evaluate_employee.py

Sign in as employee-demo.

SOC suite:

    .\.venv\Scripts\python.exe .\app\evaluate_soc.py

Sign in as soc-demo. Sign out of the previous browser session
first when switching accounts.

Each evaluator checks the identity's allowed audiences before
running its cases. Tokens remain in memory.

Reports:
- tests/evaluation/live-employee-results.json
- tests/evaluation/live-soc-results.json

Reports contain case identifiers, pass/fail results, timing,
and failure summaries. They omit tokens and response content.

A failed case produces a nonzero process exit code.
Live runs invoke AWS services and can incur charges.

## GitHub Actions

.github/workflows/tests.yml runs syntax checks and local
security tests on pushes, pull requests, and manual dispatch.

It does not run live AWS evaluations or deploy infrastructure.
No AWS credentials are configured for this workflow.

## Limitations and future coverage

Passing tests demonstrate these cases, not complete security
or factual correctness.

Answer checks use expected terms, source documents, and
citation numbers. They can miss incorrect or contradictory
claims and can reject valid paraphrases.

Local identity tests simulate authorizer context. They do not
verify JWT signatures, issuer, audience, or expiration.
Live anonymous-request tests exercise deployed authorization,
but comprehensive invalid-token tests remain future work.

Live coverage currently uses employee and SOC accounts.
An acquisition-user evaluation and a deployed multi-group
evaluation remain future work.

Broader attack variations, repeated model runs, load tests,
real failure-trigger alarm tests, and state-recovery exercises
remain future work.

A green workflow does not itself make the check mandatory
for merging; branch protection is configured separately.