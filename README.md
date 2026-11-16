# Corvo Procurement OS

Deterministic procurement decisions, versioned policy amendments, exact contract accounting and auditable buyer workflows for the Cantill assessment. The authoritative backend is implemented here. The premium React + TypeScript + Vite frontend is being developed independently in Arena AI and will connect to this API.

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

This starts PostgreSQL with a named persistent volume and the API at port 8000. Migrations run before the API starts. The root page links to live API documentation; it is an integration entry page, not the final Arena interface. Keep port 8000 free.

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

Local demo roles are `requester`, `buyer`, `admin`, each with password `corvo-demo`. Login issues an eight-hour signed bearer token. Shared roles are a deliberate assessment convenience, not individual employee identity. Startup refuses non-demo mode without a session secret and all role passwords.

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

The text parser handles explicitly named thresholds; it does not claim unrestricted amendment understanding. A structured human-reviewed editor is the reliable fallback. See `GET /api/policy-schema` and `DECISIONS.md` for supported facts and interpretations.

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

`Dockerfile`, `compose.yaml` and `render.yaml` are supplied. The Render blueprint requires private environment variables and an external managed PostgreSQL URL; no resource has been provisioned through it yet. The database must allow the host's connections and retain data across restarts. The API respects `PORT`; route `/health` checks database connectivity. After deploying, import privately, then run batch, amendment, replay, download, contract and persistence smoke checks against the actual HTTPS origin. Configure CORS for Arena's deployed origin. A source repository and hosting destination are still needed for public delivery.

## Blind-test runbook

Complete the repository, hosted application and assessment form before **19 November 2026, 10:00 AM IST**. Freeze application code at that time.

1. Import the supplied blind CSV and process explicitly under v5.0. Save the returned run ID and download `yourname__run1.csv`.
2. Upload the unseen amendment, inspect/correct all structured changes, simulate, review, approve and activate. Process the same CSV with the approved version, respecting the effective date. Download `yourname__run2.csv`.
3. Generate preferred suppliers using the evaluator's exact as-of date. Download `yourname__preferred.csv`.
4. Place only these actual evaluator outputs into `submission/` and commit before **12:00 noon IST**. Do not commit input data or change code after freeze. No fabricated submission files are included.
5. Replay both runs and verify hashes; retain audit evidence and original run IDs.

## Current boundaries

The final Arena frontend, public GitHub remote and hosted end-to-end verification are pending. Shared demo identity is not enterprise authentication. Chat uses a basic local parser. Scanned PDFs need transcription and signatures require human verification. Buyer overrides support safer sourcing routes, not arbitrary direct orders. There are no live supplier integrations or outbound PO dispatches. Approval creates persisted internal purchasing records only.

AI usage and actual architecture are documented in [APPROACH.md](APPROACH.md); detailed business judgments are in [DECISIONS.md](DECISIONS.md).
