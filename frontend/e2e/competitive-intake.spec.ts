import { test, expect } from "@playwright/test";

test("local spoken intake, safe policy handoff and calendar processing work through the browser", async ({
  page,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem("corvo.intro.seen.v1", "1"),
  );
  await page.goto("/");
  await page.getByLabel("Role", { exact: true }).selectOption("admin");
  await page.getByLabel("Password", { exact: true }).fill("corvo-demo");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("navigation", { name: "Primary" })).toBeVisible();
  await page.getByRole("link", { name: "Request Studio", exact: true }).click();
  async function say(message: string) {
    await page
      .getByLabel("Describe the request", { exact: true })
      .fill(message);
    const pending = page.waitForResponse(
      (r) => r.url().endsWith("/api/chat/messages"),
      { timeout: 45000 },
    );
    await page.getByRole("button", { name: "Send", exact: true }).click();
    const response = await pending;
    expect(response.status()).toBe(200);
    return response.json();
  }
  const initial = await say(
    "I need twenty ITM-9001 at P-A by 2026-12-01 normal",
  );
  expect(initial.state.quantity).toBe("20");
  const corrected = await say("Make that thirty-five instead");
  expect(corrected.state.quantity).toBe("35");
  expect(corrected.state.plant).toBe("P-A");
  expect(corrected.run).toBeNull();
  const dated = await say("I need this by next Friday");
  expect(dated.state.need_by_date).toBeUndefined();
  expect(dated.message).toContain("YYYY-MM-DD");
  const source =
    "Change the spot purchasing limit from INR 200000 to INR 175000";
  const proposed = await say(source);
  expect(proposed.state.policy_proposal_text).toBe(source);
  expect(proposed.run).toBeNull();
  await page
    .getByRole("link", { name: "Review policy proposal", exact: true })
    .click();
  await expect(page.getByLabel("Amendment text", { exact: true })).toHaveValue(
    source,
  );
  await page.getByRole("link", { name: "Batch Lab", exact: true }).click();
  await page.getByLabel("Batch processing mode").selectOption("calendar");
  await page.getByLabel("Batch policy version").selectOption("5.0");
  const csv =
    "pr_no,pr_line,created_at,requester,department,plant,item_code,description,quantity,uom,estimated_unit_price,need_by_date,urgency\nCALENDAR-BROWSER,1,2026-11-14 10:00,Fictional,Testing,P-A,ITM-9001,Bearing,1,NOS,,2026-11-20,Normal\n";
  await page.getByLabel("PR CSV file", { exact: true }).setInputFiles({
    name: "calendar.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(csv),
  });
  const pending = page.waitForResponse((r) =>
    r.url().endsWith("/api/process-batch"),
  );
  await page
    .getByRole("button", { name: "Process batch", exact: true })
    .click();
  const response = await pending;
  expect(response.status()).toBe(200);
  expect((await response.json()).policy_mode).toBe("calendar");
  await page.getByLabel("PR CSV file", { exact: true }).setInputFiles({
    name: "oversize.csv",
    mimeType: "text/csv",
    buffer: Buffer.alloc(4_000_001),
  });
  await expect(
    page.getByText("Maximum hosted CSV size", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Process batch", exact: true }),
  ).toBeDisabled();
});
