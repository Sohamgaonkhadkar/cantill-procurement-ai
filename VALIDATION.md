# Executed verification

Verification date: 16 November 2026 (Asia/Kolkata client context). Results below distinguish executed checks from pending deployment/integration work.

| Check | Actual result |
|---|---|
| Synthetic Python unit/API/migration/serverless suite on Windows, Python 3.14, SQLite API fixtures | **124 passed, 1 PostgreSQL-only test skipped** |
| Synthetic suite on Linux/Python 3.12 with API fixtures using isolated PostgreSQL `corvo_test` | **125 passed**, including independent concurrent approvals contending for a contract ceiling, account isolation, session revocation, login throttling, amendment governance, matching/numeric adversarial cases and randomized determinism invariants |
| Full sample batch | 186 output rows, 149 requirements, 2 explicit invalid-line outcomes |
| Worked procurement examples | All 14 privately checked against original source examples, using exact rates instead of presentation rounding |
| Worked supplier rankings | All 3 privately checked and matched |
| Contract audit/import | All 12 signed PDFs extracted; shared register terms verified; 2 PDF-only contracts loaded |
| Real local Docker/PostgreSQL HTTP flow | Passed health, authentication, sample CSV, exports, replay, amendment proposal/simulation/review/approval/activation/reprocess/comparison, ranking, contract PDF upload, CORS and API docs |
| No-code amendment demonstration | A labeled test spot-threshold amendment changed 48 sample PR-line outcomes; original run replay remained unchanged |
| API restart persistence | Existing PostgreSQL run and output hash survived API container restart; deterministic replay passed |
| Migration lifecycle | Clean SQLite upgrade, repeated upgrade, table comparison and downgrade passed; PostgreSQL initialized by Docker migrations. Migration 003 for sessions/throttles verified on both managed databases |
| Repository privacy | Staged-tree hygiene passed before initial push: 52 source/config/test files; no original kit files or obvious credentials. Original kit, extracted text, private regressions/results, databases, environment files and CLI tooling remain ignored |
| OpenAPI synchronization | Checked-in schema matches live application's generated schema in automated test |
| Compilation | `python -m compileall -q backend scripts` passed |
| Docker configuration and startup | `docker compose config --quiet` and actual `docker compose up --build -d` passed |
| Managed Neon PostgreSQL | Separate production and preview free-plan databases in Singapore provisioned. Both migrated and privately initialized with 73 items / 12 contracts; each persisted 186 sample outputs and replayed with the same business hash. This verifies database access, not a hosted Vercel HTTP deployment |
| Vercel environment configuration | Distinct production/preview session and role Secrets configured; DEMO_MODE=false and same-origin CORS configuration set. Credentials were not printed or committed |
| Managed-preview HTTP workflow | Passed through a local HTTP listener using Vercel-like startup, secure preview credentials and remote Neon persistence: sample CSV, amendment simulation/review/approval/activation, comparison (48 affected lines), historical replay, chat confirmation, actual synthetic PO approval, duplicate rejection, sourcing override, rankings, exports, contract upload and audit. The test amendment was deactivated afterward; production purchasing records were untouched |

The suite reports one Starlette deprecation warning concerning its httpx TestClient compatibility adapter. It does not affect the passing assertions. Original worked-example fixtures and exported sample results remain private and are not included in the public tests.

The hardening pass increased the synthetic suite from 79 to 125 tests. It covers individual identities and requester ownership, persisted logout/disable/throttling, redacted validation errors, scoped policy upload through activation, unresolved-source review gating, incomplete item specifications, inch/model-suffix matching, numeric resource bounds, manual scanned-contract proposals, randomized input-order invariants and two independent PostgreSQL approval transactions. Private procurement/ranking checks still match the original sample business hash.

The managed-preview HTTP hardening check passed (9 affected sample lines, 269.75 seconds), separately exercising individual requester accounts, cross-user run/export/requirement isolation, persistent logout, login throttling, a scoped plant/category amendment, simulation, review/approval/activation, reprocessing/comparison and historical replay. Synthetic identities are disabled and the test amendment withdrawn afterward. This uses a local listener with a remote preview database; it is not a public deployment test.

## Still unverified or incomplete

- Arena integration, TypeScript/production builds and real-backend browser workflows pass locally; see INTEGRATION_REPORT.md.
- Vercel project creation is verified; hosted application verification is tracked in DEPLOYMENT.md.
- Public hosted HTTP smoke checks are pending. Managed database access from this workstation does not establish Vercel-runtime connectivity.
- Exhaustive serverless load testing, corporate SSO/MFA, OCR and cryptographic PDF verification are not claimed. Individual employee account isolation and PostgreSQL transaction contention are tested.
- No blind-test batch or amendment has been received. `submission/` contains no fabricated CSV outputs.

See `DEPLOYMENT.md` for the authorized repository/project and the exact remaining release sequence.

## Arena integration verification

All nine Playwright scenarios pass against isolated real FastAPI/SQLite: CSV/export/replay, approvals, duplicate commitment rejection, sourcing override, policy proposal/upload/simulation/review/approval/activation, chat confirmation and session continuity, manual scanned-contract review, session revocation, throttling, outage states and pagination. All eleven pages were captured and visually inspected at 1440px and 390px with automated horizontal-overflow checks.

The production Vite build served directly by Docker/FastAPI/PostgreSQL separately passed an actual Chromium run over the original private sample: 186 outputs, 149 requirements, two invalid lines, authenticated export, replay and supplier view, with zero browser exceptions. Its output hash remains 9f4352ff8b07a32ce146194d44e336f4470de19c26fc2daba7a4000d55ebd94f. The final image passes 125 PostgreSQL tests; Windows passes 124 with one PostgreSQL-only skip. TypeScript, production build and generated-client drift checks pass.
