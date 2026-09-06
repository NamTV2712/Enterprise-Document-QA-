import { defineConfig, devices } from "@playwright/test";

const APP_PORT = 8765;
const PROXY_PORT = 8766;
const PREVIEW_PORT = 4173;
const baseURL = `http://localhost:${PREVIEW_PORT}`;

/**
 * Integration configuration: the production frontend build talks to the
 * REAL FastAPI harness over HTTP/SSE (through the byte-splitting proxy so
 * the frontend parser is exercised against fragmented TCP chunks). Playwright
 * route mocks are NOT installed for app routes in these specs. The harness
 * server (tests/integration/harness_server.py) must be started before this
 * suite; use the `test:e2e-integration` script.
 */
export default defineConfig({
  testDir: "./e2e",
  testMatch: /integration\.spec\.ts/,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  outputDir: "./test-results/integration",
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    { name: "integration-chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "integration-firefox", use: { ...devices["Desktop Firefox"] } },
  ],
  webServer: [
    {
      command: `${process.env.HARNESS_PYTHON ?? "python"} tests/integration/harness_server.py`,
      url: `http://127.0.0.1:${APP_PORT}/health/live`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      cwd: "..",
      env: {
        HARNESS_PORT: String(APP_PORT),
        PROXY_PORT: String(PROXY_PORT),
      },
    },
    {
      command: "bunx vite preview --port 4173 --strictPort",
      url: baseURL,
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
  ],
});
