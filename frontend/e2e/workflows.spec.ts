import { test, expect, type Page } from "@playwright/test";
import path from "node:path";
const headers =
  "pr_no,pr_line,created_at,requester,department,plant,item_code,description,quantity,uom,estimated_unit_price,need_by_date,urgency";
test("startup survives blocked storage and fonts", async ({ page }) => {
  await page.addInitScript(() =>
    Object.defineProperty(window, "localStorage", {
      get() {
        throw new DOMException("Storage denied", "SecurityError");
      },
    }),
  );
  await page.route("https://fonts.googleapis.com/**", (r) => r.abort());
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeVisible();
});
test("blocked entry script shows reload recovery instead of a blank page", async ({
  page,
}) => {
  await page.route("**/src/main.tsx", (r) => r.abort());
  await page.goto("/");
  await expect(
    page.getByRole("link", { name: "Reload workspace", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Let’s reload your workspace.", { exact: true }),
  ).toBeVisible();
});
const csv =
  headers +
  "\nPR-E2E-A,1,2026-11-01 10:00,Synthetic user,Testing,P-A,ITM-9001,Ball bearing 6205-2RS,10,NOS,,2026-11-20,Normal\nPR-E2E-B,1,2026-11-02 10:00,Synthetic user,Testing,P-A,ITM-9001,Ball bearing 6205-2RS,10,NOS,,2026-11-20,Normal\nPR-E2E-C,1,2026-11-03 10:00,Synthetic user,Testing,P-A,ITM-9002,Hydraulic hose 1/2 inch 2 wire,3,MTR,,2026-11-20,Normal\nPR-E2E-BAD,1,2026-11-04 10:00,Synthetic user,Testing,P-A,ITM-9001,Ball bearing,abc,NOS,,2026-11-20,Normal\n";
test("privileged credentials are never autofilled and the core leaves its background visible", async ({
  page,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem("corvo.intro.seen.v1", "1"),
  );
  await page.goto("/");
  for (const role of ["buyer", "admin"]) {
    await page.getByLabel("Role", { exact: true }).selectOption(role);
    await expect(page.getByLabel("Password", { exact: true })).toHaveValue("");
    await expect(page.getByLabel("Password", { exact: true })).toHaveAttribute(
      "type",
      "password",
    );
  }
  await page.getByLabel("Password", { exact: true }).fill("corvo-demo");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { level: 1, name: /PROCUREMENT/ }),
  ).toBeVisible();
  await page.waitForTimeout(3000);
  const bounds = await page.evaluate(() => {
    const a = document
      .querySelector(".hero-machine-view")!
      .getBoundingClientRect();
    const b = document
      .querySelector(".hero-stage-note")!
      .getBoundingClientRect();
    return { sceneBottom: a.bottom, noteTop: b.top };
  });
  expect(bounds.sceneBottom).toBeLessThanOrEqual(bounds.noteTop + 1);
  await page.screenshot({ path: "../.private/hero-refined-desktop.png" });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: "../.private/hero-refined-mobile.png" });
});
test("individual creates a real requester account and can sign in again", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(() =>
    localStorage.setItem("corvo.intro.seen.v1", "1"),
  );
  await page.goto("/");
  await page.getByLabel("Account type").selectOption("individual");
  await page.getByRole("button", { name: "New here? Create account" }).click();
  await page.getByLabel("Username", { exact: true }).fill("browser-new-user");
  await page.getByLabel("Full name", { exact: true }).fill("Browser New User");
  await page
    .getByLabel("Password", { exact: true })
    .fill("Synthetic-new-password-123");
  await page.screenshot({ path: "../.private/signup-mobile.png" });
  const registration = page.waitForResponse((r) =>
    r.url().endsWith("/api/auth/register"),
  );
  await page.getByRole("button", { name: "Create account & sign in" }).click();
  const r = await registration;
  expect(r.status()).toBe(201);
  expect((await r.json()).role).toBe("requester");
  await expect(
    page.getByRole("heading", { level: 1, name: /PROCUREMENT/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Policy Reactor", exact: true }),
  ).toHaveCount(0);
  await page.reload();
  await page.getByLabel("Account type").selectOption("individual");
  await page.getByLabel("Username", { exact: true }).fill("browser-new-user");
  await page
    .getByLabel("Password", { exact: true })
    .fill("Synthetic-new-password-123");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { level: 1, name: /PROCUREMENT/ }),
  ).toBeVisible();
});
async function login(page: Page, role = "admin") {
  await page.addInitScript(() =>
    localStorage.setItem("corvo.intro.seen.v1", "1"),
  );
  await page.goto("/");
  await page.getByLabel("Role", { exact: true }).selectOption(role);
  await page.getByLabel("Password", { exact: true }).fill("corvo-demo");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("navigation", { name: "Primary" })).toBeVisible();
}
async function go(page: Page, label: string) {
  if (
    await page
      .getByRole("button", { name: "Open navigation", exact: true })
      .isVisible()
  )
    await page
      .getByRole("button", { name: "Open navigation", exact: true })
      .click();
  await page.getByRole("link", { name: label, exact: true }).click();
  const titles: Record<string, string> = {
    Overview: "PROCUREMENT",
    "Request Studio": "Start with what you need.",
    "Buyer Inbox": "Decide, then move on.",
    "Decision X-Ray": "Inspect the machine.",
    "Batch Lab": "Raw lines. Controlled outcomes.",
    "Policy Reactor": "Change the rules. Keep the proof.",
    "Supplier Constellation": "Who can deliver, and how well.",
    "Contract Vault": "Every agreement, under inspection.",
    "Purchase Orders": "Approved, recorded, traceable.",
    Sourcing: "Competition starts with evidence.",
    "Audit Trail": "Every action leaves a record.",
  };
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: label === "Overview" ? /PROCUREMENT/ : titles[label],
      exact: label !== "Overview",
    }),
  ).toBeVisible();
  await page.waitForLoadState("networkidle");
  await page.waitForFunction(() =>
    Array.from(document.querySelectorAll("#main h1 [style]")).every((el) => {
      const transform = getComputedStyle(el).transform;
      return (
        transform === "none" || Math.abs(new DOMMatrix(transform).m42) < 0.2
      );
    }),
  );
}
async function noErrors(page: Page) {
  await expect(
    page.getByText("API contract mismatch:", { exact: false }),
  ).toHaveCount(0);
}

test("isolated synthetic demo calculates, changes with CSV input and leaves live runs unchanged", async ({
  page,
}) => {
  const me = page.waitForRequest((r) => r.url().endsWith("/api/auth/me"));
  await login(page);
  const authorization = (await (await me).headerValue("authorization"))!;
  const before = await (
    await page.request.get("/api/overview", {
      headers: { Authorization: authorization },
    })
  ).json();
  await go(page, "Batch Lab");
  const sandbox = page.getByTestId("demo-sandbox");
  await sandbox.locator("summary").first().click();
  const calculated = page.waitForResponse((r) =>
    r.url().endsWith("/api/demo/preview"),
  );
  await sandbox
    .getByRole("button", { name: "Calculate demo", exact: true })
    .click();
  const initial = await (await calculated).json();
  expect(initial.persistent).toBe(false);
  expect(initial.result.rows).toHaveLength(9);
  await expect(
    sandbox.getByText("SYNTHETIC PREVIEW · NOT SAVED · POLICY 5.0", {
      exact: false,
    }),
  ).toBeVisible();
  const download = page.waitForEvent("download");
  await sandbox.getByRole("button", { name: "Export demo decisions" }).click();
  expect((await download).suggestedFilename()).toBe(
    "synthetic-demo-decisions.csv",
  );
  const input = await (
    await page.request.get("/api/demo/input.csv", {
      headers: { Authorization: authorization },
    })
  ).text();
  const lines = input.trim().split(/\r?\n/);
  const row = lines.find((line) => line.startsWith("DEMO-PR-03,"))!.split(",");
  row[8] = "50000";
  await sandbox
    .getByLabel("Demo CSV file (optional)", { exact: true })
    .setInputFiles({
      name: "changed-demo.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(lines[0] + "\n" + row.join(",") + "\n"),
    });
  const changed = page.waitForResponse((r) =>
    r.url().endsWith("/api/demo/preview"),
  );
  await sandbox
    .getByRole("button", { name: "Calculate demo", exact: true })
    .click();
  const result = await (await changed).json();
  expect(result.result.rows).toHaveLength(1);
  expect(result.result.rows[0].route).toBe("RFP");
  await expect(
    sandbox.getByRole("cell", { name: "RFP", exact: true }),
  ).toBeVisible();
  const after = await (
    await page.request.get("/api/overview", {
      headers: { Authorization: authorization },
    })
  ).json();
  expect(after).toEqual(before);
  await page.setViewportSize({ width: 390, height: 844 });
  await sandbox.scrollIntoViewIfNeeded();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "../.private/isolated-demo-mobile.png" });
});

