# Corvo backend contract for Arena

The Python backend is authoritative. Keep all financial decisions in this API. Arena may replace `frontend/` without editing `backend/`, migrations or tests.

Local API origin: **http://localhost:8000**. Interactive reference: **http://localhost:8000/docs**. Machine-readable specification: **http://localhost:8000/openapi.json**; a checked-in copy is at `openapi.json`. No verified public deployment URL exists yet.

Set Arena's local `VITE_API_BASE_URL=http://localhost:8000`. Paths below already include `/api`; do not append it to the environment variable. Configure backend `CORS_ORIGINS` with Arena's exact origin (scheme, hostname and port), comma-separated for multiple origins. Production and preview Vercel environments are configured with an **empty** VITE_API_BASE_URL for same-origin calls. Preserve that empty value; use `import.meta.env.VITE_API_BASE_URL ?? ''`, not a truthiness fallback to localhost. Never put backend passwords or `SESSION_SECRET` in Vite variables.

## Authentication and common conventions

`POST /api/auth/login` accepts JSON `{"role":"admin","password":"corvo-demo"}` and returns `{"access_token":"…","token_type":"bearer","role":"admin","expires_in":28800}`. Roles: `requester`, `buyer`, `admin`. Local demo password for each is `corvo-demo`. In production set `DEMO_MODE=false`, a stable random `SESSION_SECRET`, and separate `REQUESTER_PASSWORD`, `BUYER_PASSWORD`, `ADMIN_PASSWORD`. These are controlled demo accounts, not a corporate identity provider. All business endpoints require `Authorization: Bearer <access_token>`. Keep the token in memory; a reload can require sign-in. Use `GET /api/auth/me` for the current role and demo flag. Hide unauthorized controls but also handle backend 403 responses.

Requests use JSON unless stated as multipart. Do **not** set Content-Type when sending browser `FormData`; the browser must supply the multipart boundary. Downloads require the same bearer header; fetch a Blob and create an object URL rather than linking to an authenticated endpoint directly.

Errors use `{"error":{"code":"VALIDATION_ERROR","message":"…","details":[]}}`. Codes include `HTTP_401`, `HTTP_403`, `HTTP_404`, `HTTP_409`, `HTTP_413`, and `CONFLICT`. HTTP 422 means invalid request, CSV schema, policy facts/operators, or domain values. HTTP 409 means action conflicts, duplicate identities, missing review/approval, or changed contract headroom. CSV business-row validation is returned as a **successful run with issues and NOT_PROCESSED rows**, not an HTTP error. Unexpected server errors must display a retryable error state; never substitute mock results.

Money and quantities are decimal **strings**. `group_value_inr` rounds half-up to 2 decimals for display/export. `unit_price` preserves source rate precision with at least 2 decimals. Evidence retains exact unrounded values. Never recompute procurement outcomes using JavaScript numbers. Dates are ISO `YYYY-MM-DD`; PR `created_at` is local Asia/Kolkata time; audit timestamps include UTC offsets. Empty CSV-compatible values are `""`, not `null`. Optional evidence fields can be `null`.

Pagination: `offset=0`, `limit=50` by default, response `{"items":[…],"total":149,"offset":0,"limit":50}`. Maximum limit is 100, except preferred suppliers (500); runs default to 25. Read `total` to enable next-page controls. Results currently paginate in application memory; this is appropriate for the supplied assessment scale.

IDs are opaque and case-sensitive. Runs: `RUN-…`; requirements: `REQ-…`; planned POs: `PO-…`; chat sessions: `CHAT-…`; contract proposals: `CP-…`. Requirement IDs are stable across runs, so a requirement action **also requires `run_id`**. `record_id` is the composite `run_id:requirement_id`. Use the query parameter rather than guessing a composite path.

## Screen mapping

| Screen | Primary reads | Actions |
|---|---|---|
| Overview | `/api/overview`, `/api/runs` | Navigate to real latest run |
| Request Desk | `/api/master-data`, `/api/chat/sessions/{id}` | `/api/chat/messages` |
| Buyer Inbox | `/api/requirements` | Approve or override |
| Decision Trace | `/api/requirements/{id}?run_id=…` | Inspect evidence; approve |
| Batch Lab | `/api/runs`, `/api/runs/{id}` | Upload, replay, export, compare |
| Policy Studio | `/api/policies`, `/api/policy-schema` | Upload, edit, preview, simulate, review, approve, activate |
| Supplier Intelligence | `/api/preferred-suppliers` | Change as-of date/item; export |
| Contract Vault | `/api/contracts`, `/api/contracts/proposals` | PDF upload, correct extracted contract, approve |
| Purchase Orders | `/api/purchase-orders`, `/{id}` | Inspect approved PO and its requirements |
| Sourcing | `/api/sourcing`, `/{id}` | Inspect approved sourcing request |
| Audit Trail | `/api/audit` | Filter action and paginate |

