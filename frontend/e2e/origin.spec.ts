import { test, expect } from "@playwright/test";

for (const width of [360, 1440]) {
  test(`LiveDay y filtro de origen actualizan Resumen sin recargar a ${width}px (mocks identificados)`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    let analyzed = false;
    let queued = false;
    const batch = () => ({
      id: "MOCK-LIVE",
      split: "liveday",
      filename: "MOCK-LiveDay.xlsx",
      origin_label: "MOCK-LiveDay.xlsx",
      count: 14,
      done: analyzed ? 14 : 0,
      pending: analyzed ? 0 : 14,
      errors: 0,
      queued: queued && !analyzed ? 14 : 0,
    });
    await page.route("**/api/session", (r) =>
      r.fulfill({ json: { presenter: true, csrf: "MOCK" } }),
    );
    await page.route("**/api/batches", (r) => r.fulfill({ json: [batch()] }));
    await page.route("**/api/imports", (r) =>
      r.fulfill({
        json: { batch_id: "MOCK-LIVE", split: "liveday", rows: 14 },
      }),
    );
    await page.route("**/api/batches/MOCK-LIVE/analyze", async (r) => {
      queued = true;
      await new Promise((resolve) => setTimeout(resolve, 350));
      await r.fulfill({ status: 202, json: { job_ids: ["MOCK-JOB"] } });
      setTimeout(() => {
        analyzed = true;
      }, 500);
    });
    await page.route("**/api/overview?**", (r) => {
      const u = new URL(r.request().url());
      const filtered = u.searchParams.get("origin") === "batch:MOCK-LIVE";
      return r.fulfill({
        json: {
          received: filtered ? 14 : 37,
          processed: filtered ? (analyzed ? 14 : 0) : 37,
          pending: filtered && !analyzed ? 14 : 0,
          urgent_suppliers: 0,
          active_incidents: filtered ? (analyzed ? 1 : 0) : 4,
          healthy_sources: 6,
        },
      });
    });
    await page.route("**/api/suppliers?**", (r) =>
      r.fulfill({ json: { items: [], total: 0 } }),
    );
    await page.route("**/api/articles?**", (r) => {
      const u = new URL(r.request().url());
      const origin = u.searchParams.get("origin");
      const title =
        origin === "batch:MOCK-LIVE"
          ? "MOCK: señal de LiveDay"
          : origin?.startsWith("rss:")
            ? "MOCK: señal de RSS seleccionado"
            : "MOCK: contexto completo";
      return r.fulfill({
        json: [
          {
            id: "MOCK",
            headline: title,
            summary: "Solo prueba de UI",
            source: "MOCK publisher",
            origin_label:
              origin === "batch:MOCK-LIVE" ? "MOCK-LiveDay.xlsx" : "MOCK RSS",
            published_date: "2026-10-06",
            state: analyzed ? "done" : "pending",
            analysis: null,
            version: 1,
            cached: false,
          },
        ],
      });
    });
    await page.goto("/");
    await page.getByLabel("Contexto", { exact: true }).selectOption("rss");
    await page.getByLabel("Archivo Excel").setInputFiles({
      name: "MOCK-LiveDay.xlsx",
      mimeType:
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      buffer: Buffer.from("MOCK: importer HTTP stub"),
    });
    await expect(page.getByLabel("Contexto", { exact: true })).toHaveValue(
      "exercise",
    );
    await expect(page.getByLabel("Origen de los datos")).toHaveValue(
      "batch:MOCK-LIVE",
    );
    await expect(
      page.getByRole("link", { name: "MOCK: señal de LiveDay" }),
    ).toBeVisible();
    await expect(
      page.getByText("14 entradas · 0 completadas", { exact: false }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Analizar", exact: true }).click();
    await expect(
      page.getByRole("button", { name: "Encolando…", exact: true }),
    ).toBeDisabled();
    await expect(
      page.getByText("14 entradas · 14 completadas", { exact: false }),
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByRole("button", { name: "Exportar", exact: true }),
    ).toBeEnabled();
    await expect(
      page.getByRole("button", { name: "Reanalizar lote", exact: true }),
    ).toBeVisible();
    const rssOption = page
      .locator('#summary-origin optgroup[label="Fuentes RSS"] option')
      .first();
    const rssValue = await rssOption.getAttribute("value");
    await page.getByLabel("Origen de los datos").selectOption(rssValue!);
    await expect(page.getByLabel("Contexto", { exact: true })).toHaveValue(
      "rss",
    );
    await expect(
      page.getByRole("link", { name: "MOCK: señal de RSS seleccionado" }),
    ).toBeVisible();
    await page.getByLabel("Origen de los datos").selectOption("context:rss");
    await expect(page.getByLabel("Contexto", { exact: true })).toHaveValue(
      "rss",
    );
    await expect(page.getByLabel("Origen de los datos")).toHaveValue(
      "context:rss",
    );
    await page
      .getByLabel("Origen de los datos")
      .selectOption("context:exercise");
    await expect(page.getByLabel("Contexto", { exact: true })).toHaveValue(
      "exercise",
    );
    await expect(page.getByLabel("Origen de los datos")).toHaveValue(
      "context:exercise",
    );
    await page.goBack();
    await expect(page.getByLabel("Origen de los datos")).toHaveValue(
      "context:rss",
    );
    await expect(page.getByLabel("Contexto", { exact: true })).toHaveValue(
      "rss",
    );
    await page.goForward();
    await expect(page.getByLabel("Origen de los datos")).toHaveValue(
      "context:exercise",
    );
    await page.getByRole("link", { name: "Noticias", exact: true }).click();
    await page.getByRole("link", { name: "Resumen", exact: true }).click();
    await expect(page).toHaveURL(/origen=context%3Aexercise/);
    await page.reload();
    await expect(page.getByLabel("Origen de los datos")).toHaveValue(
      "context:exercise",
    );
    await page.getByLabel("Origen de los datos").focus();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `../reports/${process.env.SCREENSHOT_PREFIX || "origin-mock"}-${width}.png`,
      fullPage: true,
    });
  });
}
