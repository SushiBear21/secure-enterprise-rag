# AI incident response exercise

A Harbor Research training document contains a harmless marker. The mocked
guardrail returns a block when this document enters the guarded request
context. The exercise follows a suspected indirect prompt-injection alert
from triage to an explicit retrieval-resume decision. The trace uses fictional
identifiers and contains no question or document body.

## Analyst runbook

From the repository root, install the pinned dependencies and run the tests
and exercise. Python 3.13 is the CI version.

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests/security -p "test_*.py" -v
python -m app.incident_scenario --output ai-incident-case.json
```

The CLI creates a disposable SQLite database and exports the full case, proposal
payloads, approvals, retest results, and hash-linked timeline. In GitHub Actions,
download `rag-ai-incident-case` from the Security unit tests workflow for the
companion checks as well.

1. **Correlate the alert.** Match request `LAB-REQ-001`, alert `RAG-IR-001`, and
   document `HR-LAB-IR-001` version `exercise-2`. Compare the document SHA-256
   recorded at indexing and in the guarded request event. Match the case ID and
   alert digest to the SOAR receipt, when available. Replaying the same alert
   leaves one case. A reused identifier with conflicting evidence is rejected.
2. **Triage and escalate.** The commander records a high exercise severity and
   escalates to the RAG owner and SOC roles. Record the observed block and the
   lack of citations in the response. Record earlier exposure, other requests
   and live impact as unknown. Keep raw source text out of the case.
3. **Pause retrieval in the simulator.** Review the proposal’s case ID, action,
   expected stage, active snapshot digest and alert digest. Confirm the exact
   SHA-256 and record a rationale. A pending or expired approval blocks the
   transition. Check that a simulated request cannot reach model invocation
   while retrieval is paused.
4. **Recover from the known-good snapshot.** Approve a separate restore proposal.
   Verify the SHA-256 of the index membership and configuration against
   [the pinned baseline](../tests/incident/baseline.json). Keep retrieval paused
   during validation and run all six retests. A modified snapshot or a failed
   retest keeps the resume gate closed.
5. **Decide whether to resume.** The commander examines the retest results and
   approves a third payload bound to the recovery receipt. Verify an authorized
   request after resumption. Record the decision, what evidence would invalidate
   it, and the corrective action. A repeated execution returns the original
   terminal status without a second state transition.

### Run the companion checks locally

Use clean sibling checkouts at the revisions below. The SOAR check calls the
workbench’s routing and response helpers to reproduce the case identity, alert
digest and approval gate. Control Tower ingests a synthetic follow-up finding,
denies execution before approval and creates exactly one local ticket after
explicit approval. The two checks run in isolated Python processes and their
receipts are included in the case JSON.

| Repository | Pinned source |
| --- | --- |
| `SushiBear21/aws-security-response-lab` | [Workbench commit 7018def](https://github.com/SushiBear21/aws-security-response-lab/commit/7018def69bf97feda639e76cfc880e4f92f8b0f0) |
| `SushiBear21/agentic-security-workflow` | [Control Tower commit a7f5c38](https://github.com/SushiBear21/agentic-security-workflow/commit/a7f5c38ad62f14eddb298ca546abd76ddd6a82f8) |

```sh
python -m app.incident_scenario --output ai-incident-case.json \
  --response-lab ../aws-security-response-lab --control-tower ../agentic-security-workflow
```

## Post-incident report

**Case** `4fa132f766c274b6ccc88699fee9a79c842b69819dd11cee516ec7d74ef3943e`

**Alert SHA-256** `7d7faf44faa6d0ca12d96c0fb0800cdcbbc7b429644cb7d5c886f3da0dc6a02b`

**Evidence period** Nov 19, 2026, scripted UTC times

| Time (UTC) | Observed event or decision |
| --- | --- |
| 17:59:00 | The fixture stages the suspect version in the index. |
| 17:59:59 | The mocked guardrail blocks the request with zero released citations. |
| 18:00:00 | The alert opens one case. Duplicate delivery opens no additional case. |
| 18:00:45 | The incident commander sets high exercise severity and escalates. |
| 18:02:00 | The approved pause takes effect. A request cannot reach model invocation. |
| 18:05:00 | The approved restore installs the pinned simulated index and configuration. Retrieval remains paused. |
| 18:06:00 | Six retests pass, covering both authorized personas, a restricted result rejected before inference, an invalid citation rejected, suspect document exclusion, and the snapshot digest. |
| 18:06:15 | The commander approves resume after reviewing the exact retest receipt. An authorized request succeeds. |

**Response metrics.** Detection to triage was 45 seconds, detection to
simulated containment was 120 seconds, containment to validated recovery was
240 seconds, and validated recovery to resume was 15 seconds. These intervals
come from the exercise clock and describe the decision sequence.

**Impact and cause.** In the simulated index, a new document version was
eligible for employee retrieval. The observed fixture response was blocked
before returning an answer or source references. The exercise did not establish
actual exposure, prior affected requests, or why a live ingestion control
would have let a document through.

**Corrective action.** The RAG ingestion owner’s follow-up is to verify retired
document exclusion before retrieval resumes. The retest issued a request for the
retired fixture against the recovered snapshot and observed insufficient
evidence, zero source citations and zero calls to the mocked model boundary.
The resume gate stayed closed until validation and approval. Owner review and
closure are tracked in [RAG issue #3](https://github.com/SushiBear21/secure-enterprise-rag/issues/3).
The broader incident command and metrics work is tracked in
[portfolio issue #18](https://github.com/SushiBear21/agentic-security-workflow/issues/18).

**Boundaries.** The original RAG service runs its audience and citation checks.
Bedrock responses, retrieval results, leadership roles, and the timeline clock
are scripted. The exercise performs zero AWS calls and changes only disposable
local state. The JSON timeline detects edits to its saved entries. It has no
independent signature, immutable storage, or identity enforcement. Live guardrail
efficacy, AWS containment and recovery, and notification delivery remain
unverified.
