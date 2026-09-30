import { mkdtempSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

const python = process.env.HARNESS_PYTHON ?? "python";
export default defineConfig({
  testDir: "./e2e", testMatch: /provider-001\.spec\.ts/,
  fullyParallel: false, workers: 1, retries: 0, timeout: 60_000,
  expect: { timeout: 10_000 }, reporter: "list", outputDir: "./test-results/provider",
  use: { baseURL: "http://localhost:4189", trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [
    { name: "provider-chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "provider-firefox", use: { ...devices["Desktop Firefox"] } },
  ],
  webServer: [{
    command: `"${python}" tests/integration/provider_product_server.py`,
    url: "http://127.0.0.1:8789/health/live", cwd: "..", reuseExistingServer: false, timeout: 60_000,
    env: { PROVIDER001_RUNTIME_DIR: mkdtempSync(path.join(os.tmpdir(), "edqa-provider001-browser-")) },
  }, {
    command: "bun run build --outDir dist-provider && bunx vite preview --outDir dist-provider --port 4189 --strictPort",
    url: "http://localhost:4189", reuseExistingServer: false, timeout: 60_000,
    env: { VITE_API_BASE_URL: "http://127.0.0.1:8789" },
  }],
});
