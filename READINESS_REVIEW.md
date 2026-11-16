# Assessment readiness review

Reviewed 16 November 2026. This is an evidence-based implementation self-review, not an independent security audit or a predicted assessment score. The actual blind batch and amendment have not been received.

## Overall assessment

The required procurement workflow is implemented, hosted and exercised end to end. Known worked examples match, the API exposes detailed evidence, and a two-run amendment rehearsal completed without application-code changes. The strongest remaining uncertainty is the meaning and novelty of the unseen amendment, followed by operational discipline during the two-hour submission window.

Current review baseline: **145 PostgreSQL tests**, **143 SQLite tests with two PostgreSQL-only skips**, and **13 browser scenarios** pass. The original sample retains its business-output hash. See VALIDATION.md for the environments and limits of those results.

| Assessment area | Weight | Implemented evidence | Residual uncertainty |
|---|---:|---|---|
| Automated decisions | 40% | All 14 supplied worked decisions and 3 ranking examples match; exact arithmetic, boundaries, supplier eligibility, grouping and consolidation have regressions | The sample has no complete answer key; unseen descriptions and edge cases can differ |
| Policy as data | 15% | Versioned DSL, registry, upload, diff, simulation, review, approval, activation; new plant/category rule rehearsed | Unfamiliar prose needs manual authoring; entirely new underlying facts/operations are not guaranteed |
| Chat and UX | 20% | Server-side sessions, clarification, corrections, explicit confirmation, real buyer actions and eleven integrated screens | Deterministic parsing is narrower than unrestricted conversational understanding |
| Business judgment | 15% | DECISIONS.md documents boundaries, ambiguity, ranking rationale, invalid lines and safe overrides | Evaluators may prefer a different reasonable interpretation |
| Engineering/delivery | 10% | Persistent PostgreSQL, migrations, OpenAPI client, automated tests, Docker, public repository and verified hosted application | No exhaustive load/penetration test; serverless payload limits remain |

No numerical score is assigned: test coverage and known-case agreement cannot establish a hidden evaluator's result.

## Concrete improvements from the review

- Reject duplicate or blank CSV headers before creating a run, preventing silent replacement of quantity or other fields.
- Provide a read-only submission checker for the three exported CSVs, including exact headers, PR-line multiplicity, route/action consistency, finite decimal text, repeated-group consistency, top-three ranks and optional Active-supplier checks.
- Document public signup throttling accurately in OpenAPI and expose the submission-access flag through Docker Compose configuration.
- Consolidate architecture, requirement traceability, executed validation and blind-test operations into linked documents instead of scattered progress notes.

## Risks requiring attention

| Priority | Risk | Practical response |
|---|---|---|
| High | Amendment wording does not compile completely | Reconcile every clause in Policy Reactor's existing DSL editor before review; do not approve unresolved text blindly |
| High | Public shared-role visitors mutate the assessment workspace | Check active policies, master data and purchasing records before the timed runs; avoid demo purchasing approvals |
| High | Form submission or final CSV push is missed | Submit links before 10 AM IST; freeze source; push only the three outputs before noon |
| Medium | A new condition needs a business fact absent from the registry | Review the current registry before freeze; do not promise arbitrary engine extensibility after freeze |
| Medium | Large batch exceeds hosted limits or runtime budget | Check file size early; use the prepared local full-batch path if needed; never silently split anti-splitting groups |
| Medium | Scanned amendment cannot be extracted | Transcribe faithfully into the existing policy workflow and verify the resulting rules |
| Medium | The interface encounters blocked resources or stale assets | Inline loading/recovery, correct asset 404s and no-store HTML are implemented and browser-tested |

## Release and blind-test gates

Before code freeze, verify public health/sign-in, v5.0 availability, imported data, the amended-policy procedure and the export checker. Keep source artifacts and credentials out of Git. Record the final application commit and complete the assessment form; deployment alone is not submission.

During the blind test, process the exact batch under v5.0, preserve its input/run hashes, apply the supplied amendment through the frozen application, then reprocess and export preferred suppliers for the specified date. Do not approve PO recommendations between comparison runs. Validate and push the three actual CSVs before noon.

See BLIND_TEST_RUNBOOK.md for the operational sequence, REQUIREMENTS_TRACEABILITY.md for requirement coverage, and VALIDATION.md for measured results and their limits.
