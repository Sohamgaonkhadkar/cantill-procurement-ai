import { defineConfig } from "@playwright/test";
import path from "node:path";
const root = path.resolve(process.cwd(), "..");
const python =
  process.env.CORVO_PYTHON ??
  (process.platform === "win32"
    ? path.join(root, ".venv/Scripts/python.exe")
    : "python");
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  timeout: 120000,
  expect: { timeout: 15000 },
  outputDir: "../.private/playwright-results",
  reporter: [
    ["list"],
    ["html", { outputFolder: "../.private/playwright-report", open: "never" }],
  ],
  use: {
    actionTimeout: 15000,
    baseURL: "http://127.0.0.1:5175",
    viewport: { width: 1440, height: 1000 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    launchOptions: { args: ["--enable-unsafe-swiftshader"] },
  },
  webServer: [
    {
      command: `"${python}" -m scripts.run_e2e_backend`,
      cwd: root,
      url: "http://127.0.0.1:8002/health",
      timeout: 60000,
      reuseExistingServer: false,
    },
    {
      command: "npm run dev -- --port 5175 --strictPort",
      url: "http://127.0.0.1:5175",
      timeout: 60000,
      env: { CORVO_DEV_API_PROXY: "http://127.0.0.1:8002" },
      reuseExistingServer: false,
    },
  ],
});
