import { test, expect } from "@playwright/test";

for (const width of [360, 390, 768, 1440])
  test(`Mesa procurement y actualización estable ${width}px (MOCK identificado)`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 960 });
    let done = false,
      detailCalls = 0;
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const supplier: any = {
      supplier_id: "S024",
      name: "MOCK Helixa Supply",
      country: "China",
      city: "Hangzhou",
      category: "Secondary Packaging",
      material: "Prospectos MOCK",
      criticality: "High",
      single_source: "Y",
      alternate_id: "S025",
      lead_days: 20,
      inventory_days: 0,
      share_category_pct: 12,
      annual_spend: 0,
      quality_score: 80,
      products: ["Producto MOCK"],
      materials: [
        {
          material_id: "M001",
          name: "Prospectos MOCK",
          primary_id: "S024",
          alternate_id: "S025",
          products: ["Producto MOCK"],
        },
      ],
      priority: 72,
      urgent: true,
      needs_review: false,
      status: "active",
      incident_count: 1,
      latest_evidence: "2026-10-18",
      reason: "MOCK interrupción con dependencia de fuente única",
      incidents: [
        {
          id: "I1",
          state: "active",
          priority: 72,
          historical_priority: 72,
          event_type: "operational_disruption",
          event_date: "2026-10-18",
          history: [
            {
              article_id: "A1",
              headline: "MOCK restricción regional",
              published_date: "2026-10-18",
              assessment: {
                p_link: 0.9,
                severity: 6,
                factor_values: { C: 1 },
                review_reasons: [],
              },
            },
          ],
        },
      ],
    };
    supplier.incidents.push({
      id: "I2",
      state: "resolved",
      priority: 0,
      historical_priority: 80,
      event_type: "operational_disruption",
      event_date: "2026-10-17",
      history: [
        {
          article_id: "A2",
          headline: "MOCK recuperación",
          assessment: { urgent: "N", needs_review: false, review_reasons: [] },
        },
      ],
    });
    const article = () => ({
      id: "A1",
      headline: "MOCK restricción regional",
      summary: "MOCK noticia sintética para interfaz.",
      source: "MOCK",
      published_date: "2026-10-18",
      fetched_at: "2026-10-18",
      version: 1,
      generation: 0,
      split: "rss",
      state: done ? "review" : "pending",
      analysis: null,
    });
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname.slice(4);
      if (path === "/drafts")
        return route.fulfill({
          json: { id: "D1", text: "MOCK consulta: confirmar disponibilidad." },
        });
      if (path === "/suppliers/S024") detailCalls++;
      const data: Record<string, any> = {
        "/session": { presenter: true, csrf: "MOCK" },
        "/config": { bands: [], cooldown_seconds: 30 },
        "/overview": {
          urgent_suppliers: 1,
          active_incidents: 1,
          processed: done ? 1 : 0,
          received: 1,
          pending: done ? 0 : 1,
          healthy_sources: 0,
        },
        "/suppliers": { items: [supplier] },
        "/suppliers/S024": { ...supplier, articles: [article()] },
        "/articles": [article()],
        "/sources": [],
        "/batches": [],
        "/alerts": {
          items: [
            {
              id: 1,
              incident_id: "I2",
              revision: 1,
              acknowledged: true,
              supplier_id: "S024",
              supplier_name: supplier.name,
              priority: 0,
              headline: "MOCK recuperación",
              needs_review: false,
              sound_eligible: false,
              created_at: "2026-10-17",
              state: "resolved",
            },
          ],
          unread: 0,
          cursor: 1,
        },
      };
      return route.fulfill({ json: data[path] ?? {} });
    });
    await page.goto("/");
    await page
      .getByRole("combobox", { name: "Contexto", exact: true })
      .selectOption("rss");
    await expect(
      page.getByRole("heading", {
        name: "De la señal a la siguiente decisión",
      }),
    ).toBeVisible();
    await expect(
      page.getByText("Exposición potencial · cartera simulada").first(),
    ).toBeVisible();
    await expect(
      page
        .getByText("Contactar al proveedor y confirmar entregas", {
          exact: false,
        })
        .first(),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `../reports/${process.env.SCREENSHOT_PREFIX || "procurement-mock"}-${width}.png`,
      fullPage: true,
    });
    await page
      .getByRole("link", { name: "Revisar suministro", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Impacto y siguiente acción" }),
    ).toBeVisible();
    await expect(
      page.getByText("0 días de inventario", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("Productos relacionados: Producto MOCK", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Prospectos MOCK · Principal" }),
    ).toHaveAttribute("href", "/materiales/M001?context=rss");
    await page
      .locator(".incident-card")
      .filter({ hasText: "MOCK restricción regional" })
      .getByRole("button", { name: "Consultar proveedor", exact: true })
      .click();
    const draft = page.getByRole("textbox", {
      name: "Texto de la consulta",
      exact: true,
    });
    await expect(draft).toBeVisible();
    await draft.fill("MOCK edición conservada");
    await draft.focus();
    await expect
      .poll(() => detailCalls, { timeout: 8000 })
      .toBeGreaterThanOrEqual(2);
    await expect(draft).toHaveValue("MOCK edición conservada");
    await expect(draft).toBeFocused();
    await page.goto("/noticias?context=rss");
    const search = page.getByRole("textbox", {
      name: "Buscar noticias",
      exact: true,
    });
    await search.fill("MOCK");
    await search.focus();
    const position = (await search.boundingBox())!.y;
    done = true;
    await expect(
      page
        .getByRole("status")
        .filter({ hasText: "actualización desde que abriste" }),
    ).toContainText("1 actualización", { timeout: 10000 });
    await expect(search).toHaveValue("MOCK");
    await expect(search).toBeFocused();
    expect(Math.abs((await search.boundingBox())!.y - position)).toBeLessThan(
      5,
    );
    await page.goto("/alertas?context=rss");
    await expect(
      page.getByText(
        "Confirmar la normalización de entregas y conservar el historial.",
        { exact: true },
      ),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Ver evidencia: MOCK recuperación" }),
    ).toHaveAttribute("href", "/noticias/A2?context=rss");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect(errors).toEqual([]);
  });