test("real CSV, consolidated approval, policy amendment lifecycle, replay and authenticated export", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await login(page);
  await go(page, "Batch Lab");
  await page.getByLabel("PR CSV file", { exact: true }).setInputFiles({
    name: "synthetic.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(csv),
  });
  const processed = page.waitForResponse(
    (r) =>
      r.url().includes("/api/process-batch") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Process batch", exact: true })
    .click();
  const response = await processed;
  expect(response.status()).toBe(200);
  const run = await response.json();
  expect(run.rows).toHaveLength(4);
  expect(run.issues).toHaveLength(1);
  await expect(
    page.getByText("4 output lines", { exact: false }),
  ).toBeVisible();
  await noErrors(page);
  const downloadEvent = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export exact CSV" }).click();
  const download = await downloadEvent;
  const stream = await download.createReadStream();
  const chunks = [];
  for await (const c of stream!) chunks.push(c);
  const exported = Buffer.concat(chunks).toString();
  expect(exported.split(/\r?\n/)[0]).toBe(
    "pr_no,pr_line,resolved_item_code,group_id,po_id,decision,route,supplier_id,unit_price,group_value_inr,suggested_supplier_ids,policy_version,reason",
  );
  await page.getByRole("button", { name: "Replay snapshot" }).click();
  await expect(
    page.getByText("Replay matches original output", { exact: false }),
  ).toBeVisible();
  await go(page, "Buyer Inbox");
  await page.getByLabel("Processing run", { exact: true }).selectOption(run.id);
  await page
    .getByLabel("Buyer reason", { exact: true })
    .fill("Reviewed synthetic consolidated order evidence");
  await page.getByLabel("I reviewed the evidence and approval scope.").check();
  const approval = page.waitForResponse(
    (r) =>
      r.url().includes("/approve?run_id=") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Approve recommendation", exact: true })
    .click();
  const approvalResponse = await approval;
  expect(approvalResponse.status()).toBe(200);
  const approvedAction = await approvalResponse.json();
  await go(page, "Purchase Orders");
  await expect(page.getByText("No approved records yet.")).toHaveCount(0);
  await noErrors(page);
  await go(page, "Policy Reactor");
  await expect(page.getByLabel("Policy DSL JSON")).toBeVisible();
  const version = "6.0-browser";
  await page.getByLabel("New policy version").fill(version);
  await page.getByLabel("Policy effective date").fill("2026-04-02");
  await page
    .getByLabel("Amendment text")
    .fill(
      "If plant is P-A and category is Bearings and value exceeds INR 500 require RFQ",
    );
  const proposed = page.waitForResponse((r) =>
    r.url().includes("/propose-amendment"),
  );
  await page.getByRole("button", { name: "Propose text amendment" }).click();
  expect((await proposed).status()).toBe(200);
  await expect(page.getByLabel("Policy DSL JSON")).toContainText(version);
  await page.getByLabel("Processing run", { exact: true }).selectOption(run.id);
  const simulation = page.waitForResponse((r) => r.url().endsWith("/simulate"));
  await page.getByRole("button", { name: "Simulate selected policy" }).click();
  const sim = await (await simulation).json();
  expect(sim.policy_id).toBe(version);
  expect(sim.comparison.affected_lines).toBeGreaterThan(0);
  await page
    .getByLabel("Governance reason")
    .fill("Reviewed source scope, comparison and priority");
  for (const action of ["Review", "Approve", "Activate"]) {
    const response = page.waitForResponse(
      (r) =>
        r.url().endsWith("/" + action.toLowerCase()) &&
        r.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: action + " policy", exact: true })
      .click();
    expect((await response).status()).toBe(200);
  }
  await go(page, "Batch Lab");
  await page.getByLabel("PR CSV file", { exact: true }).setInputFiles({
    name: "synthetic.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(csv),
  });
  await page.getByLabel("Batch policy version").selectOption(version);
  const amended = page.waitForResponse(
    (r) =>
      r.url().includes("/api/process-batch") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Process batch", exact: true })
    .click();
  const after = await (await amended).json();
  expect(after.rows[0].route).toBe("RFQ");
  await page.getByLabel("Compare with run ID").fill(run.id);
  await page.getByRole("button", { name: "Compare runs", exact: true }).click();
  await expect(
    page.getByText("affected lines ·", { exact: false }),
  ).toBeVisible();
  await go(page, "Buyer Inbox");
  await page
    .getByLabel("Processing run", { exact: true })
    .selectOption(after.id);
  await page
    .getByLabel("Buyer reason", { exact: true })
    .fill("Competitive sourcing override for synthetic test");
  await page.getByLabel("I reviewed the evidence and approval scope.").check();
  await page
    .getByLabel("Override to sourcing", { exact: true })
    .selectOption("RFP");
  const override = page.waitForResponse((r) =>
    r.url().includes("/override?run_id="),
  );
  await page
    .getByRole("button", { name: "Override to sourcing", exact: true })
    .click();
  expect((await override).status()).toBe(409);
  await expect(
    page.getByText("PR line already approved", { exact: true }),
  ).toBeVisible();
  const committed = new Set(
    approvedAction.recommendations.flatMap(
      (r: { lines: { pr_no: string; pr_line: string }[] }) =>
        r.lines.map((l) => l.pr_no + ":" + l.pr_line),
    ),
  );
  const uncommitted = after.requirements.find(
    (r: { lines: { pr_no: string; pr_line: string }[] }) =>
      r.lines.every((l) => !committed.has(l.pr_no + ":" + l.pr_line)),
  );
  expect(uncommitted).toBeTruthy();
  await page
    .getByLabel("Inspect requirement", { exact: true })
    .selectOption(uncommitted.id);
  await page
    .getByLabel("Buyer reason", { exact: true })
    .fill("Reviewed uncommitted synthetic sourcing line");
  await page.getByLabel("I reviewed the evidence and approval scope.").check();
  const sourcing = page.waitForResponse((r) =>
    r.url().includes("/override?run_id="),
  );
  await page
    .getByRole("button", { name: "Override to sourcing", exact: true })
    .click();
  expect((await sourcing).status()).toBe(200);
  await go(page, "Sourcing");
  await expect(page.getByText("No approved records yet.")).toHaveCount(0);
  await go(page, "Decision X-Ray");
  await noErrors(page);
  await page.getByRole("button", { name: "2D evidence" }).click();
  await expect(
    page.getByText("Contract evaluation", { exact: true }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("chat maintains server session and requires explicit confirmation", async ({
  page,
}) => {
  await login(page, "requester");
  await go(page, "Request Studio");
  await page
    .getByLabel("Describe the request", { exact: true })
    .fill("Need 2 ITM-9002 at P-A by 2026-12-01 normal");
  const response = page.waitForResponse((r) =>
    r.url().endsWith("/api/chat/messages"),
  );
  await page.getByRole("button", { name: "Send", exact: true }).click();
  const draft = await (await response).json();
  expect(draft.run).toBeNull();
  expect(draft.state.ready).toBe(true);
  await go(page, "Overview");
  await go(page, "Request Studio");
  await expect(
    page.getByRole("button", { name: "Confirm and create PR" }),
  ).toBeEnabled();
  const created = page.waitForResponse((r) =>
    r.url().endsWith("/api/chat/messages"),
  );
  await page.getByRole("button", { name: "Confirm and create PR" }).click();
  const confirmed = await (await created).json();
  expect(confirmed.session_id).toBe(draft.session_id);
  expect(confirmed.run.requirements).toHaveLength(1);
  await page
    .getByLabel("Describe the request", { exact: true })
    .fill("Need 3 ITM-9002 at P-A by 2026-12-02 normal");
  const secondDraft = page.waitForResponse((r) =>
    r.url().endsWith("/api/chat/messages"),
  );
  await page.getByRole("button", { name: "Send", exact: true }).click();
  expect((await (await secondDraft).json()).run).toBeNull();
  const secondConfirmation = page.waitForResponse((r) =>
    r.url().endsWith("/api/chat/messages"),
  );
  await page.getByRole("button", { name: "Confirm and create PR" }).click();
  const second = await (await secondConfirmation).json();
  expect(second.session_id).toBe(draft.session_id);
  expect(second.run.input[0].pr_no).not.toBe(confirmed.run.input[0].pr_no);
  await expect(
    page.getByRole("heading", { name: "PR created", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Buyer Inbox", exact: true }),
  ).toHaveCount(0);
  await noErrors(page);
  await page.getByRole("button", { name: "Profile", exact: true }).click();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeVisible();
});

test("manual scanned contract proposal is verified and persisted", async ({
  page,
}) => {
  await login(page);
  await go(page, "Contract Vault");
  const uploaded = page.waitForResponse((r) =>
    r.url().endsWith("/api/contracts/upload"),
  );
  await page
    .getByLabel("Upload contract PDF", { exact: true })
    .setInputFiles(path.resolve("../.private/e2e-manual-contract.pdf"));
  const p = await (await uploaded).json();
  expect(p.manual_entry_required).toBe(true);
  await page
    .getByLabel("Contract proposal", { exact: true })
    .selectOption(p.id);
  await page.getByLabel("Verified contract JSON").fill(
    JSON.stringify(
      {
        contract_id: "C-BROWSER-VERIFIED",
        supplier_id: "S-TEST-B",
        start_date: "2026-01-01",
        end_date: "2028-12-31",
        value_cap: "5000",
        consumed_value: "0",
        lines: [{ item_code: "ITM-9002", uom: "MTR", rate: "190" }],
      },
      null,
      2,
    ),
  );
  await page
    .getByLabel("Contract verification reason")
    .fill("Verified synthetic scanned agreement manually");
  await page
    .getByLabel(
      "I checked supplier, items, units, rates, dates and ceiling against the original agreement.",
    )
    .check();
  const approved = page.waitForResponse(
    (r) =>
      r.url().includes("/api/contracts/proposals/") &&
      r.url().endsWith("/approve"),
  );
  await page.getByRole("button", { name: "Approve verified contract" }).click();
  expect((await approved).status()).toBe(200);
  await expect(
    page.getByRole("link", { name: "C-BROWSER-VERIFIED", exact: true }),
  ).toBeVisible();
  await noErrors(page);
});

test("all major screens render real data at desktop and mobile widths without page overflow", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await login(page);
  const screens = [
    "Overview",
    "Request Studio",
    "Buyer Inbox",
    "Decision X-Ray",
    "Batch Lab",
    "Policy Reactor",
    "Supplier Constellation",
    "Contract Vault",
    "Purchase Orders",
    "Sourcing",
    "Audit Trail",
  ];
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const label of screens) {
      await go(page, label);
      await noErrors(page);
      await expect(
        page.getByText("Request failed", { exact: true }),
      ).toHaveCount(0);
      const main = page.locator("#main");
      await expect
        .poll(() => main.evaluate((e) => e.scrollWidth - e.clientWidth))
        .toBeLessThanOrEqual(2);
      const bands = await page
        .locator(".material-band")
        .evaluateAll((elements) =>
          elements.map((element) => {
            const copy = element.querySelector(".material-copy")!;
            const box = element.getBoundingClientRect();
            const text = copy.getBoundingClientRect();
            return {
              top: text.top - box.top,
              bottom: box.bottom - text.bottom,
              left: text.left - box.left,
              right: box.right - text.right,
              overflow: copy.scrollHeight - copy.clientHeight,
            };
          }),
        );
      for (const band of bands) {
        expect(band.top).toBeGreaterThanOrEqual(0);
        expect(band.bottom).toBeGreaterThanOrEqual(0);
        expect(band.left).toBeGreaterThanOrEqual(-1);
        expect(band.right).toBeGreaterThanOrEqual(-1);
        expect(band.overflow).toBeLessThanOrEqual(2);
      }
      await page.screenshot({
        path: path.resolve(
          `../.private/screens/${width}-${label.replaceAll(" ", "-")}.png`,
        ),
        animations: "disabled",
      });
    }
  }
  expect(errors).toEqual([]);
});

test("real authorization errors, invalid CSV and API outage never produce synthetic success", async ({
  page,
}) => {
  await login(page);
  await go(page, "Batch Lab");
  await page.getByLabel("PR CSV file", { exact: true }).setInputFiles({
    name: "bad.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("description,quantity,plant\nwrong,2,P-A"),
  });
  await expect(
    page.getByText("Missing CSV headers:", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Process batch", exact: true }),
  ).toBeDisabled();
  await page.route("**/api/overview", (route) => route.abort());
  await login(page);
  await expect(
    page.getByText("Unable to reach the API.", { exact: false }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeVisible();
});

test("amendment uploads preserve unresolved warnings and require manual reconciliation", async ({
  page,
}) => {
  await login(page);
  await go(page, "Policy Reactor");
  await page.getByLabel("New policy version").fill("6.1-unresolved-browser");
  await page.getByLabel("Policy effective date").fill("2026-04-02");
  const response = page.waitForResponse((r) =>
    r.url().endsWith("/api/policies/upload-amendment"),
  );
  await page.getByLabel("Upload amendment", { exact: true }).setInputFiles({
    name: "amendment.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(
      "Unless commercial exceptions apply, use the alternate process",
    ),
  });
  expect((await response).status()).toBe(200);
  await expect(
    page.getByText("Unresolved source clauses", { exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Governance reason")
    .fill("Incomplete source must not be silently accepted");
  await expect(
    page.getByRole("button", { name: "Review policy", exact: true }),
  ).toBeDisabled();
  await noErrors(page);
});

test("actual server session revocation sends the frontend back to sign-in", async ({
  page,
}) => {
  const meRequest = page.waitForRequest((r) =>
    r.url().endsWith("/api/auth/me"),
  );
  await login(page);
  const request = await meRequest;
  const bearer = await request.headerValue("authorization");
  expect(bearer).toBeTruthy();
  const response = await page.request.post("/api/auth/logout", {
    headers: { Authorization: bearer! },
  });
  expect(response.status()).toBe(200);
  await go(page, "Batch Lab").catch(() => {});
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeVisible();
});

test("actual login throttling displays retry delay and disables resubmission", async ({
  page,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem("corvo.intro.seen.v1", "1"),
  );
  await page.goto("/");
  await page
    .getByLabel("Account type", { exact: true })
    .selectOption("individual");
  await page
    .getByLabel("Username", { exact: true })
    .fill("unknown-browser-account");
  await page
    .getByLabel("Password", { exact: true })
    .fill("invalid-synthetic-password");
  for (let i = 0; i < 6; i++) {
    const response = page.waitForResponse((r) =>
      r.url().endsWith("/api/auth/login"),
    );
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    expect((await response).status()).toBe(i < 5 ? 401 : 429);
  }
  await expect(
    page.getByRole("button", { name: /Try again in/ }),
  ).toBeDisabled();
  await expect(
    page.getByText("Retry after", { exact: false }).last(),
  ).toBeVisible();
});

test("real run and requirement pagination use backend offsets and totals", async ({
  page,
}) => {
  const me = page.waitForRequest((r) => r.url().endsWith("/api/auth/me"));
  await login(page);
  const bearer = await (await me).headerValue("authorization");
  for (let i = 0; i < 26; i++) {
    const row = `PR-PAGE-${i},1,2026-11-01 10:00,Synthetic user,Testing,P-A,ITM-9002,Hydraulic hose,1,MTR,,2026-11-20,Normal`;
    const r = await page.request.post("/api/process-batch", {
      headers: { Authorization: bearer! },
      multipart: {
        file: {
          name: "page.csv",
          mimeType: "text/csv",
          buffer: Buffer.from(headers + "\n" + row + "\n"),
        },
        policy_version: "5.0",
      },
    });
    expect(r.status()).toBe(200);
  }
  await go(page, "Batch Lab");
  const next = page.waitForResponse((r) =>
    r.url().includes("/api/runs?offset=25"),
  );
  await page.getByRole("button", { name: "Next", exact: true }).click();
  const pageData = await (await next).json();
  expect(pageData.offset).toBe(25);
  expect(pageData.total).toBeGreaterThanOrEqual(26);
  const rows = Array.from(
    { length: 30 },
    (_, i) =>
      `PR-MANY-${i},1,2026-11-01 10:00,Synthetic user,Testing,P-A,,Unique synthetic material ${i},1,NOS,100,2026-12-01,Normal`,
  ).join("\n");
  const r = await page.request.post("/api/process-batch", {
    headers: { Authorization: bearer! },
    multipart: {
      file: {
        name: "requirements.csv",
        mimeType: "text/csv",
        buffer: Buffer.from(headers + "\n" + rows + "\n"),
      },
      policy_version: "5.0",
    },
  });
  expect(r.status()).toBe(200);
  const run = await r.json();
  expect(run.requirements).toHaveLength(30);
  await go(page, "Buyer Inbox");
  await page.getByRole("button", { name: "Refresh runs", exact: true }).click();
  await page.getByLabel("Processing run", { exact: true }).selectOption(run.id);
  const nextRequirements = page.waitForResponse(
    (r) =>
      r.url().includes("/api/requirements?") &&
      new URL(r.url()).searchParams.get("offset") === "25",
  );
  await page
    .locator(".inbox-layout")
    .getByRole("button", { name: "Next", exact: true })
    .click();
  const second = await (await nextRequirements).json();
  expect(second.offset).toBe(25);
  expect(second.total).toBe(30);
  expect(second.items).toHaveLength(5);
  await go(page, "Decision X-Ray");
  await page.getByLabel("Processing run", { exact: true }).selectOption(run.id);
  const tracePage = page.waitForResponse(
    (response) =>
      response.url().includes("/api/requirements?") &&
      new URL(response.url()).searchParams.get("offset") === "25",
  );
  await page
    .locator(".trace-chooser")
    .getByRole("button", { name: "Next", exact: true })
    .click();
  const traceItems = await (await tracePage).json();
  expect(traceItems.total).toBe(30);
  await page
    .getByLabel("Trace requirement", { exact: true })
    .selectOption(traceItems.items[0].id);
  await expect(page.locator(".trace-chooser")).toContainText("of 30");
  const otherRunId = await page
    .getByLabel("Processing run", { exact: true })
    .locator("option")
    .nth(1)
    .getAttribute("value");
  const changedRun = page.waitForResponse(
    (response) =>
      response.url().includes("/api/requirements?") &&
      new URL(response.url()).searchParams.get("run_id") === otherRunId &&
      new URL(response.url()).searchParams.get("offset") === "0",
  );
  await page
    .getByLabel("Processing run", { exact: true })
    .selectOption(otherRunId!);
  expect((await (await changedRun).json()).total).toBe(1);
  await expect(
    page.getByLabel("Trace requirement", { exact: true }).locator("option"),
  ).toHaveCount(1);
  await noErrors(page);
});
