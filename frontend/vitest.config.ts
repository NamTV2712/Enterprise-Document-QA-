import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    // Playwright specs live in e2e/ and run through `bun run test:e2e`.
    exclude: ["e2e/**", "node_modules/**", "dist/**"],
  },
});
