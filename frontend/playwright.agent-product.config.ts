import { mkdtempSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

const root = mkdtempSync(path.join(os.tmpdir(), "edqa-test005-agent-"));
const python = process.env.HARNESS_PYTHON ?? "python";
const servers = ([ ["public", 8787], ["local", 8788] ] as const).map(([mode, port]) => ({
  command: `"${python}" tests/integration/agent_product_server.py`,
  url: `http://127.0.0.1:${port}/health/live`, cwd: "..",
  reuseExistingServer: false, timeout: 60_000,
  env: { TEST005_WORKSPACE_MODE: mode, TEST005_API_PORT: String(port), TEST005_RUNTIME_DIR: path.join(root, mode) },
}));

export default defineConfig({
  testDir: "./e2e", testMatch: /test-005-agent-product\.spec\.ts/,
  fullyParallel: false, workers: 1, retries: 0,
  timeout: 60_000, expect: { timeout: 10_000 }, reporter: "list",
  outputDir: "./test-results/agent-product",
  use: { baseURL: "http://localhost:4187", trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [
    { name: "agent-product-chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "agent-product-firefox", use: { ...devices["Desktop Firefox"] } },
  ],
  webServer: [...servers, {
    command: "bun run build --outDir dist-agent-product && bunx vite preview --outDir dist-agent-product --port 4187 --strictPort",
    url: "http://localhost:4187", reuseExistingServer: false, timeout: 60_000,
    env: { VITE_API_BASE_URL: "http://127.0.0.1:8788" },
  }],
});
