# Verification evidence

Reviewed 17 November 2026. Results distinguish pure business checks, API tests, real PostgreSQL transactions, browser workflows and actual hosted behavior. Test counts are evidence of asserted behaviors, not an independent assessment score.

## Current automated baseline

| Check | Environment | Executed result |
|---|---|---|
| Complete Python suite | Windows / Python 3.14 / SQLite API fixtures | **243 passed, 4 PostgreSQL-only tests skipped**, including conversational routing and readable policy answers |
| Complete Python suite | Linux / Python 3.12 / isolated PostgreSQL corvo_test | **233 passed**, including independent approval and chat-confirmation transactions |
| Complete browser suite | Chromium / real isolated FastAPI and SQLite / Vite | **17 passed before Arena visual restoration**, including startup recovery, signup, real policy/approval/export workflows and all-screen desktop/mobile layouts |
| Restored Arena regression checks | Chromium / real isolated FastAPI and SQLite / Vite | **4 targeted checks passed**: isolated-demo autofill, private live credentials and hero layout, chat confirmation, keyboard/focus and 3D-to-2D navigation; build and lint passed |
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

The complete 17-scenario browser suite exercises a real isolated FastAPI server and synthetic database. Coverage includes blocked startup resources, visible script-failure recovery, privileged-password non-disclosure, individual signup/re-login, CSV/policy/approval/export workflows, chat confirmation, manual contract proposals, all-screen desktop/mobile layouts, validation/outage behavior, unresolved amendment reconciliation, session revocation, throttling, pagination, independent two-reviewer sourcing approval and demo isolation. The four targeted Arena checks are a subsequent regression pass, not a second execution of the complete suite.

All eleven screens have desktop/mobile captures at 1440px and 390px, horizontal-overflow checks and visual inspection. The custom Arena 3D scenes remain; the hero's opaque shader, oversized composition and overlapping inset/caption issues were corrected. Startup recovery was additionally checked with denied localStorage, blocked external fonts and a deliberately blocked entry script.

Actual hosted checks are separate from these local browser tests:

| Hosted environment | Verified behavior |
|---|---|
| Isolated Vercel preview + Neon | Original CSV, authenticated export/replay, amendment lifecycle/comparison (48 affected lines), chat confirmation, PO approval, sourcing override, supplier export, contract upload and audit. Test policy withdrawn afterward |
| Public Vercel production + Neon | Eleven screens; original sample/hash; authenticated 13-column export; ranking; logout revocation; exclusively same-origin API calls; no normal browser exceptions |
| Public production redeployment | A preexisting run retained its hash and replayed after a new release; database persistence is independent of the function filesystem |
| Retired submission-access release | Historical only: replaced by private evaluator identities. Public demonstration password aliases remain disabled. Controlled roles require private passwords; requester self-registration is enabled by explicit owner choice |
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
- Private evaluator accounts permit procurement and policy evaluation; only the owner can administer identities or replace master data.
- Exhaustive load, fault-injection and penetration testing have not been performed. The 20,000-row API bound is not a hosted throughput guarantee; Vercel's payload limit is 4.5 MB.
- The assessment form, code freeze and timely output-only Git push remain human obligations. The submission procedure is summarized in README.md.

## Synthetic demo isolation

Five backend regressions check calculated demo responses against the real engine, quantity-sensitive outcomes, CSV fidelity, authentication, assessment-record isolation and the 200-row demo limit. The real-browser demo scenario calculates nine rows, downloads a synthetic export, uploads an edited demo CSV, verifies the changed route and confirms unchanged live overview data. The demo uses fictional input data rather than precomputed output fixtures.

The public production browser check also passed: nine computed demo rows spanning eight route families, authenticated synthetic CSV export, changed-quantity RFP routing, identical live overview and contract-register responses before/after, unchanged assessment sample hash and zero browser exceptions. Live OpenAPI matches the checked-in schema.


## Historical hardening baseline — 16 November 2026

At this intermediate milestone, the PostgreSQL suite contained 204 passing tests. The current counts appear at the top of this document. Added independent expectations cover twelve exact monetary boundaries, competing contract ceilings, a 500-line mixed-item/plant batch with shuffled-input equivalence, unrelated-plant isolation, industrial aliases/mixed fractions and explicit UoM/model protection. These synthetic cases have literal expectations and invariants; they do not import an assessment answer key.

New API/security checks cover private evaluator scope, non-disclosure of legacy privileged aliases, owner-specific run IDs, persisted expiry, malformed CSV quoting, spreadsheet formula injection, operation budgets, exact amendment-upload hashes, direct contract retrieval, manual source reconciliation, stale-policy approval rejection and additional sourcing approvals. Four PostgreSQL-specific tests exercise separate transactions: contract ceiling contention, chat confirmation, policy edit versus approval, and simultaneous distinct sourcing votes.

Seven frontend unit assertions cover quoted CSV round trips, BOM/blank rows, malformed quoting/null bytes and exact formatting beyond JavaScript's safe integer range. ESLint checks TypeScript correctness patterns and React hook ordering; type checking remains an independent build gate. The supported lint toolchain uses a pinned patched minimatch override; dependency audit reports zero known advisories at this check. This is a point-in-time dependency result, not a penetration-test claim.

