import { test, expect } from "@playwright/test";
for (const width of [390, 1440])
  test(`Seguimiento y consulta recuperada sin resolver incidente ${width}px · MOCK`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 940 });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    let history: any[] = [],
      draftText = "MOCK consulta persistida, no envío externo.";
    const workspace = () => ({
      incident_id: "QA-I",
      state: "active",
      current: history[0] || null,
      history,
      drafts: [
        {
          id: "QA-OLD",
          kind: "supplier",
          context_changed: true,
          preview: "MOCK old note",
        },
        {
          id: "QA-D",
          kind: "supplier",
          context_changed: false,
          preview: "MOCK current query",
        },
      ],
    });
    const s: any = {
      supplier_id: "QA-S",
      name: "MOCK Supplier",
      country: "MOCK Country",
      city: "MOCK City",
      category: "API",
      material: "MOCK API",
      criticality: "High",
      single_source: "N",
      inventory_days: 20,
      lead_days: 30,
      share_category_pct: 50,
      products: ["MOCK product"],
      materials: [],
      priority: 50,
      urgent: false,
      needs_review: false,
      status: "active",
      incident_count: 1,
      incidents: [
        {
          id: "QA-I",
          state: "active",
          priority: 50,
          historical_priority: 50,
          event_type: "utility_outage",
          event_date: "2026-10-19",
          history: [
            {
              article_id: "QA-A",
              published_date: "2026-10-19",
              headline: "MOCK utility event",
              at: "2026-10-19",
              assessment: {
                p_link: 0.9,
                p_risk: 0.9,
                p_urgent: 0.1,
                urgent: "N",
                needs_review: false,
                review_reasons: [],
                factor_values: {},
              },
            },
          ],
        },
      ],
      articles: [],
    };
    await page.route("**/api/**", async (route) => {
      const p = new URL(route.request().url()).pathname.slice(4),
        method = route.request().method();
      if (p === "/incidents/QA-I/workspace") {
        if (method === "POST") {
          const body = route.request().postDataJSON();
          expect(body.status).toBe("done");
          history = [
            { id: "QA-W1", created_at: "2026-10-19", ...body },
            ...history,
          ];
        }
        return route.fulfill({ json: workspace() });
      }
      if (p === "/drafts/QA-D") {
        if (method === "PATCH") draftText = route.request().postDataJSON().text;
        return route.fulfill({ json: { id: "QA-D", text: draftText } });
      }
      const data: any = {
        "/session": { presenter: true, csrf: "MOCK" },
        "/config": { bands: [] },
        "/overview": {},
        "/suppliers": { items: [s] },
        "/suppliers/QA-S": s,
        "/sources": [],
        "/batches": [],
        "/articles": [],
        "/alerts": { items: [], unread: 0, cursor: 0 },
      };
      return route.fulfill({ json: data[p] ?? {} });
    });
    await page.goto("/proveedores/QA-S?context=exercise");
    await page
      .getByText("Acción y seguimiento · Pendiente", { exact: true })
      .click();
    await page
      .getByRole("combobox", { name: "Estado de la acción", exact: true })
      .selectOption("done");
    await page
      .getByLabel("Siguiente acción concreta", { exact: true })
      .fill("MOCK confirmar entregas y calendario");
    await page
      .getByLabel("Observación de seguimiento", { exact: true })
      .fill("MOCK consulta completada, mantener seguimiento del evento.");
    await page
      .getByRole("button", { name: "Guardar seguimiento", exact: true })
      .click();
    await expect(
      page.getByText("Acción y seguimiento · Acción completada", {
        exact: true,
      }),
    ).toBeVisible();
    await page.locator('button[data-draft-id="QA-D"]').click();
    await expect(page.locator(".saved-query").first()).toHaveAttribute(
      "data-draft-id",
      "QA-D",
    );
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog
      .getByLabel("Texto de la consulta guardada", { exact: true })
      .fill(draftText + " MOCK edited");
    await dialog
      .getByRole("button", { name: "Guardar consulta", exact: true })
      .click();
    await expect(dialog).not.toBeVisible();
    await page.reload();
    await page
      .getByText("Acción y seguimiento · Acción completada", { exact: true })
      .click();
    await page.locator('button[data-draft-id="QA-D"]').click();
    await expect(
      page.getByLabel("Texto de la consulta guardada", { exact: true }),
    ).toHaveValue(draftText);
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).not.toBeVisible();
    expect(s.incidents[0].state).toBe("active");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect(errors).toEqual([]);
  });
