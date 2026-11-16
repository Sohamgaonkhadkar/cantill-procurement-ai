# Requirements, implementation and verification

This matrix maps the supplied assessment requirements to implemented components and executed checks. It is a paraphrased engineering index, not a reproduction of private source documents or an evaluator score. See VALIDATION.md for environment-specific results.

| Requirement | Implementation | Evidence and limits |
|---|---|---|
| Frontend, backend and database | Arena React/Vite; FastAPI; SQLAlchemy/PostgreSQL; Alembic migrations | Public application, health, auth and persistent data verified; Docker supports local operation |
| Conversational intake | Request Studio → `/api/chat/messages`; persisted sessions and corrections | Browser and API tests require explicit confirmation; deterministic live intake and optional isolated-demo Gemini assistance |
| Unknown/vague items | Normalization, numeric-specification protection, candidate evidence and clarification | Matching/new-item tests; no invented catalog identity |
| CSV processing | `/api/process-batch`; complete input headers; malformed-header rejection | One output per input line; invalid business rows retain explicit NOT_PROCESSED reasons |
| Policy as data | Registered fact/operator DSL, priorities, configurable thresholds/windows/counts | Policy mutation, exact-boundary and validation tests |
| Amendment upload and approval | Text/PDF/JSON upload; source/diff; preview/simulation; review/approval/activation | Local and hosted preview workflows; unresolved clauses remain gated |
| New scoped rules | Plant/category/type/value and other registered predicates, nested boolean logic | Scoped language tests and five-part API rehearsal; unregistered concepts remain a limitation |
| Effective dates and historical v5.0 | Policy selection per requirement date; explicit version processing | Effective/unapproved policy tests, repeat baseline and immutable replay |
| Anti-splitting grouping | Same-item/plant grouping using fixed first-line windows and earliest eligible match | Inclusive boundaries, multiple eligible groups, nontransitive anchor tests |
| Valuation waterfall | Usable/applicable contract rate; historical PO; standard price; new-item estimate | Exhaustion, history boundaries, precision and worked-example checks |
| Contract validity/ceiling | Inclusive validity, Active supplier, exact sequential allocation | Cheapest-usable selection, capex non-allocation and concurrent ceiling tests |
| PDF-only contracts | Register/PDF reconciliation during private import; manual/runtime proposals | Twelve original contracts audited; two PDF-only contracts included; signature authenticity not inferred |
| First-match routing | Prioritized policy evaluation with complete rule trace | Thresholds, emergency precedence, contract/capex and mutation tests |
| Preferred suppliers | Dated eligibility, component scores, documented weights and reference-price lineage | All three supplied worked rankings match; four-column export checked |
| Supplier safety | Active-only ordering and suggestions; future relationship exclusion | Blocked/inactive invariants and export checker with optional private supplier master |
| PO consolidation | Separate fixed-anchor grouping by supplier, plant, route and timestamp | Distinct requirements can share a PO; sourcing stays separate |
| Buyer approvals | Run-scoped evidence, consolidated approval scope and transactional commitment ledger | Duplicate rejection, current headroom recheck and independent PostgreSQL transactions |
| Overrides and audit | Written reason, original recommendation retained, separate sourcing action | Real hosted preview override/audit; arbitrary direct-PO override intentionally unavailable |
| Detailed explanations | Matching, source lines, anchors, valuation, contract rejections, policy trace and score components | Decision X-Ray and API schemas expose structured evidence |
| Exact CSV output | Authoritative thirteen-column decision schema; decimal text; authenticated export | Serialization tests, browser download, submission integrity checker |
| Optional synthetic demo | Separate DEMO-prefixed inputs, in-memory real-engine preview and CSV export | No live master/run/policy/ledger writes; modified input changes output; not submission data |
| Two-run blind test | Explicit v5.0 run, amendment governance, same-input reprocessing, preferred export | Rehearsal produced three files and 55 affected lines; evaluator files not yet received |
| Reproducibility | Input/data/policy hashes, immutable snapshots, replay | Original sample hash retained; persisted run survives redeployment |
| Setup and delivery | One-command Docker startup, same-origin Vercel app, Neon persistence | Hosted browser verification, production health and clean repository checks |
| Documentation and judgment | DECISIONS, APPROACH, SOLUTION_DESIGN, README and authoritative `openapi.json` | Explicit alternatives, rationale, AI disclosure, evaluation procedure and known limitations |
| Freeze/privacy obligations | Ignored source kit/secrets, public code, output-only submission folder | No fabricated outputs; assessment form and timed output push remain human obligations |

## Optional capabilities beyond the assessment baseline

| Capability | Implementation | Verification boundary |
|---|---|---|
| Grounded conversation | Direct Gemini, typed read-only tools, server-validated fields and backend citations | Real hosted responses observed; availability depends on free-tier quotas |
| Local RAG | PostgreSQL search, reviewed/versioned chunks, source ACLs and effective-date filtering | Remains available without an external provider; private sources stay local |
| Demo embeddings | Native Gemini embeddings for approved fictional/public sources | Eight hosted chunks persisted; repeat request embedded zero duplicates |
| External-data isolation | Separate demo database, explicit flags, per-turn consent and provenance checks | Live egress rejected before client creation; known sensitive patterns blocked; arbitrary text classification is not infallible |
| Public demonstration access | Autofilled controlled roles only in the isolated fictional workspace | Separate session key and restricted database role; live privileged credentials remain private |

These extensions assist exploration and intake. They do not replace the assessment's deterministic procurement engine or permit model-authored financial decisions.

## Code and test navigation

| Concern | Start here |
|---|---|
| Pure procurement behavior | `backend/engine.py`, `tests/test_engine.py` |
| Policy grammar and amendment boundaries | `backend/policy.py`, `backend/language.py`, `tests/test_language.py` |
| Request confirmation and concurrency | `tests/test_chat_submissions.py` |
| Approval contention | `tests/test_postgres_concurrency.py` |
| Authentication and ownership | `backend/security.py`, `tests/test_security.py`, `tests/test_submission_access.py` |
| CSV integrity before processing | `tests/test_csv_intake.py` |
| Final export preflight | `scripts/validate_submission.py`, `tests/test_submission_validation.py` |
| Serverless and stale-resource behavior | `tests/test_serverless.py`, `frontend/src/components/AppRecovery.tsx` |
| Browser workflows | `frontend/e2e/workflows.spec.ts` |

## Acceptance boundary

A passed test demonstrates the behavior asserted by that test. Fourteen known worked decisions are not a full answer key for the entire sample, and sample-derived rehearsals are not unseen accuracy measurements. Evaluator identities are privately provisioned and restricted from identity administration and bulk data replacement. The blind-test amendment must be reviewed faithfully through the existing policy feature; unsupported wording must not be silently ignored.
