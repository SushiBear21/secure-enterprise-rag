# Secure Enterprise RAG: demo walkthrough

## Before presenting

- Confirm the API is deployed and the test accounts work.
- Run the local tests and review the latest live evaluations.
- Open the README architecture diagram and GitHub Actions results.
- Use only synthetic documents.
- Keep passwords, MFA setup codes, and tokens off shared screens.
- Allow extra time for browser sign-in and account switching.

## 1. Explain the problem — 30 seconds

"This application answers questions from enterprise documents while
restricting retrieval according to the signed-in user's groups.

It uses fictional policies so I can demonstrate the security controls
without handling real organizational information."

Show the README architecture diagram.

## 2. Demonstrate employee access — 90 seconds

From the repository root:

    .\.venv\Scripts\python.exe .\app\check_ask.py

Sign in as employee-demo.

Show:
- Anonymous request rejected with HTTP 401.
- Travel question answered with supervisor approval and HR-POL-001.
- SOC closure question returning insufficient evidence and no sources.
- Client-supplied audience override rejected with HTTP 400.

Explain:
"The backend derives permissions from verified Cognito groups.
The request cannot select its own audience."

## 3. Demonstrate SOC access — 90 seconds

Sign out of the employee session before switching accounts:

    Start-Process "https://secure-rag-359769212511.auth.us-east-1.amazoncognito.com/logout?client_id=7clhovnk1ofjeo9855eedofog4&logout_uri=http%3A%2F%2Flocalhost%3A8000%2F"

The localhost page may fail to load after sign-out because the
local callback server is not running.

Run:

    .\.venv\Scripts\python.exe .\app\check_soc.py

Sign in as soc-demo.

Show:
- Incident closure answered from HR-SOC-001.
- General travel policy still accessible.
- Acquisition question returning insufficient evidence.

Explain:
"SOC membership adds SOC documents to general employee access.
It does not grant acquisition access."

## 4. Explain injection defenses — 45 seconds

Show the recorded security-test results.

Explain:
"I tested attacks in user questions and in simulated retrieved evidence.
The deployed guardrail blocked the tested user attacks, and the local
malicious-evidence test produced an explicit guardrail block.

Authorization is enforced by application code. Guardrails add detection
but are not responsible for deciding which documents a user may access."

## 5. Show engineering evidence — 45 seconds

Show:
- GitHub Actions passing the 17 local security tests.
- Live evaluation reports: 6 employee checks and 3 SOC checks.
- An application log showing request IDs, outcome, and duration.

Explain:
"The application logs omit questions, document content, answers,
and tokens. API logs also capture requests rejected before Lambda."

## Close with limitations — 30 seconds

"This is a working sandbox demonstration, not a production deployment.
The API is public and authenticated; private endpoints are not implemented.

Citation checks validate reference numbers, not every claim's factual
support. The evaluations cover specific cases and use simple answer checks.

Next improvements would include broader identity and attack coverage,
stronger answer grading, recovery exercises, and production network design."

## If a live step fails

Do not hide the failure or repeatedly rerun until it passes.
Record the failing case and use the saved evaluation report to explain
the last verified behavior.

Use request IDs to correlate API and Lambda logs.
Do not expose credentials or enable request-body logging to troubleshoot
during a presentation.