# Corvo Procurement OS

Deterministic procurement decisions, versioned policy amendments, exact contract accounting and auditable buyer workflows for the Cantill assessment. The authoritative backend is implemented here. Arena's React + TypeScript + Vite frontend is integrated with this API, preserving its custom 3D scenes, media and visual identity.

Local API: **http://localhost:8000**. API reference: **http://localhost:8000/docs**. Integration contract: [FRONTEND_API_CONTRACT.md](FRONTEND_API_CONTRACT.md). No public hosted URL is verified yet.

```mermaid
flowchart LR
  Arena[Arena React frontend] --> API[FastAPI / OpenAPI]
  API --> Engine[Pure deterministic engine]
  Engine --> Rules[Validated policy DSL]
  API --> DB[(PostgreSQL)]
  DB --> Snapshots[Immutable runs and evidence]
  API --> Governance[Review / Approval / Audit]
  Private[Private CSV / PDF import] --> API
```

## Local Docker setup

Install Docker Desktop, start its Linux engine, then run:

```sh
docker compose up --build -d
```

This starts PostgreSQL with a named persistent volume and the API at port 8000. Migrations run before the API starts. The root page serves the integrated Arena interface, built in a separate Node stage. API documentation remains at /docs. Keep port 8000 free.

Copy `.env.example` to `.env` to customize settings. Compose supplies local-only defaults. Before public hosting set `DEMO_MODE=false`, a random stable `SESSION_SECRET`, three distinct strong role passwords, production PostgreSQL `DATABASE_URL` and the exact frontend `CORS_ORIGINS`. Do not commit `.env`.

## Private data import

The original kit must stay outside Git and Docker images. Extract it under `.private/`. The directory must contain `master_data`, `contracts`, `contracts/pdf` and `pr_batches`. Import through an authenticated admin API (`POST /api/admin/import-data`, original ZIP) or use:

```sh
docker compose exec api python -m scripts.import_kit /app/.private/Cantill_FullStack_Task_Kit
```

The private local directory is mounted read-only into the container solely for this import. PDFs are parsed and register agreement checked, including PDF-only contracts. No source data is embedded in the frontend or image. On a hosted server use the authenticated upload endpoint or a private shell, not a public Git commit. Bulk API import is blocked after purchasing commitments exist.

## Python-only setup

Python 3.11+ is required (local verification used 3.14). From the repository root:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m alembic upgrade head
python -m scripts.import_kit .private/Cantill_FullStack_Task_Kit
python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

Without DATABASE_URL this uses `.private/corvo.db` (SQLite). Set DATABASE_URL to `postgresql+psycopg://user:password@host:5432/database` for PostgreSQL. Import tools and tests work from the repository root; no global Python path change is needed.

## Demo accounts and API use

Local demo roles are `requester`, `buyer`, `admin`, each with password `corvo-demo`. Login issues an eight-hour signed bearer token backed by a revocable database session. Admins can create individual accounts through `/api/users`; requester runs and chat are isolated by identity. Five failed attempts throttle an identity for the remaining 15-minute window. Shared role accounts remain a controlled demonstration convenience. Startup refuses non-demo mode without a session secret and all role passwords.

```sh
curl -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"role":"admin","password":"corvo-demo"}'

curl -X POST http://localhost:8000/api/process-batch \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -F 'file=@/private/path/batch.csv' -F 'policy_version=5.0'
```

Use the returned run ID with `GET /api/runs/{id}/export.csv`, passing the bearer header. Interactive `/docs` supports login, Authorize, upload and JSON endpoints. All required screen APIs and precise evidence schemas are documented in the Arena contract.

## Policy amendments

Upload PDF, text or full policy JSON with a unique version, base version and effective date. Inspect extracted source and the proposed structured conditions. Edit the draft if parsing did not represent every clause. Preview validation, simulate against a stored run, review, approve, then activate. No draft or approved-but-unactivated version affects ordinary processing. Scheduled versions apply only from their effective date. Historical explicit version runs remain available. New plant/category predicates use the existing policy editor/DSL without changing Python.

