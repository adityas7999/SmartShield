import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.pw.js",
  timeout: 60000,
  workers: 1,
  outputDir: "../build/browser-results",
  reporter: [
    ["list"],
    ["json", { outputFile: "../build/browser-results.json" }],
  ],
  use: { baseURL: "http://127.0.0.1:5173", trace: "retain-on-failure", launchOptions: process.env.SMARTSHIELD_BROWSER_CONFIG ? JSON.parse(process.env.SMARTSHIELD_BROWSER_CONFIG) : {} },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    {
      name: "mobile",
      use: { ...devices["iPhone 13"], defaultBrowserType: "chromium" },
    },
  ],
  webServer: [
    {
      command:
        "python3 -m uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: false,
    },
    {
      command:
        "python3 -m uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 8001",
      url: "http://127.0.0.1:8001/api/health",
      env: { SMARTSHIELD_ANALYZER_BIN: "/missing-test-analyzer" },
      reuseExistingServer: false,
    },
    {
      command: "npm run dev -- --port 5173",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: false,
    },
  ],
});
