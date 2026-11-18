import { test, expect, type Page } from "@playwright/test";

async function login(page: Page) {
  await page.addInitScript(() =>
    localStorage.setItem("corvo.intro.seen.v1", "1"),
  );
  await page.goto("/");
  await page.getByLabel("Role", { exact: true }).selectOption("admin");
  await page.getByLabel("Password", { exact: true }).fill("corvo-demo");
  const response = page.waitForResponse((r) =>
    r.url().endsWith("/api/auth/login"),
  );
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  const auth = await (await response).json();
  await expect(page.getByRole("navigation", { name: "Primary" })).toBeVisible();
  return { Authorization: `Bearer ${auth.access_token}` };
}

test("CSV preview preserves quoted fields in a compact accessible table on mobile", async ({
  page,
}) => {
  await login(page);
  await page.setViewportSize({ width: 390, height: 1000 });
  await page
    .getByRole("button", { name: "Open navigation", exact: true })
    .click();
  await page.getByRole("link", { name: "Batch Lab", exact: true }).click();
  const headers =
    "pr_no,pr_line,created_at,requester,department,plant,item_code,description,quantity,uom,estimated_unit_price,need_by_date,urgency";
  await page.getByLabel("PR CSV file", { exact: true }).setInputFiles({
    name: "fictional-preview.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      headers +
        '\nPREVIEW,1,2026-11-01,Example,Maintenance,P-A,ITM-9001,"Bearing, sealed",2,NOS,100.00,2026-11-10,Normal\n',
    ),
  });
  await page
    .getByText("CSV preview (first five data rows)", { exact: true })
    .click();
  const table = page.getByRole("table", { name: "CSV input preview" });
  await expect(table).toBeVisible();
  await expect(table.getByRole("columnheader")).toHaveCount(13);
  await expect(table.getByRole("row")).toHaveCount(2);
  await expect(
    table.getByRole("cell", { name: "Bearing, sealed", exact: true }),
  ).toHaveCount(1);
  const region = page.getByRole("region", { name: "Scrollable CSV preview" });
  await region.focus();
  await page.keyboard.press("End");
  expect(await region.evaluate((el) => el.scrollWidth > el.clientWidth)).toBe(
    true,
  );
  expect(
    await page
      .locator("#main")
      .evaluate((el) => el.scrollWidth <= el.clientWidth + 2),
  ).toBe(true);
  expect((await table.boundingBox())!.height).toBeLessThan(400);
});

test("long real policy register stays bounded and every version remains selectable", async ({
  page,
}) => {
  const authResponse = await page.request.post("/api/auth/login", {
    data: { role: "admin", password: "corvo-demo" },
  });
  expect(authResponse.ok()).toBe(true);
  const headers = {
    Authorization: `Bearer ${(await authResponse.json()).access_token}`,
  };
  const baselineResponse = await page.request.get("/api/policies", { headers });
  expect(baselineResponse.ok()).toBe(true);
  const baseline = (await baselineResponse.json()).items.find(
    (p: { version: string }) => p.version === "5.0",
  );
  const prefix = `polish-${Date.now()}`;
  for (let index = 0; index < 12; index++) {
    const response = await page.request.post("/api/policies", {
      headers,
      data: {
        policy: {
          version: `${prefix}-${index}`,
          effective_date: "2026-11-01",
          parameters: baseline.parameters,
          rules: baseline.rules,
        },
        base_version: "5.0",
        source_text:
          "Fictional unchanged policy for register navigation regression.",
      },
    });
    expect(response.status()).toBe(200);
  }
  expect((await page.request.post("/api/auth/logout", { headers })).ok()).toBe(
    true,
  );
  await login(page);
  await page.getByRole("link", { name: "Policy Reactor", exact: true }).click();
  const register = page.getByRole("region", { name: "Policy versions" });
  await expect(register).toBeVisible();
  await expect(
    register.getByRole("button", { name: new RegExp(`${prefix}-`) }),
  ).toHaveCount(12);
  const geometry = await register.evaluate((el) => ({
    height: el.clientHeight,
    scroll: el.scrollHeight,
  }));
  expect(geometry.height).toBeLessThanOrEqual(680);
  expect(geometry.scroll).toBeGreaterThan(geometry.height);
  for (const index of [0, 11]) {
    await register
      .getByRole("button", { name: new RegExp(`${prefix}-${index}\\s`) })
      .click();
    await expect(page.getByLabel("Policy DSL JSON")).toContainText(
      `${prefix}-${index}`,
    );
  }
  await register.focus();
  await page.keyboard.press("Home");
  await expect(
    page.getByRole("heading", { name: "VERSION REGISTER", exact: true }),
  ).toBeVisible();
});
