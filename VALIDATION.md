# Executed verification

Verification date: 16 November 2026 (Asia/Kolkata client context). Results below distinguish executed checks from pending deployment/integration work.

| Check | Actual result |
|---|---|
| Synthetic Python unit/API/migration/serverless suite on Windows, Python 3.14, SQLite API fixtures | **69 passed** |
| Synthetic suite on Linux/Python 3.12 with API fixtures using isolated PostgreSQL `corvo_test` | **69 passed**, including final persistence batching, stable historical run IDs, invariant/serverless and deployment adaptations |
| Full sample batch | 186 output rows, 149 requirements, 2 explicit invalid-line outcomes |
| Worked procurement examples | All 14 privately checked against original source examples, using exact rates instead of presentation rounding |
| Worked supplier rankings | All 3 privately checked and matched |
| Contract audit/import | All 12 signed PDFs extracted; shared register terms verified; 2 PDF-only contracts loaded |
| Real local Docker/PostgreSQL HTTP flow | Passed health, authentication, sample CSV, exports, replay, amendment proposal/simulation/review/approval/activation/reprocess/comparison, ranking, contract PDF upload, CORS and API docs |
| No-code amendment demonstration | A labeled test spot-threshold amendment changed 48 sample PR-line outcomes; original run replay remained unchanged |
| API restart persistence | Existing PostgreSQL run and output hash survived API container restart; deterministic replay passed |
| Migration lifecycle | Clean SQLite upgrade, repeated upgrade, table comparison and downgrade passed; PostgreSQL initialized by Docker migrations |
| Repository privacy | Staged-tree hygiene passed before initial push: 52 source/config/test files; no original kit files or obvious credentials. Original kit, extracted text, private regressions/results, databases, environment files and CLI tooling remain ignored |
| OpenAPI synchronization | Checked-in schema matches live application's generated schema in automated test |
| Compilation | `python -m compileall -q backend scripts` passed |
| Docker configuration and startup | `docker compose config --quiet` and actual `docker compose up --build -d` passed |
| Managed Neon PostgreSQL | Separate production and preview free-plan databases in Singapore provisioned. Both migrated and privately initialized with 73 items / 12 contracts; each persisted 186 sample outputs and replayed with the same business hash. This verifies database access, not a hosted Vercel HTTP deployment |
| Vercel environment configuration | Distinct production/preview session and role Secrets configured; DEMO_MODE=false and same-origin CORS configuration set. Credentials were not printed or committed |
| Managed-preview HTTP workflow | Passed through a local HTTP listener using Vercel-like startup, secure preview credentials and remote Neon persistence: sample CSV, amendment simulation/review/approval/activation, comparison (48 affected lines), historical replay, chat confirmation, actual synthetic PO approval, duplicate rejection, sourcing override, rankings, exports, contract upload and audit. The test amendment was deactivated afterward; production purchasing records were untouched |

The suite reports one Starlette deprecation warning concerning its httpx TestClient compatibility adapter. It does not affect the passing assertions. Original worked-example fixtures and exported sample results remain private and are not included in the public tests.

## Still unverified or incomplete

- Arena's exported React frontend has not yet been received or integrated. No frontend build, type check, browser workflow or final UI quality claim is made.
- Vercel project creation is verified; final application deployment is intentionally blocked until the reviewed Arena frontend is integrated.
- Public hosted HTTP smoke checks are pending. Managed database access from this workstation does not establish Vercel-runtime connectivity.
- Full multi-process serverless concurrency, enterprise identity/employee isolation, OCR and cryptographic PDF verification are not claimed.
- No blind-test batch or amendment has been received. `submission/` contains no fabricated CSV outputs.

See `DEPLOYMENT.md` for the authorized repository/project and the exact remaining release sequence.
