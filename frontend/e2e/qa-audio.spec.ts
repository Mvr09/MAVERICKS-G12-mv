import { test, expect } from "@playwright/test";

test("QA identificada usa el sondeo y notify automático, sin JEV ni noticias nuevas", async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 900 });
  let posts = 0;
  await page.addInitScript(() => {
    (window as any).__qaTones = 0;
    const original = AudioContext.prototype.createOscillator;
    AudioContext.prototype.createOscillator = function () {
      (window as any).__qaTones++;
      return original.call(this);
    };
  });
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname.slice(4);
    if (route.request().method() === "POST") {
      expect(path).toBe("/qa/audio");
      posts++;
      return route.fulfill({
        json: {
          id: -999,
          revision: 1,
          acknowledged: false,
          sound_eligible: true,
          qa: true,
          delay_seconds: 5,
          title: "QA · Alerta automática controlada",
        },
      });
    }
    const article = {
      id: "MOCK-QA",
      headline: "MOCK · prueba identificada",
      summary: "Solo UI",
      source: "MOCK",
      published_date: "2026-10-18",
      context_id: "rss",
      state: "pending",
      analysis: null,
    };
    const data: Record<string, any> = {
      "/config": { bands: [], cooldown_seconds: 30, question_version: "1.0.0" },
      "/session": { presenter: true, csrf: "MOCK" },
      "/overview": {},
      "/suppliers": { items: [] },
      "/articles": [article],
      "/articles/MOCK-QA": article,
      "/articles/MOCK-QA/runs": [],
      "/sources": [],
      "/batches": [],
      "/alerts": { items: [], unread: 0, cursor: 0 },
    };
    return route.fulfill({ json: data[path] ?? {} });
  });
  await page.goto("/noticias/MOCK-QA");
  await page
    .getByRole("button", { name: "Activar sonido", exact: true })
    .last()
    .click();
  await expect(page.getByText("Activado", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Programar alerta QA (5 s)", exact: true })
    .click();
  expect(await page.evaluate(() => (window as any).__qaTones)).toBe(0);
  await expect
    .poll(() => page.evaluate(() => (window as any).__qaTones), {
      timeout: 12000,
    })
    .toBe(1);
  await expect(
    page.getByText("QA entregada al aviso automático.", { exact: false }),
  ).toBeVisible();
  await page.waitForTimeout(3200);
  expect(await page.evaluate(() => (window as any).__qaTones)).toBe(1);
  expect(posts).toBe(1);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
  ).toBe(false);
  await page.getByRole("button", { name: "Silenciar", exact: true }).click();
  await expect(page.getByText("Silenciado", { exact: true })).toBeVisible();
});
