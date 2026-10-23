import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "e2e",
  testMatch: "presentation-embed.spec.ts",
  reporter: "list",
  timeout: 45000,
  projects: [
    {
      name: "Chrome · cookies terceros restringidas",
      use: {
        browserName: "chromium",
        launchOptions: {
          executablePath:
            process.env.CHROME_PATH || "/opt/google/chrome/chrome",
          args: [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--test-third-party-cookie-phaseout",
          ],
        },
      },
    },
    {
      name: "Firefox · protección de seguimiento",
      use: {
        browserName: "firefox",
        launchOptions: {
          ...(process.env.FIREFOX_PATH
            ? { executablePath: process.env.FIREFOX_PATH }
            : {}),
          firefoxUserPrefs: { "network.cookie.cookieBehavior": 5 },
        },
      },
    },
  ],
});
