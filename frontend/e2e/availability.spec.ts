import { test, expect } from "@playwright/test";

test("base no disponible: error visible, sin promesas rechazadas ni sondeo continuo", async ({
  page,
}) => {
  let overviews = 0;
  const unhandled: string[] = [];
  page.on("pageerror", (error) => unhandled.push(error.message));
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/config")
      return route.fulfill({
        json: {
          model: "jev-1.13.0",
          bands: [],
          cooldown_seconds: 30,
          engine_configured: false,
          rss_paid_analysis: false,
        },
      });
    if (path === "/api/overview") overviews++;
    return route.fulfill({
      status: 503,
      json: {
        code: "DATABASE_CONFIGURATION",
        message: "PostgreSQL remoto sin configurar.",
        details: null,
        retryable: false,
      },
    });
  });
  await page.clock.install();
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText(
    "PostgreSQL remoto sin configurar",
  );
  expect(overviews).toBe(1);
  await page.clock.fastForward(25000);
  expect(overviews).toBe(1);
  await page.clock.fastForward(10000);
  await expect.poll(() => overviews).toBe(2);
  expect(unhandled).toEqual([]);
});
