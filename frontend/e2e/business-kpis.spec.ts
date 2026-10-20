import { test, expect, type Page } from "@playwright/test";

const incident = (id: string, headline: string) => ({
  id,
  state: "active",
  priority: 60,
  historical_priority: 60,
  event_type: "operational_disruption",
  event_date: "2026-10-18",
  history: [
    {
      article_id: "A" + id,
      headline,
      published_date: "2026-10-18",
      assessment: { urgent: "N", needs_review: false, review_reasons: [] },
    },
  ],
});

const supplier = (over: Record<string, any>) => ({
  country: "España",
  city: "MOCK",
  criticality: "High",
  quality_score: 80,
  products: [],
  priority: null,
  urgent: false,
  needs_review: false,
  status: "positive",
  incident_count: 0,
  incidents: [],
  latest_evidence: null,
  reason: "MOCK",
  ...over,
});

// S1 and S2 exposed; S3 without incidents. Totals checked below.
const suppliers = [
  supplier({
    supplier_id: "S1",
    name: "MOCK Envases Uno",
    category: "Secondary Packaging",
    material: "Envase MOCK",
    single_source: "Y",
    alternate_id: null,
    lead_days: 20,
    inventory_days: 5,
    share_category_pct: 40,
    annual_spend: 24000000,
    materials: [
      { material_id: "M1", name: "Envase MOCK", primary_id: "S1", alternate_id: null, products: ["P1", "P2"] },
    ],
    priority: 70,
    status: "active",
    incident_count: 1,
    incidents: [incident("I1", "MOCK cierre de planta")],
  }),
  supplier({
    supplier_id: "S2",
    name: "MOCK Transporte Dos",
    category: "Logistics",
    material: "Transporte MOCK",
    single_source: "N",
    alternate_id: "S3",
    lead_days: 10,
    inventory_days: null,
    share_category_pct: 20,
    annual_spend: 7800000,
    materials: [
      { material_id: "M2", name: "Transporte MOCK", primary_id: "S2", alternate_id: "S3", products: ["P2", "P3"] },
    ],
    priority: 40,
    needs_review: true,
    status: "review",
    incident_count: 1,
    incidents: [incident("I2", "MOCK huelga portuaria")],
  }),
  supplier({
    supplier_id: "S3",
    name: "MOCK Química Tres",
    category: "API",
    material: "Principio MOCK",
    single_source: "Y",
    alternate_id: null,
    lead_days: 30,
    inventory_days: null,
    share_category_pct: 10,
    annual_spend: 47700000,
    materials: [
      { material_id: "M3", name: "Principio MOCK", primary_id: "S3", alternate_id: null, products: ["P4"] },
    ],
  }),
];

const mockApi = async (page: Page, rows = suppliers) => {
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname.slice(4);
    const data: Record<string, any> = {
      "/session": { presenter: false },
      "/config": {
        bands: [
          { id: "low", label_es: "Baja", min: 0 },
          { id: "medium", label_es: "Media", min: 35 },
          { id: "high", label_es: "Alta", min: 65 },
          { id: "critical", label_es: "Crítica", min: 80 },
        ],
        cooldown_seconds: 30,
      },
      "/overview": { urgent_suppliers: 0, active_incidents: 2, processed: 2, received: 2, pending: 0, healthy_sources: 0 },
      "/suppliers": { items: rows, total: rows.length },
      "/articles": [],
      "/sources": [],
      "/batches": [],
      "/alerts": { items: [], unread: 0, cursor: 0 },
    };
    return route.fulfill({ json: data[path] ?? {} });
  });
};

