# Security evaluation extension

The evaluator reuses `rag_service.answer_question`; authorization, retrieval
filtering, guardrail configuration and citation validation remain application-owned.

## Run

```sh
python -m unittest discover -s tests/security -v
python app/evaluate_offline.py
python app/evaluation.py --dataset tests/evaluation/security-v1.json --observations observations.json --output evaluation.json
```

The first evaluation uses mocked AWS retrieval and guardrail decisions. It checks
six synthetic response contracts across retrieval, access boundaries, abstention,
and question/document injection. It makes **zero model calls**. A passing mock
does not establish live retrieval accuracy or prompt-injection resistance.

To score actual captured responses, provide exactly one object per case:
`{"id":"travel","response":{"status":"answered","answer":"Approval [1].","sources":[{"document_id":"HR-POL-001"}]},"latency_ms":123}`.
Use a JSON array covering every case. Preserve actual outputs, including failures.
The CLI returns 1 for failed checks and rejects missing/duplicate observations.
Version and freeze the dataset before a new evaluation. These are development
fixtures, not an independent held-out benchmark. Keywords do not prove semantic
correctness; retain human judgments separately. Existing employee/SOC live
evaluation commands remain available.

Reports retain denominators, category results and a dataset SHA-256. Unauthorized
sources, forbidden canaries, missing relevant documents and sources on abstention
fail the gate. Missing latency stays null.

## Deployment settings

The service supports `AWS_REGION`, `RAG_KNOWLEDGE_BASE_ID`, `RAG_MODEL_ID`,
`RAG_GUARDRAIL_ID`, and `RAG_GUARDRAIL_VERSION` environment overrides.
Existing defaults preserve the current lab configuration. Empty/whitespace
settings and unpublished guardrail versions fail at startup. Set values in the
deployment environment; API callers still cannot supply configuration or audiences.

CI runs the security tests and mocked evaluation and retains its JSON for 14 days.
No AWS resource was deployed by this extension.
