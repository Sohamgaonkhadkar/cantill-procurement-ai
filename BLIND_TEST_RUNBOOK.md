# Blind-test procedure — 19 November 2026

All times are IST. This runbook summarizes the supplied assessment brief; any accompanying evaluator instructions take priority. The actual blind files have not yet been received.

## Before 10:00 AM

Submit the public repository and hosted application links through the assessment form. The brief says only candidates who submit that form receive the blind test. Submission of that form is a separate human step; deployment alone does not submit it.

Open https://corvo-procurement.vercel.app, choose Controlled role account → Admin, and use the automatically filled submission password. Confirm health, catalog data and the v5.0 policy. Keep the app running for the evaluators' later repeat runs.

The owner requested public shared-role submission access. Visitors can therefore perform Admin/Buyer actions. Before the deadline, check policies, imports and purchasing records for unexpected changes; do not assume an open shared workspace stays untouched. Do not approve sample POs or replace master data in the evaluation workspace.

Freeze application code by **10:00 AM on 19 November**. Keep a record of that commit. After the freeze, push only the three required result CSVs, not application fixes, configuration changes or documentation edits.

## Run 1 — supplied batch under v5.0

1. Keep the supplied CSV and amendment outside the tracked repository, for example in ignored `.private/`.
2. In Batch Lab choose policy **5.0**, upload the actual new batch and process it. Do not substitute the sample batch or a rehearsal file.
3. Record the run ID, input hash, policy version, issue count and output hash. Check that every input PR line has an output, including explicitly explained NOT_PROCESSED lines.
4. Export exact CSV and save it as `submission/sohamgaonkhadkar__run1.csv` (use any exact filename the evaluator requests).
5. Use Replay snapshot and confirm a match. Processing and export are sufficient: **do not approve purchasing actions**, which would consume contract ceiling and change the baseline between runs.

## Run 2 — amendment through the frozen application

1. Open Policy Reactor and upload the supplied amendment with its version, base 5.0 and specified effective date. Preserve the original source and inspect every proposed change.
2. Review conditions, numeric operators, priorities, scope, effective dates and parameters. The automatic text interpreter is bounded. If clauses remain unresolved, use the existing rule builder/DSL editor to express them and explicitly verify the manual interpretation. This changes policy data, not application code. Never acknowledge unresolved clauses without implementing and checking them.
3. Preview and simulate against Run 1. Inspect affected decisions and reasons. A zero-change result is not automatically a failure: check the amendment's scope and effective date against the batch rather than forcing a change.
4. Review, approve and activate the version. Approval alone does not activate it.
5. Return to Batch Lab, upload the **same original input bytes**, and select the amended policy version. Process and export `submission/sohamgaonkhadkar__run2.csv`.
6. Confirm Run 1 and Run 2 have the same input hash. Compare their outcomes, inspect explicit invalid-line reasons, and replay both snapshots. Do not edit output values by hand.

## Preferred suppliers and final push — before noon

1. In Supplier Constellation use the evaluator's **exact as-of date** and requested policy version, not today's date. Export the all-item preferred-supplier CSV. Its columns are `item_code,rank,supplier_id,reference_price`; the baseline exports the top three where available.
2. Save it as `submission/sohamgaonkhadkar__preferred.csv`. Check all supplier IDs against Active status and inspect reference-price provenance where needed.
3. Decision exports must have the exact 13 headers documented in FRONTEND_API_CONTRACT.md. Confirm row counts, unchanged PR identifiers, decimal values, clear policy reasons, and consistent shared group/PO IDs. Do not commit private input files, PDFs, passwords, local databases or screenshots.
4. Stage the three actual output files explicitly. Use `git diff --cached --name-only` to verify that only those CSVs are staged, then commit and push to the same public repository **before 12:00 noon IST**. Confirm the three files are visible on GitHub. Late files are not scored.

## Verified preparation and limits

All 14 supplied procurement examples and three supplier-ranking examples match the implementation. A private API rehearsal changed PR identities/quantities, uploaded a five-part text amendment (limits, grouping window, scoped plant/category rule and sourcing supplier count), completed review/approval/activation and produced three valid exports. It changed 55 line outcomes; both replays matched and v5.0 remained reproducible. This was sample-derived rehearsal data, not unseen evaluator data and not an independent accuracy score.

The engine supports new rules composed from registered facts/operators and configurable parameters without code changes. Arbitrary new concepts requiring unmodeled data or engine operations are not guaranteed. Scanned amendment PDFs need transcription; unrestricted language understanding and OCR are not implemented. Vercel's platform request limit is 4.5 MB; the portable API accepts up to 10 MiB. Check file size early and retain the local Docker setup if hosting encounters a platform problem; do not silently split batches, because that changes grouping, consolidation and ceiling allocation.