The amendment compiler accounts for source clauses as proposed, preserved, unresolved or conflicting. Supported additions include exclusions, supplier-ranking weights, RFQ supplier counts, spelled-out grouping windows, scoped thresholds, exceptions and explicit dates. Unsupported text still requires saved structured corrections and a human reconciliation statement; checking a box alone cannot authorize unchanged missing rules.

Recommendation output hashes for the original sample remain unchanged. Additional-approval policies delay sourcing creation until the configured number of distinct reviewers has voted. Policy calendar and catalog locks prevent stale-policy commitments and import/approval races. Every approval still rechecks current financial headroom with Decimal arithmetic.

The final full browser rerun passed all 15 scenarios. A stale effective-date fixture initially hit the intended freshness rejection; correcting the fixture to use the latest policy allowed the quorum workflow to complete without changing its assertions. Both full backend environments then passed: PostgreSQL 204/204, SQLite 200 passed plus four PostgreSQL-only skips. The pinned Python requirements audit also reported no known vulnerabilities.


Hosted sign-in configuration update: both Controlled role account and Individual account are available. The owner explicitly enabled requester self-registration. New users choose their own password, which is hashed and verified by the backend. Admin/Buyer roles cannot be self-registered and no privileged password is returned in authentication options. Controlled role access uses private credentials; retired public aliases remain rejected.


Public demo extension: seven additional backend checks reject non-isolated database configurations, keep public passwords disabled on the live deployment and verify all demo roles remain unable to administer identities. The full backend suite passed 211 cases on PostgreSQL and 207 plus four PostgreSQL-only skips on SQLite. The demo uses a separate restricted PostgreSQL role/schema and session key, not request-based switching of the live connection. Existing migrations initialize that schema; only fictional inputs are seeded through the real engine.

## Gemini and retrieval verification

The additional AI tests cover live-data egress rejection before client creation, fictional-input acknowledgment, private-source provenance, credential/identifier rejection, source review and ACLs, index idempotency, effective policy filtering, source revision isolation, unknown/write-tool rejection, independent field evidence, spoken quantities, negative SKU corrections, citation/numeric guards, distributed budgets, duplicate confirmation and concurrent turn leases. Native embedding tests check 1536-dimensional normalized vectors and label token estimates when the provider omits usage.

Hosted checks call the real direct Gemini API from Vercel Functions using the Sensitive server-side key. Successful generation was observed with `gemini-3.5-flash-lite`, including a current-policy answer with a backend-generated citation. The native `gemini-embedding-001` endpoint embedded eight approved fictional policy chunks; an immediate repeat embedded zero chunks, demonstrating persistent idempotency. Provider 503 responses and rejected grounding were also observed: the application showed local source evidence rather than fabricating success. Free-tier latency and availability are external limitations, not a guaranteed service level.

## Current published interface — 17 November 2026

Both public deployments retain the original Arena palette, typography, navigation, page layouts and custom scenes. Gemini consent, citations, server-session handling, authentication fixes and keyboard focus safeguards are retained. The four targeted browser checks and build/lint results above apply to this interface; the complete 17-scenario run and hosted Gemini workflow preceded the visual restoration. Backend code, migrations and tests were unchanged by that restoration.

The Arena restoration was published in source commit `5a984fe05f943f83aa748fc0ab0ce9beb22bd05c`. Public browser checks confirmed the dark interface, live sign-in, demo-only requester autofill and HTTP 200 health responses on both deployments. Subsequent releases retain this interface.

| Deployment | Application | Health |
|---|---|---|
| Private live workspace | [Corvo](https://corvo-procurement.vercel.app) | [Live health](https://corvo-procurement.vercel.app/health) |
| Isolated fictional workspace | [Corvo demo](https://corvo-procurement-demo.vercel.app) | [Demo health](https://corvo-procurement-demo.vercel.app/health) |

## Conversational routing regression — 17 November 2026

Greetings, acknowledgments and intake-help prompts are handled locally without model calls, retrieval, citations or draft mutation. Questions phrased as purchase requests retain the intake path. A substantive question prefixed by thanks still reaches knowledge routing. Acknowledgments preserve the preceding conversation mode, so thanking a policy answer cannot make a subsequent yes confirm an existing purchase draft.

Seven additional regressions cover the reported messages, provider bypass, draft preservation and confirmation safety. The focused chat suite passed 46 tests with one PostgreSQL-only skip; the complete Windows backend suite passed 236 tests with four PostgreSQL-only skips. The previous PostgreSQL result of 233 is retained as a prior executed baseline; these seven additions have not been rerun against PostgreSQL.

The deployed public demo browser passed greeting, copied intake prompt and thanks checks with no irrelevant citations. A subsequent current-policy question returned a real Gemini response with `ai_status=available`, grounded citations and the `get_active_policy` tool. Thanking that answer preserved knowledge mode, and a following yes created no PR. No browser exceptions were observed. The application release is `0995f1c`; both existing Vercel projects were rebuilt from that release without visual changes.

Follow-up coverage includes quoted combined greetings, the exact phrase "current procurement policy", dynamically rendered policy conditions, altered thresholds and one-generation current-policy retrieval. Local fallback explains actual source values and conditions instead of reporting only that passages were found. Model prose omits internal citation hashes while preserving validated source cards. Seven additional tests passed, bringing the full Windows suite to 243 passed plus four PostgreSQL-only skips; frontend lint and type checking passed.
