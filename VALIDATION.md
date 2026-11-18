# Verification evidence

Reviewed **18 November 2026**. Results describe executed checks, not a predicted assessment score. Private source documents, credentials, master snapshots and rehearsal artifacts remain outside Git.

## Release checks

| Check | Environment | Result |
|---|---|---|
| Complete Python suite | Windows / Python 3.14 / SQLite | **302 passed; 4 PostgreSQL-only skips** |
| Complete Python suite | Linux / Python 3.12 / isolated PostgreSQL `corvo_test` | **306 passed**, including concurrent approval and chat-confirmation tests |
| Browser release gate | Chromium / real isolated FastAPI, SQLite and Vite | **25 passed in the final clean full run (3.7 minutes)** |
| Frontend unit tests | Node test runner | **7 passed** |
| ESLint, TypeScript and Vite build | Retained Arena frontend | Passed; nonblocking large-3D-bundle and dependency-comment warnings remain |
| Container build | Pinned Python dependencies and production frontend | Passed |
| OpenAPI equality and generated client | FastAPI schema / checked-in JSON / generated TypeScript and Zod | Passed |
| Publication hygiene | Staged source and private-artifact/credential scan | Required before publication: repository checker plus private artifact/credential scan; exact outcome is recorded in the release report |

PostgreSQL tests use only the explicitly named disposable `corvo_test` database, with current source mounted read-only. They never drop or reset hosted data. Browser fixtures use synthetic masters. Test counts are not independent accuracy percentages.

## Final targeted freeze pass

The final pass reproduced two Medium issues before changing application code. An explicit supplier-count amendment could silently ignore a mismatched `from` count or interpret an increase as a decrease. Three negative regressions failed before the fix; three equivalent positive instructions passed. Prior count and direction now produce visible conflicts without mutating the policy, while valid instructions preserve other routes.

A real-browser regression also showed that Policy Reactor allowed review while different, unsaved DSL edits were visible. Actions operated on the saved backend definition, which could mislead the reviewer. The editor now identifies unsaved changes and blocks simulation and governance actions until they are saved. Approval remains disabled until the saved definition is reviewed. Inline guidance identifies the next step; original source and unresolved-clause warnings remain visible. The browser regression failed before the fix and passed after it.

A browser-helper `networkidle` wait timed out after Batch Lab had rendered and was removed. Exact-heading, settled-animation, HTTP response and business-result assertions remain. See the browser coverage section for the retained failure history.

No procurement algorithm, API schema, database migration, dependency, workspace protection or visual redesign was introduced in this pass. The targeted business suite passed 94 checks covering unfamiliar wording, precedence, effective dates, exhausted and competing contracts, supplier eligibility, fixed-anchor grouping and exact financial boundaries. Full-suite and final hosted results are recorded below and in the release report. No further speculative change is recommended after the release gates pass.

## Evidence presentation verification

The shared evidence viewer now presents labeled fields, readable record tables and expandable sections across all workflow pages. Exact JSON remains available in an explicitly labeled technical view. Decision X-Ray separates policy, matching clause, valuation source, grouped PR lines, commitment scope and exact group value. A real-browser regression checks the labeled evidence, optional raw source and desktop/mobile overflow. This presentation-only change preserves backend schemas, decimal strings and original outputs; its then-current 23-scenario browser suite, frontend unit tests, lint, type checking and production build passed.

## Evaluator polish, 18 November

All eleven workspaces were inspected on the canonical site at 1440- and 390-pixel widths: no page overflow or browser page errors. Two presentation defects were reproduced before editing: the five-row CSV preview rendered as nested lists rather than columns (4,144 pixels tall), and twelve policy versions produced an unbounded 1,438-pixel register. The preview now uses a keyboard-scrollable semantic table, preserving quoted fields and decimal text. The version list has its own bounded scroll region; every version remains selectable. Both new real-backend browser regressions failed against the old presentation and passed after the fix. Their fixtures seed policies before sign-in to avoid client-cache timing.

No procurement algorithm, schema, migration or dependency changed. The original sample hash and all disclosed outcomes still match. All three frozen-rehearsal exports also pass independent validation under the recruiter-required filenames, with no missing-evidence warnings. The README verification count, demo/assessment access wording, media credits and submission filenames were reconciled with the implementation.

## Final zero-regression audit

The submission checker reproduced three calendar-evidence failures: CSV-only validation assumed every Run 2 row used the amendment; a captured calendar run could be accepted as the original baseline; and duplicate invalid identities crossing an effective date lost one captured version. The checker now requires captured pinned v5.0 baseline and the requested Run 2 calendar endpoint, preserves duplicate-line evidence, and verifies complete captured CSV contents. Without snapshots it reports calendar-version verification as unavailable rather than inventing an all-amended expectation. Missing policy versions on actionable rows remain hard failures. Negative cases reject a changed per-line version, wrong baseline and wrong endpoint. These regressions failed before the respective corrections; all 19 targeted validation/rehearsal checks pass. No financial output was edited to satisfy validation.

