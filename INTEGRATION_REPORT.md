# Arena integration verification

16 November 2026. Backend procurement algorithms, migrations and existing tests are preserved.

| Area | Integrated behavior |
|---|---|
| Authentication | In-memory bearer token, real login/logout/revocation, role-aware navigation and route guards, explicit validation/conflict/throttle errors |
| Overview | Persisted counters and latest-run queue, without synthetic savings or performance metrics |
| Request Studio | Server session IDs, corrections, alternatives and explicit confirmation; draft retained within the signed-in session across navigation |
| Inbox / X-Ray | Paginated run-scoped requirements; matching, grouping, valuation, contracts, rule trace and supplier evidence; consolidated scope and reason before action |
| Batch Lab | Exact CSV headers, real upload, history/retrieval, replay, identical-input comparison, issues and authenticated Blob exports |
| Policy Reactor | Schema registry/rule circuit, full DSL editor, registered-fact rules, text/file amendments, preview, simulation, review, approval, activation and withdrawal |
| Policy safety | Source, exact diff and unresolved clauses remain visible; unsupported clauses block ordinary review without explicit reconciliation acknowledgment |
| Suppliers | Item/as-of/policy selection, real components/reference prices, master-based constellation and authenticated preferred CSV |
| Contracts | Paginated register and server ledger values, PDF proposals, source hash/text, manual scanned-document correction and explicit buyer verification |
| Records / Audit | Persisted paginated records, details and decision links, exact audit-action filters; no external dispatch claims |
| Numeric handling | Money stays decimal text; JavaScript does not calculate financial decisions |
| Production API | Empty VITE_API_BASE_URL preserved; no localhost fallback, mock imports or client procurement evaluator |

TypeScript/Zod models are generated from root openapi.json with scripts/generate_frontend_contract.py. Supplemental validators for generic-response endpoints are exercised against real HTTP responses.

Arena's CoreScene, XRayScene, bearing schematic, branding and media components remain. Missing credited images/video were restored from original Pexels sources. Layout fixes cover headline/core separation, expanded navigation, mobile layouts, heading leading and the technical-view toggle. All eleven pages were visually inspected at desktop/mobile widths.

Executed: nine real-backend browser scenarios; 125 PostgreSQL tests; TypeScript/production build; generated-client drift check; production Docker browser test on the private original sample. Screenshots, traces, input artifacts and exports stay in ignored .private/. Hosted evidence belongs in DEPLOYMENT.md.

Remaining boundaries: bounded deterministic language parsing, human reconciliation of unsupported clauses, no OCR/signature cryptographic verification, no corporate SSO/MFA/recovery and no external PO dispatch or supplier invitation service.