## Batch Lab and run schemas

`POST /api/process-batch` multipart fields: `file` (CSV, required), `policy_version` (optional string, e.g. `5.0`). Omit version for automatic dated selection. Upload maximum 10 MiB and 20,000 PR lines. Input CSV headers:

```text
pr_no,pr_line,created_at,requester,department,plant,item_code,description,quantity,uom,estimated_unit_price,need_by_date,urgency
```

Returned `RunResponse`:

```typescript
type Run = {
  id: string; created_at: string; actor: string; status: 'completed';
  input_hash: string; data_hash: string; policy_hash: string; output_hash: string;
  explicit_policy: string | null; policy_snapshots: Policy[];
  input: Record<string,string>[];
  rows: DecisionRow[]; requirements: Requirement[]; orders: PlannedOrder[];
  allocations: Record<string,string>;
  issues: {pr_no:string; pr_line:string; errors:string[]}[];
  counts: Record<string,number>;
};
type DecisionRow = {
  pr_no:string; pr_line:string; resolved_item_code:string; group_id:string;
  po_id:string; decision:'PO'|'SOURCING_REQUEST'|''; route:string;
  supplier_id:string; unit_price:string; group_value_inr:string;
  suggested_supplier_ids:string; policy_version:string; reason:string;
};
type PlannedOrder = {
  id:string; supplier_id:string; plant:string; route:string;
  anchor:string; requirements:string[];
};
```

`counts` counts PR lines by route, not requirements. `allocations` is simulated contract consumption within this run. `orders` are **recommendations**, not approved purchase orders. Batch processing never commits contract consumption.

`GET /api/runs` returns paginated summaries: id, created_at, four hashes, status, counts, explicit_policy, line_count, requirement_count, issue_count. `GET /api/runs/{run_id}` returns immutable `Run`. Repeating identical inputs with the same snapshots returns the stored run. `GET /api/runs/{run_id}/export.csv` downloads the exact 13-column CSV (the DecisionRow fields above, in that order).

`POST /api/runs/{run_id}/replay` has no body; returns `{run_id,matches,output_hash,result}`. It recomputes using the stored data and policy snapshots. `GET /api/runs/{run_id}/compare/{other_id}` returns `Comparison`:

```typescript
type Comparison = {
  affected_lines:number; explanation_changes:number;
  changes:{pr_no:string;pr_line:string;business_changed:boolean;
    changes:Record<string,{before:unknown;after:unknown}>}[];
};
```

Compared fields are route, supplier_id, group_value_inr, group_id, po_id, reason and suggested_supplier_ids. `affected_lines` excludes explanation-only changes. Require matching input hashes in UI when presenting an amendment comparison; the comparison API itself joins shared PR identities.

## Buyer Inbox and Decision Trace

`GET /api/requirements` accepts optional `run_id`, `route`, `status`, `search`, `offset`, `limit`. Search covers item description, item code and plant. Status is `pending`, `approved` or `overridden`. Returns paginated `Requirement` objects, with `record_id` and `run_id`. `GET /api/requirements/{requirement_id}?run_id=…` returns one.

```typescript
type Requirement = {
  id:string; item_code:string; description:string; plant:string;
  created_at:string; need_by_date:string; quantity:string;
  decision:string; route:string; supplier_id:string; unit_price:string;
  group_value_inr:string; suggested_supplier_ids:string; policy_version:string;
  reason:string; po_id:string; approval_status:string;
  lines:Record<string,string>[]; evidence:Evidence;
  record_id?:string; run_id?:string; action_id?:string;
  approved_by?:string; approved_at?:string; override_id?:string;
};
type Evidence = {
  facts:Record<string,string|number|boolean|null>;
  rule_trace:{rule:string;matched:boolean}[];
  valuation:{unit_price:string;source:string;reference:string;quantity:string;
    exact_value:string;lookback_days:number};
  contracts:{contract_id:string;supplier_id:string;rate:string;remaining:string;
    required:string;applicable:boolean;usable:boolean;rejection:string|null}[];
  ranking:SupplierRanking[];
  order_reference:string; selected_contract:string|null;
  group_anchor:Record<string,string>; grouping:string;
  matching:{method:string;confidence:number;error?:string;
    candidates?:{item_code:string;score:number}[]}[];
  po_anchor?:string|null;
};
```

