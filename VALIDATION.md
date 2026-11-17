# Verification evidence

Reviewed **17 November 2026**. Results describe executed checks, not a predicted assessment score. Private source documents, credentials, master snapshots and rehearsal artifacts remain outside Git.

## Release checks

| Check | Environment | Result |
|---|---|---|
| Complete Python suite | Windows / Python 3.14 / SQLite | **294 passed; 4 PostgreSQL-only skips** |
| Complete Python suite | Linux / Python 3.12 / isolated PostgreSQL `corvo_test` | **298 passed**, including concurrent approval and chat-confirmation tests |
| Browser release gate | Chromium / real isolated FastAPI, SQLite and Vite | **21 passed in the final clean full run (3.2 minutes)** |
| Frontend unit tests | Node test runner | **7 passed** |
| ESLint, TypeScript and Vite build | Retained Arena frontend | Passed; nonblocking large-3D-bundle and dependency-comment warnings remain |
| Container build | Pinned Python dependencies and production frontend | Passed |
| OpenAPI equality and generated client | FastAPI schema / checked-in JSON / generated TypeScript and Zod | Passed |
| Publication hygiene | Staged source and private-artifact/credential scan | Required before publication: repository checker plus private artifact/credential scan; exact outcome is recorded in the release report |

PostgreSQL tests use only the explicitly named disposable `corvo_test` database, with current source mounted read-only. They never drop or reset hosted data. Browser fixtures use synthetic masters. Test counts are not independent accuracy percentages.

## Original-data regression

| Evidence | Result |
|---|---|
| Disclosed procurement examples | **14/14 match** |
| Disclosed preferred-supplier examples | **3/3 match** |
| Complete original sample | **186 outputs; 149 requirements; 2 explicit invalid outcomes** |
| Signed-contract import | 12 PDFs reconciled with register terms; two PDF-only contracts included |
| Business-output SHA-256 | `9f4352ff8b07a32ce146194d44e336f4470de19c26fc2daba7a4000d55ebd94f` |

The private regression was rerun after procurement hardening and retained this hash. No PR-specific answer map or synthetic production-success fallback is used. The disclosed examples do not provide an answer key for every sample row or unseen input.

## Independent business and amendment checks

Synthetic expectations cover exact monetary boundaries, fixed-anchor and nontransitive grouping, earliest eligible anchors, normal/emergency grouping, sequential competing ceilings, exhausted-contract valuation, blocked/inactive suppliers, historical benchmarks, expired contract relationships, PO consolidation, decimal precision, invalid identities, shuffling and large quantities. A literal thirteen-field CSV expectation checks equal-rate contract selection and stable IDs independently of engine helpers.

Mixed-date fixtures use PRs dated 14, 15 and 16 November around an amendment effective on the 15th. They distinguish automatic dated selection, pinned v5.0, pinned amendment applicability and Run 2 calendar processing, then verify exported versions, grouping boundaries and replay. Same-date policy activation tests establish explicit supersession for numeric and descriptive version names.

Amendment tests cover equivalent wording, old-value/direction conflicts, Indian currency notation, exact comparisons, plant/category scope and protected-route precedence. Three unresolved clauses cannot be cleared using one mapping or unrelated parameter edits. Wrong scope, amount, priority, date, missing confirmation and reason-only changes are rejected. Negative/broad predicates and reversed or exclusive inclusive-interval bounds are also rejected. A date-only correction is executable and must match the stated source date. Approval is tied to the reviewed definition hash.

The independent read-only checker imports neither the production engine nor supplier-ranking implementation. With run/master snapshots and preferred-export metadata it recalculates selected arithmetic, membership, calendar, source-price, ranking, ceiling and PO-window invariants. It checks CSV versus snapshot and same-input hashes. Missing evidence produces warnings; failures prevent publication. Natural-language meaning remains a human review responsibility.

## Complete novel rehearsal

Eight lines cover multiple item classes, two plants, normal/emergency requests, a genuinely new item, an invalid quantity and a policy-date boundary. Six source instructions include a plant/category exception and one unsupported inclusive interval. The interval is authored in the existing DSL and reconciled explicitly before review, approval and activation; no application-code edit occurs during the rehearsal.

| Measure | Run 1 | Run 2 |
|---|---|---|
| Input / output lines | 8 / 8 | 8 / 8 |
| Requirements | 6 | 7 |
| Planned consolidated POs | 3 | 3 |
| Invalid lines | 1 | 1 |
| Supplier eligibility failures | 0 | 0 |
| Purchasing approvals / overrides | 0 / 0 | 0 / 0 |

