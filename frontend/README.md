# Corvo Arena frontend

Arena's React/TypeScript/Vite visual foundation is integrated with the authoritative FastAPI backend. The original Kinetic Core, X-Ray scene, monogram, bearing schematic, cinematic media and motion components are retained.

Run `npm ci`, then `npm run dev` in this directory. The development server proxies `/api` to `http://127.0.0.1:8000`; `CORVO_DEV_API_PROXY` can select an isolated test backend. `VITE_API_BASE_URL` defaults to an empty string for same-origin production requests. There is no live-mode mock fallback or client-side procurement evaluator.

Use `npm run typecheck`, `npm run build` and `npm run test:e2e`. Browser tests start an isolated real FastAPI/SQLite server using synthetic master data, exercise the complete workflows and save evidence under the ignored root `.private/` directory. Install browser binaries with `npx playwright install chromium`. Python dependencies and the repository virtual environment must exist first; `CORVO_PYTHON` can override the Python interpreter.

The exact API contract is [FRONTEND_API_CONTRACT.md](../FRONTEND_API_CONTRACT.md). `src/api/generated.ts` contains TypeScript types and Zod validators generated from root `openapi.json`. Regenerate with `python -m scripts.generate_frontend_contract`; verify with `--check`. Supplemental validators cover endpoints whose OpenAPI response is generic and are checked against actual HTTP responses in browser tests.

Authentication uses in-memory bearer tokens, server logout/revocation and role-aware routes/navigation. Refreshing requires sign-in. Monetary values stay decimal strings, including display formatting; procurement outcomes are never computed in JavaScript. Downloads use authenticated fetch and Blob URLs. Lists use backend pagination and immutable run IDs.

The supplied ZIP omitted all referenced media binaries. The credited Pexels photographs and the same SD hero footage were restored from their original sources. Vite emits cached assets separately rather than embedding the whole application in one HTML file. See ASSET_CREDITS.md for the original credits.
