import { test, expect } from "@playwright/test";

for (const width of [360, 390, 768, 1440]) {
  test(`Etiquetas de noticia en todas las vistas a ${width}px (mocks identificados)`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const result = (category: string, uncertain = false) => ({
      event_type: category === "wildfire" ? "natural_disaster" : category,
      event_classification: {
        category,
        confidence: uncertain ? 0.4 : 0.98,
        taxonomy_version: "MOCK",
      },
      context_notes: uncertain ? ["event_type_confidence_low"] : [],
      analysis_status: "review",
      review_reasons: [],
      assessments: [],
      evidence: [],
      affected_supplier_ids: [],
      is_risk: "N",
      urgent: "N",
    });
    const make = (id: string, analysis: any, state = "review") => ({
      id,
      headline: "MOCK noticia " + id,
      summary: "MOCK sin datos reales.",
      state,
      split: "rss",
      source: "MOCK RSS",
      published_date: "2026-10-18T00:00:00Z",
      analysis,
    });
    const articles = [
      make("forest", result("wildfire")),
      make("uncertain", result("logistics_disruption", true)),
      make("pending", null, "pending"),
      make(
        "failed",
        {
          analysis_status: "error",
          event_type: null,
          review_reasons: [],
          assessments: [],
          evidence: [],
        },
        "error",
      ),
    ];
    const supplier = {
      supplier_id: "S001",
      name: "MOCK proveedor",
      category: "Services",
      country: "MOCK",
      city: "MOCK",
      materials: [],
      products: [],
      priority: 0,
      incidents: [
        {
          id: "MOCK-inc",
          state: "active",
          event_type: "natural_disaster",
          current_headline: articles[0].headline,
          event_tag: result("wildfire"),
          history: [],
          event_date: "2026-10-18T00:00:00Z",
        },
      ],
      articles: [articles[0]],
    };
    await page.route("**/api/**", async (route) => {
      expect(route.request().method()).toBe("GET");
      const path = new URL(route.request().url()).pathname.replace("/api", "");
      const values: Record<string, any> = {
        "/config": { bands: [], fixtures: true, rss_paid_analysis: false },
        "/session": { presenter: true, csrf: "MOCK" },
        "/overview": { received: 4, processed: 2 },
        "/suppliers": { items: [], total: 0 },
        "/batches": [],
        "/sources": [],
        "/worker": { online: true, compatible: true },
        "/budget": {},
        "/articles": articles,
        "/articles/forest": articles[0],
        "/suppliers/S001": supplier,
        "/articles/forest/runs": [
          {
            generation: 0,
            created_at: "2026-10-18T00:00:00Z",
            result: result("wildfire"),
          },
        ],
        "/articles/forest/comparisons": [
          {
            state: "done",
            ballots: [{ ...result("wildfire"), error: null }],
            summary: {},
          },
        ],
        "/alerts": {
          cursor: 1,
          unread: 1,
          items: [
            {
              id: 1,
              supplier_id: "S001",
              supplier_name: "MOCK proveedor",
              headline: articles[0].headline,
              state: "active",
              created_at: "2026-10-18T00:00:00Z",
              event_tag: result("wildfire"),
            },
          ],
        },
      };
      await route.fulfill({ json: values[path] ?? {} });
    });
    const tag = (text: string) =>
      page.getByLabel("Tipo de noticia: " + text, { exact: true });
    for (const route of [
      "/",
      "/noticias",
      "/fuentes",
      "/noticias/forest",
      "/proveedores/S001",
      "/alertas",
    ]) {
      await page.goto(route);
      await expect(tag("Incendio forestal").first()).toBeVisible();
      if (["/", "/noticias", "/fuentes"].includes(route)) {
        await expect(
          tag("Interrupción logística · Por confirmar"),
        ).toBeVisible();
        await expect(tag("Tipo pendiente de análisis")).toBeVisible();
        await expect(
          tag("Tipo sin determinar · Error de análisis"),
        ).toBeVisible();
      }
      if (route === "/noticias/forest") {
        await page.getByText("Historial de análisis", { exact: true }).click();
        await expect(tag("Incendio forestal")).toHaveCount(3);
        // Risk review does not make the event type uncertain.
        await expect(tag("Incendio forestal · Por confirmar")).toHaveCount(0);
      }
      if (route === "/noticias" && [360, 1440].includes(width))
        await page.screenshot({
          path: `../reports/news-tags-mock-${width}.png`,
          fullPage: true,
        });
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
    }
    expect(errors).toEqual([]);
  });
}
