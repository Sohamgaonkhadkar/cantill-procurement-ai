import { test, expect } from "@playwright/test";

test("decision evidence presents labeled fields and keeps exact JSON optional", async ({
  page,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem("corvo.intro.seen.v1", "1"),
  );
  await page.goto("/");
  await page.getByLabel("Role", { exact: true }).selectOption("admin");
  await page.getByLabel("Password", { exact: true }).fill("corvo-demo");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("link", { name: "Batch Lab", exact: true }).click();
  const csv =
    "pr_no,pr_line,created_at,requester,department,plant,item_code,description,quantity,uom,estimated_unit_price,need_by_date,urgency\nREADABLE-1,1,2026-11-17 10:00,Fictional user,Testing,P-A,ITM-9001,Bearing,1,NOS,,2026-12-01,Normal\n";
  await page.getByLabel("PR CSV file", { exact: true }).setInputFiles({
    name: "fictional.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(csv),
  });
  await page.getByLabel("Batch policy version").selectOption("5.0");
  const pending = page.waitForResponse((r) =>
    r.url().endsWith("/api/process-batch"),
  );
  await page
    .getByRole("button", { name: "Process batch", exact: true })
    .click();
  expect((await pending).status()).toBe(200);
  await page.getByRole("link", { name: "Decision X-Ray", exact: true }).click();
  await page
    .getByRole("button", { name: "5 · FINAL ROUTE", exact: true })
    .click();
  const details = page.locator("details").filter({
    has: page.locator(":scope > summary", { hasText: /^Stage evidence$/ }),
  });
  await details.locator(":scope > summary").click();
  await expect(details.locator(".evidence-fields").first()).toBeVisible();
  await expect(details.locator("pre")).not.toBeVisible();
  await expect(
    page.getByText("Grouped purchase request lines", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".decision-lines")).toContainText("READABLE-1");
  await details
    .getByText("Technical JSON · exact source data", { exact: true })
    .click();
  await expect(details.locator("pre")).toContainText('"route": "CONTRACT_PO"');
  await details
    .getByText("Technical JSON · exact source data", { exact: true })
    .click();
  await page.getByRole("button", { name: "2D evidence", exact: true }).click();
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(
      await page
        .locator("#main")
        .evaluate((el) => el.scrollWidth <= el.clientWidth + 2),
    ).toBe(true);
    await page.locator(".decision-summary").scrollIntoViewIfNeeded();
    await page.screenshot({
      path: `../.private/evidence-format-${width}.png`,
      fullPage: true,
    });
  }
});
