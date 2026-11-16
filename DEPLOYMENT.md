# Deployment target and current state

Authorized repository: https://github.com/Sohamgaonkhadkar/cantill-procurement-ai (public, main).

Authorized Vercel project: `corvo-procurement`, project ID `prj_7RIb7YlCS7VbCwYxK2hkUqhyxKHf`, team ID `team_oZevuRFeSWvyGYcMBdfiQAp5` (team slug `gaonkhadkarsoham2006-5043`). The project exists; a final application deployment has **not** been published.

Provisioned managed PostgreSQL: `corvo-procurement-db` for production and `corvo-procurement-preview-db` for preview, both on Neon's `free_v3` plan in `sin1` (Singapore). The user completed Vercel CLI authentication and accepted Neon's integration terms. Both databases have migrated schemas, privately imported master/contract data and a verified persisted sample run. Production and preview data are isolated. Only v5.0 is initially active in each managed database.

Server-only SESSION_SECRET and all three role passwords are configured as distinct production/preview Secrets. DEMO_MODE is false. Empty CORS_ORIGINS restricts cross-origin calls; the final frontend is intended to use same-origin relative API paths. Local recovery/access values are saved only in the ignored `.private/deployment-access.json`, not in public source or documentation. Database connection files are likewise ignored.

The Python function region is pinned to Singapore (`sin1`) to colocate it with the databases. The hardened suite passes on Windows/SQLite and Linux/PostgreSQL (see VALIDATION.md for counts), including a real PostgreSQL concurrent contract-ceiling approval test. Migration 003 adds persistent sessions and login-throttle records. A Vercel-like local HTTP listener backed by managed preview Neon also passed chat, policy lifecycle, batch/export, synthetic purchasing approval, override, audit and replay checks. This is not a substitute for the pending public Vercel deployment/browser checks.

The Arena frontend is integrated. The release build validates its generated OpenAPI client and TypeScript before compiling assets. A multi-stage Docker build packages the same UI with FastAPI. Local workflows and original-sample browser verification pass; hosted evidence is recorded after deployment.

## Vercel compatibility

Vercel supports a FastAPI ASGI application at the root `app.py` entrypoint. `vercel.json` sets the Python function duration and includes the existing modular backend. Procurement algorithms are unchanged. See [official FastAPI support](https://vercel.com/docs/frameworks/backend/fastapi).

The reviewed Arena frontend builds into `frontend/dist`; its static assets are copied to `public/` for Vercel's CDN. FastAPI serves the built SPA index and supplies safe deep-link fallback routes. `/api/*`, `/health`, `/docs`, `/redoc` and `/openapi.json` remain API routes. API and frontend can share one origin; Arena can then use an empty `VITE_API_BASE_URL`. The deployed routing still needs an actual Vercel build and browser verification after integration.

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

Current local API: http://localhost:8000. Public app and health URLs are pending verified deployment; no guessed production URL is advertised.
