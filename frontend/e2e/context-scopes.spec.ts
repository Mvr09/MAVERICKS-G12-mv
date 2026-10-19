import { test, expect } from "@playwright/test";
for (const width of [360, 390, 768, 1024, 1440])
  test(`Fuentes distingue almacenadas y novedades en Ejercicio ${width} · MOCK`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 940 });
    let paidWrites = 0;
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.route("**/api/**", async (route) => {
      const u = new URL(route.request().url()),
        p = u.pathname.slice(4);
      if (route.request().method() !== "GET" && p.includes("analysis"))
        paidWrites++;
      const source = {
        id: "QA-SOURCE",
        name: "MOCK source",
        status: "unchanged",
        last_attempt_at: "2026-10-19",
        last_success_at: "2026-10-19",
        http_status: 304,
        item_count: 0,
        received_count: 500,
        duplicates: 497,
        stored_unique: 2,
        stored_versions: 3,
        job_state: "done",
      };
      const rss = [1, 2].map((n) => ({
        id: "QA" + n,
        news_id: "QA" + n,
        split: "rss",
        headline: "MOCK RSS " + n,
        summary: "MOCK",
        state: "done",
        published_date: "2026-10-19",
        source: "MOCK source",
      }));
      const defaults: any = {
        "/session": { presenter: true, csrf: "MOCK" },
        "/config": { bands: [], rss_paid_analysis: false },
        "/overview": { received: 47 },
        "/suppliers": { items: [] },
        "/articles": u.searchParams.get("context") === "rss" ? rss : [],
        "/sources": [source],
        "/batches": [],
        "/alerts": { items: [], cursor: 0, unread: 0 },
        "/worker": { online: true, compatible: true },
      };
      await route.fulfill({ json: defaults[p] || {} });
    });
    await page.goto("/fuentes?context=exercise");
    await expect(page.getByRole("heading", { name: "Fuentes." })).toBeVisible();
    await expect(page.getByText(/Estás en Ejercicio/)).toBeVisible();
    await expect(
      page.getByText("2 artículos RSS únicos almacenados", { exact: true }),
    ).toBeVisible();
    await expect(page.getByText(/0 incorporaciones observadas/)).toBeVisible();
    await expect(
      page.getByText(/No hay noticias pendientes de analizar/),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Analizar hasta 0/ }),
    ).toHaveCount(0);
    await page.getByRole("link", { name: "Consultar resultados RSS" }).click();
    await expect(
      page.getByRole("combobox", { name: "Contexto", exact: true }),
    ).toHaveValue("rss");
    expect(paidWrites).toBe(0);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect(errors).toEqual([]);
  });
