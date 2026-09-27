import { mkdtempSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

const root = mkdtempSync(path.join(os.tmpdir(), "edqa-final-product-"));
const python = process.env.HARNESS_PYTHON ?? "python";
const servers = ([ ["public", 8777], ["local", 8778] ] as const).map(([mode, port]) => ({
  command: `"${python}" tests/integration/final_product_server.py`,
  url: `http://127.0.0.1:${port}/health/live`, cwd: "..",
  reuseExistingServer: false, timeout: 60_000,
  env: { TEST004_WORKSPACE_MODE: mode, TEST004_API_PORT: String(port), TEST004_RUNTIME_DIR: path.join(root, mode) },
}));

export default defineConfig({
  testDir: "./e2e", testMatch: /test-004-product\.spec\.ts/,
  fullyParallel: false, workers: 1, retries: 0,
  timeout: 60_000, expect: { timeout: 10_000 }, reporter: "list",
  outputDir: "./test-results/product",
  use: { baseURL: "http://localhost:4177", trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [
    { name: "product-chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "product-firefox", use: { ...devices["Desktop Firefox"] } },
  ],
  webServer: [...servers, {
    command: "bun run build --outDir dist-product && bunx vite preview --outDir dist-product --port 4177 --strictPort",
    url: "http://localhost:4177", reuseExistingServer: false, timeout: 60_000,
    env: { VITE_API_BASE_URL: "http://127.0.0.1:8778" },
  }],
});