Matching entries correspond in order to `lines`. `rule_trace` ends at the first matching rule; subsequent rules were not evaluated. Contracts include rejected candidates and exact remaining headroom at that stage of the run. `valuation.source` is `contract`, `historical_po`, `item_standard` or `requester_estimate`. **Valuation price and actual PO reference price may differ**; present them separately. Requirement grouping and PO consolidation anchors are separate evidence.

`POST /api/requirements/{id}/approve?run_id=…`: JSON `{"reason":"Buyer reviewed supporting evidence"}`, buyer/admin. Returns `Action` (see below). Approving a PO requirement approves **all pending requirements on the same consolidated planned PO** atomically. Show that scope before submission. Actual contract availability is rechecked under locks. Duplicate PR commitments across runs are rejected. Immutable run recommendations do not change; refetch `/api/requirements` for current approval state.

`POST /api/requirements/{id}/override?run_id=…`: JSON `{"route":"RFQ","reason":"Obtain fresh competitive quotations"}`, buyer/admin. Allowed routes: RFQ, RFP, CAPEX_SOURCING, NEW_ITEM_SOURCING. Returns `Action`, preserves the original recommendation and immediately creates a sourcing request. Direct-PO overrides are intentionally unavailable: a buyer cannot bypass supplier/ceiling checks using an arbitrary order. Reason minimum 5 characters, maximum 2,000. Overrides clear supplier/price/PO fields.

```typescript
type Action = {
 id:string;run_id:string;requirements:string[];recommendations:Requirement[];
 actor:string;approved_at:string;reason:string;status:'approved';
};
```

## Policy Studio

`GET /api/policies` returns `{items: Policy[]}` including full rules, parameters, status, id and governance. `GET /api/policy-schema` returns `{facts,operators,boolean_operators,routes,example}`. Build the visual rule editor from this registry; unknown facts/operators fail validation.

```typescript
type Predicate = {fact:string;op:string;value?:string|number|boolean|null|unknown[]};
type Condition = Predicate | {all:Condition[]} | {any:Condition[]} | {not:Condition};
type Rule = {id:string;priority:number;when:Condition;route:string;reason:string};
type Policy = {
 version:string;effective_date:string;
 parameters:{group_days:number;need_days:number;history_days:number;
   preferred_days:number;po_hours:number;preferred_count:number;
   suggestions:Record<string,number>;weights:{frequency:number;recency:number;
   contract:number;delivery:number;quality:number};
   recency_days:[number,number];frequency_cap:number};
 rules:Rule[];id?:string;status?:'draft'|'approved'|'active'|'superseded';
 governance?:Record<string,unknown>;
};
```

`eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `not_in`, `exists`, `is_null` are supported. Fact values have declared string, Decimal, bool or date types. Money predicates accept decimal strings. Each rule ID and priority must be unique. Lower priority number executes first. Conditions nest to maximum depth 12. Parameters are validated integers, bounded to 10,000; suggestion counts maximum 20. New plant/category rules use `requirement.plant` / `item.category` without backend changes.

`POST /api/policies`: JSON `{policy:Policy,source_text?:string,base_version?:string}` (base defaults 5.0), admin. Creates a unique draft; returns full Policy with id/status/governance/diff.

`PUT /api/policies/{id}`: same body, admin. Updates a draft only; version cannot be renamed. Editing clears review. Approved/active versions are immutable.

`POST /api/policies/upload-amendment`: multipart `file` (.pdf/.txt/.json), `version`, `effective_date` required, `base_version` optional (5.0). Admin. JSON files contain a complete Policy, not a partial patch. Returns full draft plus `interpretation:{detected_changes:string[],requires_manual_review:true,warning:string}`. PDF/text extraction conservatively proposes explicitly named thresholds; it is **not a general language model**. Always show extracted `governance.source_text`, all detected changes, and an editable visual rule representation. Unsupported clauses require manual structured editing. Do not present unchanged clauses as interpreted successfully.

`POST /api/policies/propose-amendment`: JSON `{text:string,version:string,effective_date:string,base_version?:string}` (base defaults 5.0), admin. Use for policy changes described conversationally in Policy Studio. Returns the same draft/interpretation structure as file upload, and follows exactly the same review/approval/activation path. This endpoint does not create a purchase requisition.

Automatic threshold extraction accepts only a whole unambiguous global-limit statement, such as “Change spot limit to INR 100000”. Scoped, conditional, negated or more complex prose is retained for structured manual rule authoring and does not silently change a global threshold. An empty detected_changes list means no executable rule change was interpreted; a new version/effective date alone does not implement the document's instructions.

`POST /api/policies/preview`: same JSON body as policy creation, buyer/admin. Returns `{valid:true,diff:{path,before,after}[],policy,snapshot_hash}`; does not persist.

`POST /api/policies/{id}/simulate`: JSON `{run_id:string}`, buyer/admin. Returns `{simulation:true,policy_id,base_run_id,result:ProcessingResult,comparison:Comparison}` using the base run's data snapshot. Draft simulation does not activate a policy or persist a purchasing action. Lines earlier than the explicit version's effective date become NOT_PROCESSED; surface this, rather than pretending the policy applied retroactively.

`POST /api/policies/{id}/review`: JSON `{reason:string}`, admin. Marks draft reviewed and returns full Policy. A review is an explicit human acknowledgement of the structured rules and original source.

`POST /api/policies/{id}/approve`: JSON `{reason:string}`, admin. Requires reviewed draft; returns full approved Policy and records approval metadata.

`POST /api/policies/{id}/activate`: JSON `{reason:string}`, admin. Requires approved version. Returns `{id,status:'active',effective_date,scheduled:boolean}`. Active versions are selected by procurement date, not upload time. A future effective version is scheduled; it does not affect earlier requests. Approved-but-unactivated and draft versions never influence ordinary runs. An explicit historical version selection must still be effective on that requirement's date. Restore earlier logic by creating a **new dated version** cloned from the historical rules, then review/approve/activate; do not rewrite history.

`POST /api/policies/{id}/deactivate`: JSON `{reason:string}`, admin. Returns `{id,status:'superseded',explicit_historical_runs_available:true}`. Removes a version from automatic selection; the next dated active policy applies. The superseded version remains available for explicit historical runs and stored-run replay. Use this to withdraw an incorrectly activated amendment, with an audit reason. A superseded approved snapshot can be reactivated. For a new prospective business change, create a new dated version instead.

## Supplier Intelligence

`GET /api/preferred-suppliers?as_of=YYYY-MM-DD&item_code=…&policy_version=…&offset=0&limit=50` requires `as_of`; item/version are optional. Returns a page plus `as_of`, `policy_version`. Items are `SupplierRanking` with extra `item_code` and `rank`:

```typescript
type SupplierRanking = {
 supplier_id:string;name:string;purchase_count:number;last_purchase:string|null;
 contract_history:boolean;reference_price:string;reference_source:string;
 components:{frequency:string;recency:string;contract:string;delivery:string;quality:string};
 score:string;
};
```

Components are weighted points; score is their sum. Only Active suppliers appear. `GET /api/preferred-suppliers/export.csv?as_of=…&policy_version=…` downloads columns `item_code,rank,supplier_id,reference_price` with the configured top count (v5: 3).

## Contract Vault

`GET /api/contracts?as_of=YYYY-MM-DD&offset=0&limit=50` returns a page plus `as_of`. Optional as_of defaults to the current date. Items:

```typescript
type Contract = {
 contract_id:string;supplier_id:string;start_date:string;end_date:string;
 value_cap:string;consumed_value:string;baseline_consumed_value?:string;
 lines:{item_code:string;description?:string;uom:string;rate:string}[];
 provenance?:Record<string,unknown>;
 committed_value?:string;remaining_value?:string;
 supplier_status?:string;valid_as_of?:boolean;
};
```

`consumed_value` in list responses includes register baseline plus actual approvals; `baseline_consumed_value` shows the register amount. `committed_value` excludes the register baseline. Simulated allocations do not enter this ledger.

`POST /api/contracts/upload`: multipart `file` PDF, buyer/admin. Returns `{id,status:'pending_review',contract:Contract|null,source_text,source_hash,validation_error:string|null,signature_verified:false,actor}`. Extraction failures still create a proposal so the buyer can enter corrected structured fields. Scanned/no-text or unreadable PDFs return 422. Never hide validation errors or imply cryptographic signature verification.

`GET /api/contracts/proposals` returns `{items:ContractProposal[]}`, buyer/admin.

`POST /api/contracts/proposals/{id}/approve`: JSON `{contract:Contract,reason:string}`, buyer/admin. Correct structured fields before posting. Validates supplier/item IDs, UoMs, rates, dates and ceilings. Returns persisted Contract. Existing contract IDs return 409; this endpoint does not silently replace binding register records.

## Request Desk

`POST /api/chat/messages`: JSON `{message:string,session_id?:string}`. Returns `{session_id,message,state,alternatives,run:Run|null,messages}`. Messages have `{role:'user'|'assistant',content,timestamp}`. State may contain description, item_code, quantity, plant, need_by_date, urgency, estimated_unit_price, uom, ready and alternatives. Render it as a confirmation card, not as a completed PR.

Maintain session_id across turns. `alternatives` contains `{item_code,description}`; sending an item code selects it. No PR is created until the user sends `confirm`, `yes` or `submit` **after** state.ready. `cancel` / `reset` clear the draft. Corrections update fields. A confirmed request returns a real run and PR lines, which appear in Buyer Inbox. If there are validation issues, show them and retain the draft. Extraction fallback covers industrial specifications, quantities, plant names/codes, ISO dates, weekdays, tomorrow and explicit normal/emergency. It is not unrestricted natural-language understanding. “Next Friday” means Friday of the following calendar week; dates use Asia/Kolkata.

`GET /api/chat/sessions/{id}` returns `{session_id,actor,messages,state}` for the owning demo principal. Never use client-generated decision labels to render a successful request.

## Remaining endpoints

`GET /health` is public: `{status:'ok',database:'connected',demo_mode:boolean}`. Checks database connectivity.

`GET /api/overview`: `{items:number,suppliers:number,contracts:number,runs:number,pending_requirements:number,purchase_orders:number,sourcing_requests:number,latest_run:RunSummary|null}`. Counts come from persisted records. Pending requirements count simulation records across all runs, so use a selected run in Buyer Inbox to avoid presenting replays as fresh purchasing work.

`GET /api/master-data`: `{items:Item[],plants:Plant[],suppliers:Supplier[]}` for real selectors. Item fields: item_code, description, uom, category, item_type, standard_price. Plant: plant,name. Supplier: supplier_id,name,city,categories,status,on_time_pct,quality_rating. categories is a semicolon-separated string. Do not select Blocked/Inactive suppliers for actions.

`POST /api/admin/import-data`: multipart `file` (.zip), admin. Private setup import of the original task-kit layout. Returns `{snapshot_id,items,suppliers,history_rows,contracts}` (counts, not source rows). Maximum compressed upload 10 MiB, expanded size 50 MiB, 250 archive members. Paths, CSV headers, master references and PDF/register consistency are checked. Temporary extraction is removed after import. Repeated bootstrap is idempotent. Once actual PR commitments exist, bulk replacement is rejected with 409. Never send kit data to a third-party mock service or include it in frontend source.

`GET /api/purchase-orders?offset=…&limit=…` and `GET /api/sourcing?offset=…&limit=…` return pages of Action objects. `GET /api/purchase-orders/{id}` and `GET /api/sourcing/{id}` return one Action. These lists contain actual approvals only; use run.orders for simulated planned orders.

`GET /api/audit?action=policy.approved&offset=0&limit=50`, buyer/admin, returns a page of `{id,created_at,actor,action,details}`. Details vary by event. Examples: batch.processed, policy.proposed, policy.edited, policy.reviewed, policy.approved, policy.activation_scheduled, contract.uploaded, contract.approved, chat.message, purchase_order.approved, sourcing.approved, requirement.overridden. Render actual timestamps and values; do not synthesize missing events.

## Integration rules

Use one typed API client, a bearer-token provider, and one error adapter. Refetch affected queries after mutations. Disable duplicate submissions while requests are pending. Keep all mock fixtures behind an explicit disconnected preview mode; live mode must surface empty/loading/error states. Preserve file uploads as binary FormData and export downloads as Blob data. Keep Backend business logic and immutable run evidence intact when integrating Arena's ZIP.

## Verification and limitations

Synthetic engine/API tests and private worked-example regression are executed locally; see `VALIDATION.md` for results. Production and preview managed PostgreSQL are provisioned, migrated and privately loaded; sample persistence/replay is verified through direct database connections. Public Vercel HTTP deployment and Arena browser end-to-end integration remain unverified until the final frontend is available. Authentication currently identifies three controlled shared role accounts; there is no per-employee identity/ownership boundary for run reads. Do not advertise this as enterprise tenancy or SSO. PDF cryptographic authenticity and broad amendment/chat AI extraction are not implemented; human-reviewed structured correction is the supported path.
