import { test, expect, type Page } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

test("blind rehearsal uploads, reconciles, activates and exports the same batch without purchasing", async ({
  page,
}) => {
  // This multi-page rehearsal includes three downloads and full clause review.
  // Keep individual action/assertion deadlines unchanged on slower CI machines.
  test.setTimeout(300000);
  const errors: string[] = [];
  let purchasingActions = 0;
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (
      request.method() === "POST" &&
      /\/requirements\/.*\/(approve|override)/.test(request.url())
    )
      purchasingActions++;
  });
  await page.addInitScript(() =>
    localStorage.setItem("corvo.intro.seen.v1", "1"),
  );
  await page.goto("/");
  await page.getByLabel("Role", { exact: true }).selectOption("admin");
  await page.getByLabel("Password", { exact: true }).fill("corvo-demo");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("navigation", { name: "Primary" })).toBeVisible();
  const folder = path.resolve("../.private/final-blind-browser");
  await fs.mkdir(folder, { recursive: true });
  const csv =
    "pr_no,pr_line,created_at,requester,department,plant,item_code,description,quantity,uom,estimated_unit_price,need_by_date,urgency\n" +
    "SYNTH-A,1,2026-11-01 10:00,Synthetic user,Testing,P-A,ITM-9001,Bearing,8,NOS,,2026-11-20,Normal\n" +
    "SYNTH-B,1,2026-11-01 10:05,Synthetic user,Testing,P-A,ITM-9001,Bearing,8,NOS,,2026-12-15,Emergency\n" +
    "SYNTH-C,1,2026-11-01 10:10,Synthetic user,Testing,P-A,ITM-9002,Hose,4,MTR,,2026-11-20,Normal\n";
  await fs.writeFile(path.join(folder, "input.csv"), csv);
  async function go(label: string) {
    await page.getByRole("link", { name: label, exact: true }).click();
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  }
  async function process(version: string) {
    await go("Batch Lab");
    await page
      .getByLabel("PR CSV file", { exact: true })
      .setInputFiles({
        name: "synthetic-blind.csv",
        mimeType: "text/csv",
        buffer: Buffer.from(csv),
      });
    await page.getByLabel("Batch policy version").selectOption(version);
    const pending = page.waitForResponse(
      (r) =>
        r.url().includes("/api/process-batch") &&
        r.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Process batch", exact: true })
      .click();
    const response = await pending;
    expect(response.status()).toBe(200);
    return response.json();
  }
  async function download(button: string, name: string) {
    const pending = page.waitForEvent("download");
    await page.getByRole("button", { name: button, exact: true }).click();
    await (await pending).saveAs(path.join(folder, name));
  }
  const before = await process("5.0");
  expect(before.rows.map((r: { route: string }) => r.route)).toEqual([
    "CONTRACT_PO",
    "CONTRACT_PO",
    "SPOT_PO",
  ]);
  await download("Export exact CSV", "run1.csv");
  await go("Policy Reactor");
  await page.getByRole("button", { name: /5\.0.*active/ }).click();
  const version = "AUDIT-BROWSER-6";
  const source =
    "Set grouping window to twelve calendar days.\nSet quality ranking weight to 22.\nAt plant Alpha plant, require RFQ for Bearings purchases above INR 500 except emergency.\nFor Hydraulics requests at P-A with value between INR 700 and INR 900 inclusive, require RFP.";
  await page.getByLabel("New policy version").fill(version);
  await page.getByLabel("Policy effective date").fill("2026-11-01");
  const upload = page.waitForResponse((r) =>
    r.url().endsWith("/api/policies/upload-amendment"),
  );
  await page
    .getByLabel("Upload amendment", { exact: true })
    .setInputFiles({
      name: "unfamiliar-amendment.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(source),
    });
  const uploaded = await upload;
  expect(uploaded.status()).toBe(200);
  const draft = await uploaded.json();
  expect(draft.interpretation.source_clauses).toHaveLength(4);
  expect(draft.interpretation.unresolved_clauses).toHaveLength(1);
  await expect(
    page.getByText("Unresolved source clauses", { exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Governance reason")
    .fill(
      "Reconciled exact plant, category and inclusive interval with the source",
    );
  const manual = page.getByLabel(
    "I manually reconciled all unresolved clauses into the structured rules.",
  );
  await manual.check();
  await expect(
    page.getByRole("button", { name: "Review policy", exact: true }),
  ).toBeDisabled();
  const policy = {
    version: draft.version,
    effective_date: draft.effective_date,
    parameters: draft.parameters,
    rules: [
      ...draft.rules,
      {
        id: "reviewed-hydraulics-interval",
        priority: 2,
        route: "RFP",
        reason: "Reviewed Hydraulics inclusive interval at P-A",
        when: {
          all: [
            { fact: "requirement.plant", op: "eq", value: "P-A" },
            { fact: "item.category", op: "eq", value: "Hydraulics" },
            { fact: "requirement.group_value_inr", op: "gte", value: "700" },
            { fact: "requirement.group_value_inr", op: "lte", value: "900" },
          ],
        },
      },
    ],
  };
  await page
    .getByLabel("Policy DSL JSON")
    .fill(JSON.stringify(policy, null, 2));
  await clickResponse(page, "Preview validation and diff", "/preview");
  await clickResponse(
    page,
    "Save draft changes",
    "/api/policies/" + version,
    "PUT",
  );
  await page
    .getByLabel("Processing run", { exact: true })
    .selectOption(before.id);
  await clickResponse(page, "Simulate selected policy", "/simulate");
  await manual.check();
  await page
    .getByLabel("Clause 1 meaning")
    .fill("Implement the inclusive Hydraulics value interval using RFP");
  await page.getByLabel("Clause 1 scope").fill("Hydraulics requests at P-A");
  await page
    .getByLabel("Clause 1 paths")
    .fill("rules[reviewed-hydraulics-interval]");
  await page.getByLabel("Clause 1 priority").fill("2");
  await page
    .getByLabel("Clause 1 evidence")
    .fill(
      "Verified both inclusive boundaries and the exact plant and category predicates",
    );
  await page
    .getByLabel("I verified this clause against the saved executable change.")
    .check();
  await page.getByLabel("Acknowledge rule precedence").check();
  for (const action of ["Review", "Approve", "Activate"])
    await clickResponse(page, action + " policy", "/" + action.toLowerCase());
  const after = await process(version);
  expect(after.input_hash).toBe(before.input_hash);
  expect(after.rows.map((r: { route: string }) => r.route)).toEqual([
    "RFQ",
    "CONTRACT_PO",
    "RFP",
  ]);
  expect(after.rows).toHaveLength(3);
  await download("Export exact CSV", "run2.csv");
  await page.getByLabel("Compare with run ID").fill(before.id);
  await page.getByRole("button", { name: "Compare runs", exact: true }).click();
  await expect(
    page.getByText("affected lines ·", { exact: false }),
  ).toBeVisible();
  for (const id of [before.id, after.id]) {
    await page.getByLabel("Processing run", { exact: true }).selectOption(id);
    const replay = await clickResponse(page, "Replay snapshot", "/replay");
    expect(replay.run_id).toBe(id);
    await expect(
      page.getByText("Replay matches original output", { exact: false }),
    ).toBeVisible();
  }
  await go("Supplier Constellation");
  await page
    .getByLabel("Supplier as-of date", { exact: true })
    .fill("2026-11-19");
  await page
    .getByLabel("Supplier ranking policy", { exact: true })
    .selectOption(version);
  const supplierExport = page.waitForResponse((r) =>
    r.url().includes("/api/preferred-suppliers/export.csv"),
  );
  await download("Export preferred CSV", "preferred.csv");
  const exported = await supplierExport;
  expect(new URL(exported.url()).searchParams.get("policy_version")).toBe(
    version,
  );
  expect(new URL(exported.url()).searchParams.get("as_of")).toBe("2026-11-19");
  expect(
    (await fs.readFile(path.join(folder, "preferred.csv"), "utf8")).split(
      /\r?\n/,
    )[0],
  ).toBe("item_code,rank,supplier_id,reference_price");
  expect(purchasingActions).toBe(0);
  expect(errors).toEqual([]);
  await fs.writeFile(
    path.join(folder, "report.json"),
    JSON.stringify(
      {
        version,
        rows: 3,
        run1: before.id,
        run2: after.id,
        input_hash: before.input_hash,
        same_input: true,
        source_clauses: 4,
        manually_reconciled: 1,
        expected_routes: ["RFQ", "CONTRACT_PO", "RFP"],
        purchasing_actions: purchasingActions,
        both_replays: true,
        browser_errors: errors,
      },
      null,
      2,
    ),
  );
  // Leave the shared isolated browser server on its original active policy.
  await go("Policy Reactor");
  await page
    .getByRole("button", { name: new RegExp(version + ".*active") })
    .click();
  await expect(page.getByLabel("Policy DSL JSON")).toHaveValue(
    new RegExp('"version":\\s*"' + version + '"'),
  );
  await page
    .getByLabel("Governance reason")
    .fill("Completed isolated rehearsal; restore original policy calendar");
  const withdrawn = await clickResponse(
    page,
    "Deactivate policy",
    "/deactivate",
  );
  expect(withdrawn.id).toBe(version);
  expect(withdrawn.status).toBe("superseded");
});

async function clickResponse(
  page: Page,
  button: string,
  suffix: string,
  method = "POST",
) {
  const pending = page.waitForResponse(
    (r) => r.url().endsWith(suffix) && r.request().method() === method,
  );
  await page.getByRole("button", { name: button, exact: true }).click();
  const response = await pending;
  expect(response.status()).toBe(200);
  return response.json();
}
