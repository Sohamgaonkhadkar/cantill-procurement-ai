# Deployment target and current state

Authorized repository: https://github.com/Sohamgaonkhadkar/cantill-procurement-ai (public, main).

Authorized Vercel project: `corvo-procurement`, project ID `prj_7RIb7YlCS7VbCwYxK2hkUqhyxKHf`, team ID `team_oZevuRFeSWvyGYcMBdfiQAp5` (team slug `gaonkhadkarsoham2006-5043`). The integrated Arena/FastAPI application is published at **https://corvo-procurement.vercel.app**. Health: **https://corvo-procurement.vercel.app/health**.

Provisioned managed PostgreSQL: `corvo-procurement-db` for production and `corvo-procurement-preview-db` for preview, both on Neon's `free_v3` plan in `sin1` (Singapore). The user completed Vercel CLI authentication and accepted Neon's integration terms. Both databases have migrated schemas, privately imported master/contract data and a verified persisted sample run. Production and preview data are isolated. The production baseline remains v5.0; preview test amendments were withdrawn after verification.

Server-only SESSION_SECRET and all three role passwords are configured as distinct production/preview Secrets. DEMO_MODE is false. Empty CORS_ORIGINS restricts cross-origin calls; the deployed frontend uses same-origin relative API paths. Local recovery/access values are saved only in the ignored `.private/deployment-access.json`, not in public source or documentation. Database connection files are likewise ignored.

The Python function region is pinned to Singapore (`sin1`) to colocate it with the databases. The hardened suite passes on Windows/SQLite and Linux/PostgreSQL (see VALIDATION.md for counts), including a real PostgreSQL concurrent contract-ceiling approval test. Migration 003 adds persistent sessions and login-throttle records. A Vercel-like local HTTP listener backed by managed preview Neon also passed chat, policy lifecycle, batch/export, synthetic purchasing approval, override, audit and replay checks. Actual hosted preview and public production checks also pass, as recorded below.

The Arena frontend is integrated. The release build validates its generated OpenAPI client and TypeScript before compiling assets. A multi-stage Docker build packages the same UI with FastAPI. Local, hosted-preview and public-production browser checks pass.

## Vercel compatibility

Vercel supports a FastAPI ASGI application at the root `app.py` entrypoint. `vercel.json` sets the Python function duration and includes the existing modular backend. Procurement algorithms are unchanged. See [official FastAPI support](https://vercel.com/docs/frameworks/backend/fastapi).

The reviewed Arena frontend builds into `frontend/dist`; its static assets are copied to `public/` for Vercel's CDN. FastAPI serves the built SPA index and supplies safe deep-link fallback routes. `/api/*`, `/health`, `/docs`, `/redoc` and `/openapi.json` remain API routes. API and frontend can share one origin; Arena can then use an empty `VITE_API_BASE_URL`. Actual Vercel builds and browser checks verified the deployed routing.

Serverless differences are handled at the infrastructure boundary:

- PostgreSQL is mandatory on Vercel; ephemeral SQLite fallback is disabled.
- PostgreSQL connection creation performs no local directory writes; PDF processing is in memory and private kit import uses disposable temporary storage.
- Schema migrations and default-policy/role seeds run during the build. Cold starts do not run DDL or insert seeds. PostgreSQL advisory locks serialize migrations and seeding.
- Database connection pools are bounded (2 pooled + 1 overflow per instance), recycled and checked; psycopg automatic prepared statements are disabled for transaction-pool compatibility.
- All purchasing commitments rely on PostgreSQL transactions, row locks and unique source-PR commitments. No in-memory lock is the sole safeguard across instances.
- All durable runs, proposals, chat state, approvals and source evidence live in PostgreSQL. No private task files are bundled in source or deployment artifacts.
- Vercel's request/response platform cap is 4.5 MB even though the portable API permits 10 MiB uploads. The supplied sample batch fits; larger PDFs/batches need splitting or a separately configured direct upload path. See [Functions limits](https://vercel.com/docs/functions/limitations).

## Provisioning order

1. Verify the selected Vercel owner/project. Do not create a second repository or project.
2. Authenticate the local pinned Vercel CLI if needed. Install Neon through the Marketplace for **this project only**, choosing a free plan if available. User completes any account/legal/billing authorization. Do not start a paid subscription without a spending authorization.
3. Ensure production and preview get separate persistent PostgreSQL resources/branches where supported. Configure DATABASE_URL and SSL. Do not log or commit connection strings.
4. Configure SESSION_SECRET, DEMO_MODE=false, REQUESTER_PASSWORD, BUYER_PASSWORD, ADMIN_PASSWORD and exact CORS_ORIGINS in Vercel. Keep private values server-only. Secrets should be marked Secret; never prefix them with VITE_.
5. Inspect and integrate Arena's exported ZIP into `frontend/`; remove live-mode mocks and test all API paths. Preserve backend source, migrations and tests.
6. Run unit/API tests, frontend type/build checks and full UI flows. Regenerate OpenAPI if a transport schema changes.
7. Build a staged Vercel release, run migrations/seed, verify the preloaded private data (import through admin upload only if needed), and smoke-test the actual hosted API. Vercel deployment protection must be addressed through the platform's normal authenticated access or an approved public production configuration.
8. Promote only the tested final integrated application. Check public access and persistence after redeployment. Record the actual URLs and verification evidence here.

Local API: http://localhost:8000. Public API base: https://corvo-procurement.vercel.app (no trailing /api in VITE_API_BASE_URL).


## Hosted release verification — 16 November 2026

Production deployment `dpl_BwHyjpsts9fb7anRqw9oCWv14tVR` runs application commit `af0f30ad932ae84a7ccee4de7f6ed606866da317`. It was built with production environment secrets, staged without changing the public alias, then promoted after a successful build. Public health stayed available during the next release build. Vercel CLI source uploads were used because the Vercel Git connection is not installed; GitHub pushes alone do not currently trigger deployment. Documentation-only commits after this application commit do not alter the deployed code.

- Public Chromium verification loaded all eleven screens against FastAPI, with zero browser exceptions and exclusively same-origin API calls.
- The private sample produced 186 rows / 149 requirements / two invalid lines, with output hash `9f4352ff8b07a32ce146194d44e336f4470de19c26fc2daba7a4000d55ebd94f`. Authenticated 13-column CSV download, replay, supplier ranking and database-backed logout revocation passed.
- A run persisted before redeployment remained readable with the same output hash and successful replay after the new deployment. PostgreSQL data is independent of the function filesystem.
- Hosted preview Chromium checks exercised amendment upload/proposal, simulation, review, approval, activation and before/after comparison (48 affected lines), confirmed chat submissions, PO approval, sourcing override, supplier export, contract upload and audit. The test policy was withdrawn afterward; synthetic purchasing actions used the isolated preview database.
- Public health returns HTTP 200 with database connected and DEMO_MODE false. Business endpoints return HTTP 401 without an application session. Deployment previews retain Vercel Authentication protection.

Private screenshots, reports, exports and access values remain ignored. No original assessment data or secrets were committed or bundled into the frontend.