Three lines change. Both input hashes match, both immutable replays match, and both decision CSVs plus the one-row preferred export pass independent validation without missing-evidence warnings. Files are temporary/private and never placed in `submission/`. This is a synthetic rehearsal, not a passed blind test.

## Browser and conversational coverage

The twenty-one scenarios cover single-page role/individual login, demo-only autofill, signup, startup recovery, real CSV/policy/approval/export workflows, clause reconciliation, all eleven desktop/mobile screens, errors/outages, revocation, throttling, pagination, distinct-reviewer sourcing approval, focus handling and the 3D/2D alternative. New coverage exercises spoken quantities, corrections, ambiguous weekdays, the exact-text policy handoff, calendar mode and client rejection above the upload limit.

During release preparation one overlapping build/database/browser run had two browser timeouts; a later complete run passed those cases but exhausted the long rehearsal's 120-second total budget after business processing and cleanup. Its overall budget is now 300 seconds; the new chat test allows 45 seconds for the send action plus its response. Correctness assertions remain unchanged. The final full run passed all 21 scenarios with trace recording disabled to reduce local recording overhead. A new signup fixture's outdated button label was corrected; one in-flight run was invalidated by schema regeneration. The accepted run used unchanged application sources.

Local intake and policy proposals work without Gemini. Chat cannot approve or activate policies. The isolated demo's optional real Gemini integration was verified in earlier hosted checks; this sprint does not introduce a new AI provider or claim that a mocked response proves model availability. Live external-AI access remains disabled.

## Hosted capacity and failure recovery

Real fictional-demo requests to the canonical Vercel deployment produced these measured results during release preparation:

| Rows | Requirements | CSV bytes | Response bytes | Processing seconds |
|---|---|---|---|---|
| 500 | 24 | 83,792 | 650,162 | 1.29 |
| 1,000 | 24 | 168,452 | 1,249,545 | 1.66 |
| 2,500 | 24 | 420,938 | 3,042,986 | 2.68 |
| 500 separate new-item requirements | 500 | 85,557 | 1,482,053 | 1.81 |
| 1,000 separate new-item requirements | 1,000 | 172,092 | 2,970,139 | 2.82 |

Every case passed authenticated export, snapshot replay and identical-request retry with the same run ID. No purchasing commitments were created. These timings are observations, not latency guarantees or a claim that 20,000 rows are hosted-safe.

Client and batch API enforce **4,000,000 CSV bytes**, leaving multipart overhead below the platform request ceiling. A local padded one-line CSV at exactly that boundary succeeds; one extra byte returns 413 and creates no run. This byte-boundary check is separate from realistic workload tests above. Response evidence and group count also affect resource use. Larger/highly fragmented workloads remain unqualified; never split a business batch across independent processing calls because that changes grouping and ceiling allocation.

Injected database connection failures and pool timeouts return retryable 503 responses with `Retry-After: 5`, conceal connection details, and recover without duplicate runs. Actual platform/function failure beyond tested workloads is not exhaustively fault-injected.

## Evaluator access and publication

The exact public hostname is [corvo-procurement.vercel.app](https://corvo-procurement.vercel.app), with a public [health endpoint](https://corvo-procurement.vercel.app/health). Fresh unauthenticated browser checks reach the application login without Vercel account access. Built-in roles use the isolated fictional database through the same website; private evaluator credentials use the assessment database. Public signup now creates fictional-demo Requesters only. Hosted assessment self-registration is rejected even with a mistaken enabling flag. Legacy self-registered assessment sessions are denied; owner-provisioned individuals remain authorized. Public demo Admins cannot administer identities or replace master data.

The evaluator uses Admin role with evaluation scope: policy and procurement workflows are available, while account administration and bulk master replacement return 403. Anonymous export and cross-workspace tokens are rejected. Credentials are handed privately to the recruiter, not embedded in the public URL, repository or frontend. The URL-only form is not treated as a credential channel.

The final release report records the full GitHub SHA and both Vercel deployment SHAs from deployment metadata. Publication is accepted only when these match and canonical-host smoke checks pass. Canonical release acceptance additionally requires the original-data hash, authenticated exports/replay, workspace boundaries and fresh-browser checks on that exact deployed commit. The final release report records those outcomes rather than embedding a self-referential commit hash here.

## Assurance limits

Unseen accuracy is unmeasured. Arbitrary language, unregistered business facts, scanned-document authenticity, exhaustive penetration testing, unlimited hosted capacity, corporate SSO/MFA/recovery and external supplier dispatch are outside this evidence. Optional free services can throttle or cold-start. A human reviewer must still compare each unfamiliar amendment with its executable DSL and inspect consequential route changes.