for (const width of [360, 390, 768, 1440])
  test(`Exposición de compras ${width}px (MOCK identificado)`, async ({ page }) => {
    await page.setViewportSize({ width, height: 960 });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await mockApi(page);
    await page.goto("/");
    const panel = page.locator("section.bkpi");
    await expect(panel.getByRole("heading", { name: "Exposición de compras" })).toBeVisible();
    const tile = (label: string) => panel.locator(".kpi").filter({ hasText: label });
    await expect(panel.locator(".kpi")).toHaveCount(4);
    await expect(panel.locator(".bkpi-heading p")).toContainText(
      "Sobre 2 proveedores con incidente activo (2 incidentes) en el origen seleccionado · por validar: 1",
    );
    await expect(tile("Gasto anual expuesto").locator(".kpi-value")).toHaveText("31,8 M€");
    await expect(tile("Gasto anual expuesto")).toHaveAttribute("title", /^31\.800\.000\s€ · gasto total del proveedor, no por producto$/);
    await expect(tile("Gasto anual expuesto").locator("small")).toHaveText("40 % del gasto de cartera");
    await expect(tile("Gasto anual expuesto")).toContainText("40 % del gasto de cartera");
    await expect(tile("Productos sin\u00a0plan\u00a0B").locator(".bkpi-num")).toHaveText("2 / 4");
    await expect(tile("Productos sin\u00a0plan\u00a0B").locator(".bkpi-unit")).toHaveCount(0);
    await expect(tile("Productos sin\u00a0plan\u00a0B").locator("small")).toHaveText("expuestos en total: 3\u00a0/\u00a04");
    await expect(tile("Fuente única afectados").locator(".kpi-value")).toHaveText("1");
    await expect(tile("Fuente única afectados")).toContainText("1 de 2 fuentes únicas de la cartera");
    await expect(tile("Fuente única afectados")).toHaveAttribute("title", "MOCK Envases Uno");
    await expect(tile("Cobertura insuficiente").locator(".kpi-value")).toHaveText("1");
    // S2 is Logistics: excluded from the comparison but counted as "no aplica".
    await expect(tile("Cobertura insuficiente")).toHaveAttribute("title", "MOCK Envases Uno");
    await expect(tile("Cobertura insuficiente").locator("small")).toHaveText(
      "Stock menor que el plazo de reposición · sin\u00a0dato:\u00a00 · no\u00a0aplica:\u00a01",
    );
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    ).toBe(true);
    if (width === 1440) {
      // Same size as the Resumen tiles above when everything fits.
      const top = await page.locator(".kpis .kpi-value").first().evaluate((e) => getComputedStyle(e).fontSize);
      for (const v of await panel.locator(".bkpi-value").all())
        expect(await v.evaluate((e) => getComputedStyle(e).fontSize)).toBe(top);
    }
    await panel.screenshot({ path: `test-results/business-kpis-mock-${width}.png` });
    expect(errors).toEqual([]);
  });

// Every width from 320 to 1440 px: no tile value may be clipped by its card.
for (const spend of [24000000, 999000000])
  test(`Exposición de compras sin cortes 320-1440px · ${spend} € (MOCK identificado)`, async ({ page }) => {
    await mockApi(page, suppliers.map((s) => (s.supplier_id === "S1" ? { ...s, annual_spend: spend } : s)));
    await page.setViewportSize({ width: 1440, height: 960 });
    await page.goto("/");
    await expect(page.locator("section.bkpi .kpi")).toHaveCount(4);
    const clipped: string[] = [];
    for (let width = 320; width <= 1440; width += 10) {
      await page.setViewportSize({ width, height: 960 });
      // The fit runs in a ResizeObserver, before the next paint.
      await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
      const bad = await page.evaluate(() =>
        [...document.querySelectorAll("section.bkpi .kpi")]
          .filter((card) => {
            const box = card.getBoundingClientRect();
            return [...card.querySelectorAll(".bkpi-num, .bkpi-unit")].some((el) => {
              const r = el.getBoundingClientRect();
              return r.right > box.right - 1 || el.scrollWidth > Math.ceil(r.width) + 1;
            });
          })
          .map((card) => card.querySelector(".kpi-top span")?.textContent || "?"),
      );
      if (bad.length) clipped.push(`${width}px: ${bad.join(", ")}`);
      // Either one row with all tiles or rows of two (never 3 + 1).
      const rows = await page.evaluate(() => {
        const tops = [...document.querySelectorAll("section.bkpi .kpi")].map((c) => Math.round(c.getBoundingClientRect().top));
        return [...new Set(tops)].map((t) => tops.filter((x) => x === t).length);
      });
      if (!(rows.length === 1 || rows.every((n) => n === 2)))
        clipped.push(`${width}px: filas ${rows.join("+")}`);
      if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth))
        clipped.push(`${width}px: desbordamiento global`);
      // Panel, last card and "Ver proveedores" stay within the same right edge as the Resumen tiles.
      const edge = await page.evaluate(() => {
        const right = (e: Element | null) => e!.getBoundingClientRect().right;
        const link = document.querySelector("section.bkpi .bkpi-heading a") as HTMLElement;
        const limit = right(document.querySelector(".kpis")) + 0.5;
        return (
          right(document.querySelector("section.bkpi")) <= limit &&
          right(document.querySelector("section.bkpi .kpi:last-child")) <= limit &&
          right(link) <= limit &&
          link.scrollWidth <= link.clientWidth + 1
        );
      });
      if (!edge) clipped.push(`${width}px: borde derecho`);
    }
    expect(clipped).toEqual([]);
  });

