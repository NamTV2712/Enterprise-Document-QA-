import { defineConfig } from "@playwright/test";
import productConfig from "./playwright.product.config";

export default defineConfig({
  ...productConfig,
  testMatch: /agent-001-sweep\.spec\.ts/,
  outputDir: "./test-results/agent-001",
});
