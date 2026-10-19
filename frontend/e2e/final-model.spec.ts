import { test, expect } from "@playwright/test";
const metric = {
  tp: 19,
  fp: 0,
  fn: 0,
  tn: 21,
  n: 40,
  positives: 19,
  precision: 1,
  recall: 1,
  f1: 1,
};
const s = { n: 74, mean: 2, median: 1.8, p95: 3 };
function report(sample = "labelled") {
  return {
    profile: {
      profile: "radar-1.0.0-candidate",
      evaluation_commit: "MOCK-COMMIT",
      components: {
        model: "jev-1.13.0",
        questions: "decision-3.4.2",
        review: "review-1.3.1",
      },
      historical_rate: { per_million_tokens: 0.03941248835 },
    },
    sample,
    status: "complete",
    limit:
      "Training y validation ya inspeccionados; no validación independiente ni precisión RSS.",
    evaluation: { name: "MOCK campaña persistida", completed_at: "2026-10-19" },
    quality: {
      total: 40,
      completed: 40,
      errors: 0,
      pending: 0,
      quality: {
        risk: metric,
        urgent: {
          ...metric,
          tp: 7,
          fp: 2,
          tn: 31,
          positives: 7,
          precision: 7 / 9,
          f1: 0.875,
        },
        suppliers: {
          ...metric,
          tp: 32,
          fp: 5,
          fn: 0,
          n: 40,
          exact: 37,
          precision: 32 / 37,
          recall: 1,
          f1: 64 / 69,
        },
      },
      automatic: 19,
      automatic_rate: 19 / 40,
      review: 21,
      automatic_errors: 0,
      automatic_labelled: 19,
    },
    performance: {
      fresh: s,
      cached_or_mixed: { n: 0 },
      queue: { ...s, mean: 28 },
      tokens_reported: { n: 74, mean: 31333 },
      start: "2026-10-19",
      end: "2026-10-19",
      environment: { service: "MOCK local", python: "3.12" },
      definition: "Duración individual, no campaña / noticias.",
      new_requests: 265,
    },
    railway: {
      fresh: { n: 0, mean: null },
      cached_or_mixed: { n: 0, mean: null },
      queue: { mean: null },
      definition: "Nuevas mediciones separadas",
    },
  };
}
for (const width of [360, 390, 768, 1024, 1440])
  test(`Perfil final, matrices y simulador sin inferencia ${width} · MOCK`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 940 });
    let writes = 0;
    await page.route("**/api/**", async (route) => {
      if (route.request().method() !== "GET") writes++;
      const u = new URL(route.request().url()),
        p = u.pathname.slice(4);
      const basics: any = {
        "/session": { presenter: true, csrf: "MOCK" },
        "/config": { bands: [] },
        "/overview": {},
        "/suppliers": { items: [] },
        "/articles": [],
        "/sources": [],
        "/batches": [],
        "/alerts": { items: [], cursor: 0, unread: 0 },
      };
      await route.fulfill({
        json:
          p === "/model/final"
            ? report(u.searchParams.get("sample") || "labelled")
            : basics[p] || {},
      });
    });
    await page.goto("/modelo");
    await expect(
      page.getByRole("heading", {
        name: "Perfil final de Supplier Risk Radar",
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      page.getByLabel("Tokens por noticia", { exact: true }),
    ).toHaveValue("31333");
    await expect(
      page.getByRole("combobox", { name: "Perfil A", exact: true }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("heading", { name: "Riesgo", exact: true }),
    ).toHaveCount(2);
    const cost = page
      .getByText("Coste estimado", { exact: true })
      .locator("..")
      .locator("strong");
    await page.getByLabel("Número de noticias", { exact: true }).fill("1");
    await page.getByLabel("Tokens por noticia", { exact: true }).fill("1");
    await expect(cost).toHaveText("0,00000004 $");
    await page.getByLabel("Número de noticias", { exact: true }).fill("0");
    await expect(cost).toHaveText("0 $");
    await page.getByLabel("Número de noticias", { exact: true }).fill("-1");
    await expect(page.getByRole("alert")).toContainText("no negativos");
    await page.getByLabel("Número de noticias", { exact: true }).fill("10");
    await page.getByLabel("Tokens por noticia", { exact: true }).fill("1000");
    await expect(cost).toHaveText("0,00039412 $");
    await page
      .getByLabel("Muestra evaluada", { exact: true })
      .selectOption("validation");
    await page.reload();
    await expect(
      page.getByLabel("Muestra evaluada", { exact: true }),
    ).toHaveValue("validation");
    await expect(
      page.getByLabel("Tokens por noticia", { exact: true }),
    ).toHaveValue("1000");
    for (const w of [width, 650, 820, width]) {
      await page.setViewportSize({ width: w, height: 940 });
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
    }
    expect(writes).toBe(0);
    if (width === 390)
      await page.screenshot({
        path: ".runtime/final-model-mock-390.png",
        fullPage: true,
      });
  });
test("Modelo mantiene datos durante actualización y recupera fallos · MOCK", async ({
  page,
}) => {
  let fail = true,
    resolve: any;
  let hold = new Promise((r) => (resolve = r));
  await page.route("**/api/**", async (route) => {
    const p = new URL(route.request().url()).pathname.slice(4);
    if (p === "/model/final") {
      await hold;
      if (fail)
        return route.fulfill({
          status: 503,
          json: { message: "MOCK métricas temporalmente no disponibles" },
        });
      return route.fulfill({ json: report() });
    }
    const b: any = {
      "/session": { presenter: false },
      "/config": { bands: [] },
      "/overview": {},
      "/suppliers": { items: [] },
      "/articles": [],
      "/sources": [],
      "/batches": [],
      "/alerts": { items: [], cursor: 0, unread: 0 },
    };
    await route.fulfill({ json: b[p] || {} });
  });
  await page.goto("/modelo");
  await expect(
    page.getByText("Cargando perfil, métricas y telemetría…"),
  ).toBeVisible();
  resolve();
  await expect(page.getByRole("alert")).toContainText("MOCK métricas");
  fail = false;
  await page
    .getByRole("button", { name: "Reintentar carga de Modelo" })
    .click();
  await expect(page.getByLabel("Número de noticias")).toBeVisible();
});
