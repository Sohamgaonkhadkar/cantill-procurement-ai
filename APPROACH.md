# Engineering approach and AI disclosure

Corvo was built around the assessment's highest-risk requirement: the same frozen application must process an unfamiliar batch under v5.0, accept an amendment as reviewed policy data, and produce a second explainable result without source changes. The interface is an operational client of that engine, not the place where procurement rules live.

## Implementation strategy

1. Inspect the brief, policy, worked examples, CSV schemas and contract PDFs privately. Record ambiguities before choosing behavior.
2. Implement a transport-independent deterministic engine with exact arithmetic and explicit tie rules. Use synthetic tests for public regressions and private checks for supplied examples.
3. Represent conditions, priorities, thresholds and time windows as validated, versioned policy data. Separate amendment interpretation from approval and activation.
4. Persist recommendations and snapshots before building approval workflows. Treat actual commitments as transactional writes with independent safeguards.
5. Integrate Arena's exported React/TypeScript/Vite interface against the actual OpenAPI contract. Preserve its visual components while replacing incorrect adapters, models and mock assumptions.
6. Verify browser-to-API-to-database behavior locally and on hosted infrastructure. Treat a passed build as a compilation result, not proof of a complete workflow.

## Why these architectural choices

| Choice | Reason | Tradeoff |
|---|---|---|
| Python/FastAPI and Decimal | Typed transport, document tooling and precise financial calculations | Python hosting must respect serverless limits |
| Explicit first-match DSL | Safe, inspectable conditions and controllable precedence | New rules are limited to registered facts and supported operations |
| Conservative text compiler | Never silently pretend to understand an unsupported clause | Complex wording requires structured human review |
| PostgreSQL plus SQLAlchemy/Alembic | Durable transactions, row locks, source relationships and repeatable schema evolution | More setup than an in-memory prototype |
| Relational identities plus JSON snapshots | Enforce commitments while preserving detailed historical evidence | Some evidence is intentionally denormalized |
| React/Vite with a generated API client | Keep Arena's visual design and make transport drift detectable | Generic responses need supplemental runtime validators |
| Same-origin Vercel deployment | One public application URL with no production localhost fallback | The platform's 4.5 MB payload limit is below the portable API limit |
| Separate production/preview databases | Exercise mutable approval and policy flows without contaminating the evaluation workspace | Both environments require migrations and configuration |

Detailed algorithms, business invariants and an illustrative policy rule are in SOLUTION_DESIGN.md. DECISIONS.md records policy interpretations and why alternatives were rejected.

## Deterministic execution and data lineage

A recommendation is a function of input rows, a master-data snapshot, selected effective policies and explicit version selection. Stable IDs and hashes make repeated input distinguishable from changed data. Replay uses saved snapshots, not the latest supplier register or current policy. Policy governance and purchase commitments remain separate from the original recommendation.

The application records intermediate matching, grouping, valuation, contract, rule and ranking evidence. Approval rechecks current headroom transactionally because an accurate historical recommendation can still become stale before execution. Simulation and export never consume live ceiling.

## Frontend integration discipline

The exported Arena frontend was a visual foundation. Its API assumptions were replaced with actual endpoints and OpenAPI-generated TypeScript/Zod schemas. All eleven workspaces use real data, authenticated downloads, backend pagination and explicit run IDs. Financial values remain decimal strings. There is no production mock fallback or browser-side procurement evaluator.

Visual verification covered desktop/mobile layouts, navigation, captions and the custom 3D scenes. A reproduced stale-asset failure led to correct missing-asset responses, nonblocking external fonts, inline startup recovery and a React error boundary. Browser verification now includes blocked storage/fonts and failed entry-script recovery.

## Validation method

Public tests use synthetic fixtures. The original kit, extracted source text, worked-example assertions, sample exports, screenshots and deployment credentials remain private and ignored. Tests cover exact boundaries, fixed-anchor grouping, non-Active supplier exclusion, contract allocation, policy governance, replay, ownership, revocation, throttling and independent PostgreSQL contention.

The blind-test rehearsal used sample-derived altered PR identities/quantities and a new five-part amendment through unchanged API endpoints. It produced all three exports, changed 55 line outcomes and replayed both runs exactly. This validates a procedure; it does not measure unseen evaluator accuracy. VALIDATION.md distinguishes each test environment and its evidence.

## AI tools and authorship

OpenAI Codex assisted with implementation, review, synthetic tests, debugging, documentation and deployment in this workspace. Arena AI generated the frontend visual foundation, which was exported and integrated on 16 November 2026. No other candidate's implementation was copied. No coding subagents were used.

The running backend does not invoke an LLM. Procurement arithmetic and routing are deterministic. Document text extraction uses pypdf within the application; no supplied dataset is sent by the application to an external LLM or document-extraction service. AI assistance does not replace the candidate's responsibility to understand and explain every design choice in the interview.

## Scope boundaries

The implemented system creates internal PO/sourcing records rather than transmitting orders externally. Controlled language interpretation is bounded; scanned policies need transcription and signatures need human verification. Corporate SSO, MFA, password recovery and exhaustive load/security audits are not implemented. Evaluator access uses private individual accounts; privileged public aliases are removed.

## Conversational and presentation extensions

The optional LLM acts as a constrained language interface. It proposes structured fields with literal user evidence and selects from an intent-specific read-only tool registry. Independent validation and the existing procurement engine retain authority. A leased chat turn separates network work from database writes; explicit confirmation is the only path from a draft to `execute_run`.

Retrieval runs locally over reviewed, versioned sources. Source metadata, clause/page identifiers, hashes, visibility and effective dates travel with every citation. The isolated fictional demo can use direct Gemini free-tier generation and embeddings after explicit acknowledgment. Live data stays local. Provider outages, quota limits and unsupported grounding preserve a usable local workflow and are reported as fallback states.

The redesigned interface uses graphite brand surfaces and mineral operational pages, stable grouped navigation and source-first evidence panels. Financial values remain decimal strings. Optional 3D supplements the readable decision trace; it does not encode a second decision algorithm.
