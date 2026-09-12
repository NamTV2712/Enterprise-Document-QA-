import { defineConfig, devices } from "@playwright/test";

const PORT = 4173;
// Vite preview binds to the localhost hostname (IPv6 on Windows), so the
// canonical URL uses localhost instead of 127.0.0.1.
const baseURL = `http://localhost:${PORT}`;

export default defineConfig({
  testDir: "./e2e",
  // Integration-over-HTTP and dedicated local-backend specs run through their
  // own configs so the regular hermetic browser gate never depends on a
  // task-owned harness or a real API process.
  testIgnore: /(integration|workspace\.local)\.spec\.ts/,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  outputDir: "./test-results/e2e",
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
  ],
  webServer: {
    // Browser specs use the hermetic API fixture origin. Rebuild here so a
    // developer's local .env.local (often an ngrok or deployed backend) is
    // never baked into the production bundle under test.
    command: "bun run build && bunx vite preview --port 4173 --strictPort",
    url: baseURL,
    // Never reuse a preview that might have been built with a developer's
    // real backend URL; the fixture contract depends on the build above.
    reuseExistingServer: false,
    timeout: 30_000,
    env: {
      ...process.env,
      VITE_API_BASE_URL: "http://127.0.0.1:8000",
    },
  },
});
