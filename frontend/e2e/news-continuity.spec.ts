import { test, expect } from "@playwright/test";
for (const width of [360, 390, 768, 1440])
  test(`Filtros, contexto y retorno conservados ${width}px · MOCK`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    const a = {
      id: "MOCK-RETURN",
      headline: "MOCK Asia-Europe pricing",
      summary: "MOCK harmless price statistic.",
      source: "MOCK Loadstar",
      published_date: "2026-10-18",
      split: "rss",
      state: "pending",
    };
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname.slice(4);
      const data: any = {
        "/session": { presenter: false },
        "/config": { bands: [], cooldown_seconds: 30 },
        "/overview": {},
        "/sources": [],
        "/suppliers": { items: [] },
        "/batches": [],
        "/alerts": { items: [], unread: 0, cursor: 0 },
        "/articles": [a],
        "/articles/MOCK-RETURN": a,
        "/articles/MOCK-RETURN/runs": [],
        "/articles/MOCK-RETURN/drafts": [],
      };
      await route.fulfill({ json: data[path] ?? {} });
    });
    await page.goto("/noticias?context=rss");
    await page
      .getByRole("combobox", { name: "Fuente", exact: true })
      .selectOption("MOCK Loadstar");
    await page
      .getByRole("textbox", { name: "Buscar noticias", exact: true })
      .fill("Asia-Europe");
    await page.getByRole("link", { name: a.headline, exact: true }).click();
    await expect(page).toHaveURL(/MOCK-RETURN\?context=rss/);
    await page.getByRole("link", { name: "← Noticias", exact: true }).click();
    await expect(
      page.getByRole("textbox", { name: "Buscar noticias", exact: true }),
    ).toHaveValue("Asia-Europe");
    await expect(
      page.getByRole("combobox", { name: "Fuente", exact: true }),
    ).toHaveValue("MOCK Loadstar");
    await expect(
      page.getByRole("link", { name: a.headline, exact: true }),
    ).toBeFocused();
    await page.reload();
    await expect(
      page.getByRole("textbox", { name: "Buscar noticias", exact: true }),
    ).toHaveValue("Asia-Europe");
    await page
      .getByRole("textbox", { name: "Buscar noticias", exact: true })
      .fill("no such news");
    await expect(
      page.getByRole("heading", { name: "Sin coincidencias", exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Limpiar", exact: true }).click();
    await expect(
      page.getByRole("link", { name: a.headline, exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });
