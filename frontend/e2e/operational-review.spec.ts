import { test, expect } from "@playwright/test";
for (const width of [360, 390, 768, 1440]) {
  test(`Revisión humana con salida, persistencia y cambio de generación ${width}px · MOCK`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 940 });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    let generation = 0;
    let sourceObsolete = false;
    let human: any = {
      state: "pending",
      resolved_suppliers: [],
      remaining_suppliers: ["QA-S"],
      decisions: [],
      analysis_id: "MOCK-A0",
      source_hash: "MOCK-HASH",
      generation: 0,
      source_version: 1,
      history: [],
    };
    const analysis = {
      analysis_status: "review",
      is_risk: "Y",
      urgent: "N",
      event_type: "utility_outage",
      affected_supplier_ids: ["QA-S"],
      review_reasons: ["association_support_insufficient:QA-S"],
      evidence: [
        {
          id: "e1",
          field: "summary",
          text: "MOCK regional power interruption.",
          start: 0,
          end: 33,
        },
      ],
      assessments: [
        {
          supplier_id: "QA-S",
          p_link: 0.55,
          p_risk: 0.8,
          p_urgent: 0.1,
          is_risk: "Y",
          urgent: "N",
          needs_review: true,
          review_reasons: [],
          severity: 5,
          priority: 30,
          priority_band: "medium",
          factor_values: {},
          evidence_ids: ["e1"],
          impact_status: "monitoring",
        },
      ],
    };
    const frozen = JSON.stringify(analysis);
    const article = () => ({
      id: "QA-NEWS",
      generation,
      version: 1,
      news_id: "QA",
      headline: "MOCK regional electricity notice",
      summary: "MOCK regional power interruption.",
      source: "MOCK source",
      published_date: "2026-10-19",
      split: "training",
      state: "review",
      analysis,
    });
    const supplier = {
      supplier_id: "QA-S",
      name: "MOCK Supplier",
      country: "MOCK country",
      city: "MOCK city",
      material: "MOCK API",
      geography: { status: "ambiguous" },
    };
    await page.route("**/api/**", async (route) => {
      const p = new URL(route.request().url()).pathname.slice(4);
      if (p === "/articles/QA-NEWS/review") {
        if (route.request().method() === "POST") {
          const body = route.request().postDataJSON();
          expect(body.association).toBe(
            width === 1440 ? "confirmed" : "rejected",
          );
          if (width === 1440) {
            expect(body.impact_status).toBe("active");
            expect(body.urgent).toBe("N");
            expect(body.severity).toBe(6);
          }
          expect(body.generation).toBe(0);
          human = {
            ...human,
            state: "resolved",
            resolved_suppliers: ["QA-S"],
            remaining_suppliers: [],
            history: [
              {
                ...body,
                id: "MOCK-H1",
                created_at: "2026-10-19",
                actor: "MOCK presenter",
                obsolete: false,
              },
            ],
            decisions: [{ supplier_id: "QA-S", association: "rejected" }],
          };
        }
        return route.fulfill({
          json: { ...human, generation, analysis_id: "MOCK-A" + generation },
        });
      }
      const data: any = {
        "/session": { presenter: true, csrf: "MOCK" },
        "/config": { bands: [] },
        "/overview": {},
        "/sources": [],
        "/suppliers": { items: [supplier] },
        "/batches": [],
        "/alerts": { items: [], unread: 0, cursor: 0 },
        "/articles": [article()],
        "/articles/QA-NEWS": article(),
      };
      return route.fulfill({ json: data[p] ?? {} });
    });
    await page.goto("/noticias/QA-NEWS?context=exercise");
    await page
      .getByRole("combobox", { name: "Proveedor de la revisión" })
      .selectOption("QA-S");
    await page
      .getByLabel("Conclusión del vínculo", { exact: true })
      .selectOption(width === 1440 ? "confirmed" : "rejected");
    if (width === 1440) {
      await page
        .getByLabel("Decisión humana de riesgo", { exact: true })
        .selectOption("Y");
      await page
        .getByLabel("Estado humano del impacto", { exact: true })
        .selectOption("active");
      await page.getByLabel("Severidad humana", { exact: true }).fill("6");
    }
    await page
      .getByLabel("Evidencia humana", { exact: true })
      .fill("MOCK explicit route exclusion, checked separately.");
    await page
      .getByLabel("Procedencia humana", { exact: true })
      .fill("MOCK reference");
    await page
      .getByLabel("Observación de revisión", { exact: true })
      .fill("MOCK supplier route differs from the event scope.");
    await page
      .getByRole("button", { name: "Registrar decisión humana", exact: true })
      .click();
    await expect(
      page.getByText("Revisión resuelta", { exact: true }),
    ).toBeVisible();
    await page.reload();
    await expect(
      page.getByText("Revisión resuelta", { exact: true }),
    ).toBeVisible();
    await page
      .getByRole("combobox", { name: "Proveedor de la revisión" })
      .selectOption("QA-S");
    await page
      .getByLabel("Observación de revisión", { exact: true })
      .fill("MOCK unsaved note must survive polling changes.");
    generation = 1;
    await expect(page.getByText(/El análisis o la fuente cambió/)).toBeVisible({
      timeout: 10000,
    });
    await expect(
      page.getByLabel("Observación de revisión", { exact: true }),
    ).toHaveValue("MOCK unsaved note must survive polling changes.");
    expect(JSON.stringify(analysis)).toBe(frozen);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect(errors).toEqual([]);
  });
  test(`RSS lote explícito con progreso y error sin negativo ${width}px · MOCK`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 940 });
    let posts = 0;
    const rows = ["ONE", "TWO"].map((id) => ({
      id,
      headline: "MOCK " + id,
      summary: "MOCK text",
      source: "MOCK RSS",
      published_date: "2026-10-19",
      state: "pending",
      split: "rss",
      version: 1,
      generation: 0,
      analysis: null,
      preliminary_relevance: {
        level: "geography",
        reasons: ["MOCK geographic candidate only"],
      },
    }));
    await page.route("**/api/**", async (route) => {
      const p = new URL(route.request().url()).pathname.slice(4);
      if (p === "/analysis/rss") {
        posts++;
        expect(route.request().postDataJSON()).toEqual({
          article_ids: ["ONE", "TWO"],
          analysis_profile: "radar-1.0.0-candidate",
        });
        return route.fulfill({
          status: 202,
          json: { job_ids: ["J1", "J2"], articles: 2, maximum_requests: 72 },
        });
      }
      if (p.startsWith("/jobs/"))
        return route.fulfill({
          json: {
            id: p.split("/").pop(),
            article_id: p.endsWith("J1") ? "ONE" : "TWO",
            state: p.endsWith("J1") ? "done" : "error",
            error: p.endsWith("J2") ? "MOCK_CONTRACT_ERROR" : null,
            network_requests: 1,
          },
        });
      const data: any = {
        "/session": { presenter: true, csrf: "MOCK" },
        "/config": { bands: [] },
        "/overview": {},
        "/sources": [],
        "/suppliers": { items: [] },
        "/batches": [],
        "/alerts": { items: [], unread: 0, cursor: 0 },
        "/articles": rows,
      };
      return route.fulfill({ json: data[p] ?? {} });
    });
    await page.goto("/noticias?context=rss");
    await page.getByText(/Seleccionar noticias para análisis manual/).click();
    await page
      .getByRole("combobox", { name: "Perfil de análisis RSS", exact: true })
      .selectOption("radar-1.0.0-candidate");
    await page
      .getByRole("checkbox", {
        name: "Seleccionar noticia MOCK ONE",
        exact: true,
      })
      .check();
    await page
      .getByRole("checkbox", {
        name: "Seleccionar noticia MOCK TWO",
        exact: true,
      })
      .check();
    await page
      .getByRole("checkbox", { name: /Confirmo esta selección/ })
      .check();
    await page
      .getByRole("button", { name: "Analizar selección", exact: true })
      .click();
    await expect(
      page.getByText(/1\/2 análisis terminados · 1 errores/),
    ).toBeVisible();
    await expect(page.getByText(/MOCK_CONTRACT_ERROR/)).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Ver resultado o diagnosticar error" }),
    ).toHaveCount(2);
    expect(posts).toBe(1);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });
}
