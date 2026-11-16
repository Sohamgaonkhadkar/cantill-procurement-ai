# Verification evidence

Reviewed 16 November 2026. Results distinguish pure business checks, API tests, real PostgreSQL transactions, browser workflows and actual hosted behavior. Test counts are evidence of asserted behaviors, not an independent assessment score.

## Current automated baseline

| Check | Environment | Executed result |
|---|---|---|
| Complete Python suite | Windows / Python 3.14 / SQLite API fixtures | **148 passed, 2 PostgreSQL-only tests skipped** |
| Complete Python suite | Linux / Python 3.12 / isolated PostgreSQL corvo_test | **150 passed**, including independent approval and chat-confirmation transactions |
| Complete browser suite | Chromium / real isolated FastAPI and SQLite / Vite | **14 passed**, including startup recovery, signup, real policy/approval/export workflows and all-screen desktop/mobile layouts |
| CSV intake and submission checker | Synthetic public fixtures and real engine output | 14 targeted tests pass; malformed headers and corrupted exports are rejected |
| OpenAPI snapshot | Application-generated schema versus checked-in openapi.json | Automated equality test passes |
| Generated frontend models | OpenAPI-derived TypeScript and Zod | Drift check passes; release build enforces TypeScript compilation |
| Repository hygiene | Tracked source/configuration/tests; private original hashes and actual secrets | No original kit artifacts or deployment credentials in the audited staged tree/history |

The Python suite emits one Starlette TestClient/httpx deprecation warning. It does not invalidate passing assertions. PostgreSQL tests operate only against the explicitly named isolated corvo_test database, never the hosted application database.

## Business correctness evidence

| Check | Result | What it establishes |
|---|---|---|
| Supplied worked procurement decisions | All 14 match | Agreement on the disclosed worked cases, including PDF-only contracts and consolidation |
| Supplied supplier-ranking examples | All 3 match | Agreement on disclosed ranking/reference behavior |
| Complete original sample | 186 output rows, 149 requirements, 2 explicit invalid-line outcomes | Full ingestion, stable output cardinality and explainable rejection |
| Contract import | 12 PDFs reconciled with shared register terms; 2 PDF-only contracts loaded | The register is not incorrectly treated as complete |
| Original sample output hash | 9f4352ff8b07a32ce146194d44e336f4470de19c26fc2daba7a4000d55ebd94f | A stable business-output baseline across hardening and deployment checks |
| Boundary/invariant tests | Inclusive grouping/contract dates, nontransitive anchors, exact thresholds, eligible suppliers, deterministic ordering | Targeted behavior under synthetic adversarial cases |

The sample does not provide a complete answer key. Passing all disclosed examples does not prove that every sample decision or future unseen decision matches the evaluator's interpretation. Original assertions and source artifacts stay private.

## Browser and deployment evidence

The browser suite exercises a real isolated FastAPI server and synthetic database. It contains fourteen scenarios: blocked startup resources, visible script-failure recovery, role-password autofill, individual signup/re-login, CSV/policy/approval/export workflows, chat confirmation, manual contract proposals, all-screen desktop/mobile layouts, validation/outage behavior, unresolved amendment reconciliation, session revocation, throttling and pagination.

All eleven screens have desktop/mobile captures at 1440px and 390px, horizontal-overflow checks and visual inspection. The custom Arena 3D scenes remain; the hero's opaque shader, oversized composition and overlapping inset/caption issues were corrected. Startup recovery was additionally checked with denied localStorage, blocked external fonts and a deliberately blocked entry script.

Actual hosted checks are separate from these local browser tests:

| Hosted environment | Verified behavior |
|---|---|
| Isolated Vercel preview + Neon | Original CSV, authenticated export/replay, amendment lifecycle/comparison (48 affected lines), chat confirmation, PO approval, sourcing override, supplier export, contract upload and audit. Test policy withdrawn afterward |
| Public Vercel production + Neon | Eleven screens; original sample/hash; authenticated 13-column export; ranking; logout revocation; exclusively same-origin API calls; no normal browser exceptions |
| Public production redeployment | A preexisting run retained its hash and replayed after a new release; database persistence is independent of the function filesystem |
| Public submission-access release | All role passwords visibly autofill; Admin login and mobile requester signup/re-login work; temporary test account disabled afterward |
| Public startup-recovery release | Missing previous-release asset returns 404 JSON; HTML uses no-store; blocked fonts/storage permit sign-in; failed entry download exposes recovery; reload restores sign-in |

Production synthetic purchase commitments were avoided. Mutable purchasing verification used the separate preview database. The hosted application uses the same reviewed FastAPI backend, with persistent PostgreSQL and same-origin frontend requests.

## Blind-test rehearsal and export preflight

A private API rehearsal used all 186 sample-derived lines with altered PR identities and quantities. A five-part text amendment changed spot/RFQ limits, the grouping window, a scoped plant/category rule and the RFP supplier count. Upload, simulation, review, approval, activation, reprocessing and three exports completed through unchanged application APIs.

The amendment changed 55 line outcomes. Both runs had the same input hash, both replays matched, repeating v5.0 remained unchanged, and all chosen/suggested suppliers were Active. The preferred export contained 155 rows across 68 items with eligible relationships; catalog items with no qualifying preferred supplier legitimately had no ranking row.

The standalone read-only checker accepted all three rehearsal files with supplier-status validation. Its corruption tests cover lost/duplicate PR lines, policy mismatch, invalid decimals, blocked suppliers, inconsistent repeated requirements, wrong headers and malformed preferred ranks. It checks output integrity rather than recalculating routing, quantities, effective dates or as-of-date correctness.

## Limits of the evidence

- The actual blind batch and amendment have not been received; submission/ contains no fabricated evaluator outputs.
- Controlled-language parsing is bounded. Unsupported clauses require faithful structured authoring and explicit review.
- No unrestricted LLM, OCR, cryptographic signature verifier, corporate SSO/MFA/recovery or external PO fulfillment is claimed.
- Shared submission Admin access is deliberately public and requires an operational preflight before the timed assessment.
- Exhaustive load, fault-injection and penetration testing have not been performed. The 20,000-row API bound is not a hosted throughput guarantee; Vercel's payload limit is 4.5 MB.
- The assessment form, code freeze and timely output-only Git push remain human obligations. The submission procedure is summarized in README.md.

## Synthetic demo isolation

Five backend regressions check calculated demo responses against the real engine, quantity-sensitive outcomes, CSV fidelity, authentication, assessment-record isolation and the 200-row demo limit. The real-browser demo scenario calculates nine rows, downloads a synthetic export, uploads an edited demo CSV, verifies the changed route and confirms unchanged live overview data. The demo uses fictional input data rather than precomputed output fixtures.

The public production browser check also passed: nine computed demo rows spanning eight route families, authenticated synthetic CSV export, changed-quantity RFP routing, identical live overview and contract-register responses before/after, unchanged assessment sample hash and zero browser exceptions. Live OpenAPI matches the checked-in schema.
