import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "e2e",
  use: {
    baseURL: process.env.E2E_URL || "http://127.0.0.1:8000",
    launchOptions: {
      executablePath: process.env.CHROME_PATH || "/opt/google/chrome/chrome",
      args: ["--no-sandbox", "--disable-dev-shm-usage"],
    },
  },
  reporter: "list",
});
