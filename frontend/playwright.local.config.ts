import { existsSync, mkdtempSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

const APP_PORT = Number(process.env.HARNESS_PORT ?? 8765);
const PROXY_PORT = Number(process.env.PROXY_PORT ?? 8766);
const PREVIEW_PORT = 4175;
const useRealBackend = process.env.PLAYWRIGHT_REAL_BACKEND === "1";
const apiOrigin = useRealBackend ? "http://127.0.0.1:8000" : `http://127.0.0.1:${PROXY_PORT}`;
const baseURL = `http://localhost:${PREVIEW_PORT}`;
const repoRoot = path.resolve(process.cwd(), "..");
const localPython = process.platform === "win32"
  ? path.join(repoRoot, ".venv", "Scripts", "python.exe")
  : path.join(repoRoot, ".venv", "bin", "python");
const harnessPython = process.env.HARNESS_PYTHON ?? (existsSync(localPython) ? localPython : "python");
const harnessTempDir = process.env.HARNESS_TEMP_DIR ?? mkdtempSync(path.join(os.tmpdir(), "edqa-playwright-local-"));

/**
 * Isolated workspace verification. The default mode starts only the
 * provider-free harness and uses the integration API binding. The explicit
 * PLAYWRIGHT_REAL_BACKEND=1 mode starts no backend, targets a separately
 * verified local API on 8000, and is used only for the B02.1 gate.
 */
export default defineConfig({
  testDir: "./e2e",
  testMatch: useRealBackend ? /workspace-performance\.spec\.ts/ : /workspace\.local\.spec\.ts/,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  outputDir: "./test-results/local",
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    { name: "local-chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "local-firefox", use: { ...devices["Desktop Firefox"] } },
  ],
  webServer: [
    ...(useRealBackend ? [] : [{
      command: `${harnessPython} tests/integration/harness_server.py`,
      url: `http://127.0.0.1:${APP_PORT}/health/live`,
      // An occupied port must fail the task rather than silently reusing an
      // unknown backend or fixture binding.
      reuseExistingServer: false,
      timeout: 60_000,
      cwd: "..",
      env: {
        HARNESS_PORT: String(APP_PORT),
        PROXY_PORT: String(PROXY_PORT),
        HARNESS_TEMP_DIR: harnessTempDir,
      },
    }]),
    {
      command: useRealBackend
        ? "bun run build --outDir dist-local && bunx vite preview --outDir dist-local --host localhost --port 4175 --strictPort"
        : "bun run build --mode integration --outDir dist-local && bunx vite preview --outDir dist-local --host localhost --port 4175 --strictPort",
      url: baseURL,
      reuseExistingServer: false,
      timeout: 30_000,
      env: { VITE_API_BASE_URL: apiOrigin },
    },
  ],
});
