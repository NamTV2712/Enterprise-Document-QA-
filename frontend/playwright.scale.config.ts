import { mkdtempSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

const python = process.env.HARNESS_PYTHON ?? "python";
export default defineConfig({
  testDir: "./e2e", testMatch: /scale-001\.spec\.ts/,
  fullyParallel: false, workers: 1, retries: 0, timeout: 60_000,
  expect: { timeout: 10_000 }, reporter: "list", outputDir: "./test-results/scale",
  use: { baseURL: "http://localhost:4191", trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [
    { name: "scale-chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "scale-firefox", use: { ...devices["Desktop Firefox"] } },
  ],
  webServer: [{
    command: `"${python}" tests/integration/scale_product_server.py`, cwd: "..",
    url: "http://127.0.0.1:8790/health/live", reuseExistingServer: false, timeout: 60_000,
    env: { SCALE001_RUNTIME_DIR: mkdtempSync(path.join(os.tmpdir(), "edqa-scale001-browser-")) },
  }, {
    command: "bun run build --outDir dist-scale && bunx vite preview --outDir dist-scale --port 4191 --strictPort",
    url: "http://localhost:4191", reuseExistingServer: false, timeout: 60_000,
    env: { VITE_API_BASE_URL: "http://127.0.0.1:8790" },
  }],
});