A separate fresh-browser rehearsal used a disposable local database initialized from the private assessment masters. Eleven unfamiliar requests crossed a 15 November policy boundary. The six-clause amendment changed a monetary threshold, grouping window and ranking weight, introduced a plant rule, and required one manually authored normal-category inclusive interval with explicit priority ahead of contracts. All five recognized clauses and the unresolved clause were reconciled through the existing UI. Preview, saved-definition review gates, calendar simulation, review, approval and activation completed without application-code changes during the rehearsal.

Both actual browser exports contain eleven rows, including one invalid outcome. Six lines change and five remain unchanged; the 11-day grouping boundary, other-plant isolation, emergency contract routing and Capex route were checked explicitly. Both immutable snapshots replay exactly, and simulation matches Run 2. The dated all-item preferred export contains 155 rows across 68 eligible items. Independent checks of both runs, masters and preferred metadata pass without warnings. No purchasing approval/override or sourcing commitment occurred. Tokens remain in memory: a new tab and refresh require sign-in. A prepared private read-only capture helper reproduces all three browser downloads byte-for-byte.

Disposable local load checks passed 2,500 grouped lines (one requirement) and 1,000 distinct requirements. Identical retries reused runs, repeated CSV downloads matched and replays succeeded; concurrent health probes remained responsive. These local timings are not Vercel capacity guarantees. Current production acceptance and the exact matched deployment SHAs are recorded separately after release.

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

## Eight-line API regression rehearsal

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

The twenty-five scenarios cover single-page role/individual login, demo-only autofill, signup, startup recovery, real CSV/policy/approval/export workflows, clause reconciliation, all eleven desktop/mobile screens, errors/outages, revocation, throttling, pagination, distinct-reviewer sourcing approval, focus handling and the 3D/2D alternative. Coverage also exercises spoken quantities, corrections, ambiguous weekdays, the exact-text policy handoff, calendar mode, client rejection above the upload limit, the tabular CSV preview and selection within a long policy register.

Earlier overlapping build/database/browser runs produced setup timeouts and exhausted the long rehearsal's original 120-second budget after processing. The rehearsal now allows 300 seconds and the chat action 45 seconds; business assertions remain unchanged. The accepted full runs execute separately from build/database stress, with trace recording disabled. A signup fixture label was corrected, and a run interrupted by schema regeneration was discarded. These harness corrections do not establish a hosted latency guarantee.

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

A later concurrent hosted check exposed delayed export/retry requests and one client timeout on a 2,500-line batch. Subsequent serial export and identical-request retry recovered the same saved runs. A controlled regression reproduced synchronous database work blocking the asynchronous batch handler: `/health` could not respond while that work waited. Batch parsing and the complete database transaction now run together in a worker thread, preserving atomic grouping and ceiling allocation while allowing unrelated requests to proceed. The regression fails before this transport fix and passes after it. Concurrent hosted latency remains resource-dependent; the final release report records the post-deployment results rather than treating earlier sequential timings as concurrency guarantees.

Injected database connection failures and pool timeouts return retryable 503 responses with `Retry-After: 5`, conceal connection details, and recover without duplicate runs. Actual platform/function failure beyond tested workloads is not exhaustively fault-injected.

## Evaluator access and publication

The exact public hostname is [corvo-procurement.vercel.app](https://corvo-procurement.vercel.app), with a public [health endpoint](https://corvo-procurement.vercel.app/health). Fresh unauthenticated browser checks reach the application login without Vercel account access. Built-in roles use the isolated fictional database through the same website; private evaluator credentials use the assessment database. Public signup now creates fictional-demo Requesters only. Hosted assessment self-registration is rejected even with a mistaken enabling flag. Legacy self-registered assessment sessions are denied; owner-provisioned individuals remain authorized. Public demo Admins cannot administer identities or replace master data.

The evaluator uses Admin role with evaluation scope: policy and procurement workflows are available, while account administration and bulk master replacement return 403. Anonymous export and cross-workspace tokens are rejected. Credentials stay private; delivery cannot be inferred from automated access tests. No separate credential-email requirement is claimed. They are not embedded in the public URL, repository or frontend. The URL-only form is not treated as a credential channel.

The final release report records the full GitHub SHA and both Vercel deployment SHAs from deployment metadata. Publication is accepted only when these match and canonical-host smoke checks pass. Canonical release acceptance additionally requires the original-data hash, authenticated exports/replay, workspace boundaries and fresh-browser checks on that exact deployed commit. The final release report records those outcomes rather than embedding a self-referential commit hash here.

## Assurance limits

Unseen accuracy is unmeasured. Arbitrary language, unregistered business facts, scanned-document authenticity, exhaustive penetration testing, unlimited hosted capacity, corporate SSO/MFA/recovery and external supplier dispatch are outside this evidence. Optional free services can throttle or cold-start. A human reviewer must still compare each unfamiliar amendment with its executable DSL and inspect consequential route changes.
