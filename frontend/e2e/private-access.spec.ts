import { test, expect } from "@playwright/test";

test("public personal signup targets fictional data while assessment login stays private", async ({
  page,
}) => {
  let privateRegistrationRequests = 0;
  let demoRegistrationRequests = 0;
  await page.route("**/api/auth/options", (route) =>
    route.fulfill({
      json: {
        submission_access: false,
        registration_enabled: false,
        roles: [],
        workspace_mode: "live",
        demo_url: "https://corvo-procurement-demo.vercel.app",
      },
    }),
  );
  await page.route("**/demo-api/auth/options", (route) =>
    route.fulfill({
      json: {
        submission_access: true,
        registration_enabled: true,
        workspace_mode: "demo",
        demo_url: null,
        roles: ["requester", "buyer", "admin"].map((role) => ({
          role,
          password: "corvo-demo-" + role,
        })),
      },
    }),
  );
  await page.route("**/api/auth/register", (route) => {
    privateRegistrationRequests++;
    return route.abort();
  });
  await page.route("**/demo-api/auth/register", (route) => {
    demoRegistrationRequests++;
    expect(route.request().postDataJSON().username).toBe(
      "fictional-personal-account",
    );
    return route.fulfill({
      status: 403,
      json: {
        error: {
          code: "HTTP_403",
          message: "Synthetic routing check stops before creating an account",
          details: [],
        },
      },
    });
  });
  await page.goto("/");
  await page
    .getByLabel("Account type", { exact: true })
    .selectOption("individual");
  await expect(page.getByLabel("Individual workspace")).toHaveValue(
    "assessment",
  );
  await expect(page.getByLabel("Password", { exact: true })).toHaveValue("");
  await page
    .getByRole("button", { name: "New here? Create account", exact: true })
    .click();
  await expect(page.getByLabel("Individual workspace")).toHaveValue("demo");
  await page
    .getByLabel("Username", { exact: true })
    .fill("fictional-personal-account");
  await page
    .getByLabel("Full name", { exact: true })
    .fill("Fictional routing test");
  await page
    .getByLabel("Password", { exact: true })
    .fill("Fictional-Password-2026!");
  await expect(page.getByLabel("Password", { exact: true })).toHaveAttribute(
    "type",
    "password",
  );
  await page
    .getByRole("button", { name: "Create account & sign in", exact: true })
    .click();
  await expect(
    page.getByText("Synthetic routing check stops before creating an account", {
      exact: true,
    }),
  ).toBeVisible();
  expect(demoRegistrationRequests).toBe(1);
  expect(privateRegistrationRequests).toBe(0);
});
