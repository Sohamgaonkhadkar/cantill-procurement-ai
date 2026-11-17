# Blind-test readiness audit

Reviewed **17 November 2026** against the original brief, Procurement Policy v5.0 and disclosed worked examples. This is an evidence-based freeze assessment, not an unseen-accuracy guarantee. Original challenge documents, private credentials and rehearsal artifacts are excluded from Git.

## Release and evaluator access

The repository is public: [Sohamgaonkhadkar/cantill-procurement-ai](https://github.com/Sohamgaonkhadkar/cantill-procurement-ai). Production is [Corvo](https://corvo-procurement.vercel.app), with a public [health endpoint](https://corvo-procurement.vercel.app/health). At the start of this audit GitHub was one documentation commit ahead of production. The audit release must publish the complete verified commit; its full GitHub and deployed SHA values are recorded in the accompanying release report and Vercel deployment metadata.

A fresh unauthenticated Chromium context reached the application's own login without Vercel authentication. The private evaluator identity authenticated with **admin role / evaluation scope**, reached all eleven screens and downloaded an authenticated decision CSV. Its identity-administration and bulk-import requests returned **403**; anonymous CSV access returned **401**. No deployment-protection or access-control changes were necessary. Credentials must be shared privately through the assessment submission channel.

Production database inspection confirmed **Alembic revision 004**, persistent PostgreSQL connectivity and the required knowledge/chat tables.

## Re-executed checks

| Check | Result |
|---|---|
| Windows / Python 3.14 / SQLite | **250 passed, 4 PostgreSQL-only skips** |
| Linux / Python 3.12 / PostgreSQL | **254 passed**, including all independent concurrency tests |
| Full Chromium suite / isolated real FastAPI | **18 passed**, including desktop/mobile workspaces and the new blind rehearsal |
| Frontend unit tests | **7 passed** |
| Type checking, ESLint, Vite production build | Passed |
| OpenAPI snapshot and generated client drift | Passed |
| Disclosed worked decisions / preferred rankings | **14/14 decisions; 3/3 rankings match** |
| Original sample | **186 rows, 149 requirements, 2 explicit invalid outcomes**, unchanged output hash |
| Runtime npm / pinned Python dependency audits | No known advisories at the check |
| Repository artifact and credential checks | Tracked tree and history checked; no original kit artifacts or known private deployment credentials |

The original sample hash is `9f4352ff8b07a32ce146194d44e336f4470de19c26fc2daba7a4000d55ebd94f`. Independent tests include literal monetary boundaries, competing ceilings, fixed-anchor grouping, supplier safety, shuffled-input equivalence and a 500-line mixed-item/plant batch. Tests do not derive expected decisions by calling the engine a second time.

## Unfamiliar amendment rehearsals

New public API regressions cover a nine-clause document: preserved emergency limits, a scoped plant/category rule with an emergency exception, an eleven-day grouping window, ranking weights, supplier and contract exclusions, an effective date and RFQ supplier count. They verify source-text/upload hashes, clause accounting, unchanged unrelated fields, exact boundaries, unchanged historical v5.0 output and all three CSVs.

A separate case deliberately uses unfamiliar wording for an inclusive value interval. Upload reports it unresolved. Review, approval and activation remain blocked until a reviewer saves an actual condition using the existing `all`, `not`, `gte` and `lte` DSL and explicitly verifies the reconciliation. Boundary, other-plant and emergency cases have independently specified outcomes. No DSL extension or procurement-algorithm change was needed.

The browser rehearsal executes the complete workflow over real HTTP:

1. Upload a three-line synthetic batch explicitly under v5.0; download Run 1.
2. Upload four amendment clauses; inspect the unresolved interval and blocked review.
3. Author the interval in Policy DSL JSON, preview, save, simulate, review, approve and activate.
4. Process the exact same bytes under the amended version; download Run 2 and compare.
5. Replay each saved run and export preferred suppliers for the selected version and **19 November 2026**.

| Evidence | Run 1 | Run 2 |
|---|---|---|
| Input hash | `1f7385eb2897d37afc246cc02b828523b262627af31fadb1fb4fc2a673e3bf70` | Identical |
| Output rows | 3 | 3 |
| Independently expected routes | CONTRACT_PO, CONTRACT_PO, SPOT_PO | RFQ, CONTRACT_PO, RFP |
| Saved snapshot replay | Matches | Matches |

There were **zero purchasing approvals or overrides** between these runs. Both decision downloads had the exact thirteen columns. The preferred download had the required four columns, two eligible relationships, the chosen policy version and explicit as-of date. `scripts.validate_submission` accepted all three files with the synthetic Active supplier master. Export integrity is checked separately from the literal routing expectations.

The larger private sample-derived rehearsal also passed again: 186 rows in each run, five policy changes, 55 affected lines, 155 preferred rows and matching input hashes/replays. Neither rehearsal fabricates blind-test submission outputs.

## Findings and fixes

| Severity | Verified finding | Resolution |
|---|---|---|
| Medium | The standalone export checker accepted malformed CSV quoting | Strict CSV parsing with explicit malformed-content errors; two failing regressions now pass |
| Medium | A wrong nonempty policy version escaped checking on NOT_PROCESSED rows | Validate supplied policy versions before the invalid-line branch; existing missing-date/blank-version compatibility retained |
| Low | An occupied policy-rule priority was blocked but classified only as unresolved | Classify it as a conflict, preserving the existing review gate and source evidence |
| Low | The supplier ranking-policy selector lacked a stable explicit accessible name | Add an accessible label and verify the actual export policy/date in the browser |
| Low | GitHub was ahead of the published application by a documentation commit | Publish the final verified source commit and compare its full SHA with deployment metadata before freeze |

The first new export assertion expected `100` instead of the authoritative `100.00`; the new fixture was corrected to assert the exact required formatting. This was a test-authoring error, not a financial-engine defect. Existing assertions were not weakened. No engine algorithms, database migrations or working tests were deleted.

## Remaining risks

- **Medium — bounded interpretation:** arbitrary English is not guaranteed to compile. Unsupported wording requires faithful structured authoring and human review. Rules needing an unregistered business fact or a new engine operation are outside the present DSL; the unseen amendment has not been received.
- **Medium — hosted resource bounds:** the portable API permits 20,000 rows, but maximum-size Vercel throughput has not been load-tested. Its 4.5 MB payload ceiling and execution limits apply. Do not split a real batch into separately processed parts: that can change grouping and ceiling allocation.
- **Low — operational availability:** managed free services can cold-start or throttle. Gemini is optional and disabled for live data; blind-test calculations and amendment governance do not require external AI.
- **Low — broader assurance:** no exhaustive penetration or fault-injection audit is claimed. Dependency results are point-in-time checks, not a security certification.

No unresolved Critical or High defect was identified by the executed checks. The application is a freeze candidate with the limits above; actual unseen accuracy remains unmeasured.

## Freeze and blind-test procedure

Before **19 November 2026, 10:00 AM IST**, finish source changes, run the gates, commit, deploy that exact full SHA, verify public login/processing/export and privately provide evaluator credentials. Submit the public repository and hosted link through the official form; the application does not submit that form.

After freeze, keep application source, dependencies, compiler, tests and documentation unchanged unless official assessment rules explicitly authorize an exception. Apply the received amendment through the existing interface only. Keep the supplied files private.

1. Process the complete unseen batch under explicit **5.0**, export decisions and record run/input hashes.
2. Upload and reconcile every amendment clause; verify priority and effective date, simulate, review, approve and activate.
3. Reprocess the exact same original file under the amended version. Compare matching input hashes and replay both snapshots. Do not approve purchasing actions between runs.
4. Export preferred suppliers for the evaluator's exact as-of date and requested policy version.
5. Run `python -m scripts.validate_submission` using the three actual downloads, original private input, amended version and private supplier master. Independently inspect route changes and eligibility; the checker cannot certify business accuracy.
6. Place only the three actual result CSVs in `submission/`. Review the staged file list to ensure no source/data/credential changes, then commit and push the output files before **12:00 noon IST**. No automatic post-freeze source push is configured.