The controlled text compiler handles named limits, windows, supplier counts and explicit scoped conditions. Unknown clauses remain visible and block ordinary review until a human reconciles the structured rules and explicitly acknowledges manual verification. It does not claim unrestricted amendment understanding. A structured human-reviewed editor is the reliable fallback. See `GET /api/policy-schema` and `DECISIONS.md` for supported facts and interpretations.

## Verification

```sh
python -m pytest -q
python -m compileall -q backend scripts
python -m scripts.export_openapi
docker compose config --quiet
```

Tests use only synthetic public fixtures. Original worked-example checks and original batch outputs remain private. API tests use isolated SQLite databases; real PostgreSQL validation is separate. See [VALIDATION.md](VALIDATION.md) for executed checks and open limitations. Windows sandboxed Python event loops may require local socket access for TestClient; normal local terminals do not have that restriction.

Migrations are frozen schema files in `migrations/versions/`. New changes must add migrations. Do not remove backend tests or migrations to accommodate a frontend export. OpenAPI is generated from application schemas and tested for synchronization.

## Deployment

The public repository is [Sohamgaonkhadkar/cantill-procurement-ai](https://github.com/Sohamgaonkhadkar/cantill-procurement-ai). The Vercel project `corvo-procurement` and separate production/preview Neon PostgreSQL databases have been provisioned. Schemas and private initial data are loaded; secure role/session environment variables are configured. See [DEPLOYMENT.md](DEPLOYMENT.md) for the current target and checks.

`app.py` and `vercel.json` adapt the existing backend to Vercel's Python ASGI runtime. The release build checks the generated OpenAPI client, compiles TypeScript and builds the reviewed Arena frontend. Its Vite build is served from the same origin; purchasing data persists in PostgreSQL, not the function filesystem. Hosted request/response limits are tighter than the portable API upload limit; see the deployment notes. Local browser and production Docker checks pass. Hosted checks are recorded separately in DEPLOYMENT.md.

`Dockerfile`, `compose.yaml` and `render.yaml` also remain available for local deployment or a backend fallback. No Render resource has been created. The API respects `PORT`; `/health` checks database connectivity.

## Blind-test runbook

Complete the repository, hosted application and assessment form before **19 November 2026, 10:00 AM IST**. Freeze application code at that time.

1. Import the supplied blind CSV and process explicitly under v5.0. Save the returned run ID and download `yourname__run1.csv`.
2. Upload the unseen amendment, inspect/correct all structured changes, simulate, review, approve and activate. Process the same CSV with the approved version, respecting the effective date. Download `yourname__run2.csv`.
3. Generate preferred suppliers using the evaluator's exact as-of date. Download `yourname__preferred.csv`.
4. Place only these actual evaluator outputs into `submission/` and commit before **12:00 noon IST**. Do not commit input data or change code after freeze. No fabricated submission files are included.
5. Replay both runs and verify hashes; retain audit evidence and original run IDs.

## Current boundaries

Arena integration and local browser verification are complete. Hosted verification is tracked separately. Individual application accounts are available; corporate SSO, MFA and account recovery are not integrated. Chat uses a bounded deterministic parser and asks for incomplete specifications. Scanned contracts create manual-entry proposals; scanned policies need transcription. Signatures require human verification. Buyer overrides support safer sourcing routes, not arbitrary direct orders. There are no live supplier integrations or outbound PO dispatches. Approval creates persisted internal purchasing records only.

AI usage and actual architecture are documented in [APPROACH.md](APPROACH.md); detailed business judgments are in [DECISIONS.md](DECISIONS.md).

## Frontend development and integration checks

Run `npm ci --prefix frontend`, then `npm run dev --prefix frontend` alongside FastAPI on port 8000. The Vite development proxy forwards /api; production uses an empty VITE_API_BASE_URL for same-origin requests. Run `npm run build --prefix frontend` before serving the SPA directly from Python.

Regenerate the frontend TypeScript/Zod contract with `python -m scripts.generate_frontend_contract`; append `--check` to detect drift. Browser verification: install Chromium with `npx --prefix frontend playwright install chromium`, then run `npm run test:e2e --prefix frontend`. Tests start an isolated real FastAPI/SQLite server with synthetic records. See INTEGRATION_REPORT.md.
