import { test, expect } from "@playwright/test";
for (const width of [360, 390, 768, 1440])
  test(`Decisión, hipótesis y exclusión distinguibles ${width}px · MOCK`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 940 });
    const a = (id: string, review: boolean, linked = false) => ({
      supplier_id: id,
      p_link: linked ? 0.9 : 0.1,
      p_identity: 0.1,
      p_exposure: 0.1,
      p_risk: 0.1,
      p_urgent: 0.1,
      is_risk: "N",
      urgent: "N",
      priority: 0,
      priority_band: "low",
      severity: 1,
      impact_status: "unrelated",
      needs_review: review,
      review_reasons: review ? ["association_support_insufficient"] : [],
      evidence_ids: [],
      factor_values: {},
      policy_version: "1.0.0",
      exposure_kind: review ? "unknown" : "excluded",
    });
    const article = {
      id: "MOCK-READ",
      headline: "MOCK unrelated market report",
      summary: "MOCK controlled evidence.",
      source: "MOCK",
      published_date: "2026-10-18",
      split: "rss",
      state: "review",
      analysis: {
        analysis_status: "review",
        is_risk: "N",
        urgent: "N",
        affected_supplier_ids: ["S001"],
        assessments: [
          a("S001", false, true),
          a("S002", true),
          a("S003", false),
        ],
        evidence: [],
        review_reasons: ["association_support_insufficient:S002"],
        review_details: [
          {
            code: "association_support_insufficient",
            field: "final_link",
            supplier_id: "S002",
            relevance: "association",
            requires_review: true,
            resolution_hint: "Confirma la ruta declarada.",
          },
        ],
        event_type: "other",
      },
    };
    if (width === 390) delete (article.analysis as any).review_details; // Legacy stored analyses still need actionable guidance.
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname.slice(4);
      const data: any = {
        "/session": { presenter: false },
        "/config": { bands: [] },
        "/overview": {},
        "/sources": [],
        "/suppliers": {
          items: ["S001", "S002", "S003"].map((id) => ({
            supplier_id: id,
            name: "MOCK supplier " + id,
          })),
        },
        "/articles": [article],
        "/articles/MOCK-READ": article,
        "/alerts": { items: [], unread: 0, cursor: 0 },
        "/batches": [],
      };
      await route.fulfill({ json: data[path] ?? {} });
    });
    await page.goto("/noticias/MOCK-READ?context=rss");
    await expect(
      page.getByRole("region", { name: "Qué confirmar antes de decidir" }),
    ).toBeVisible();
    await expect(
      page.locator(".assessment").filter({ hasText: "MOCK supplier S001" }),
    ).toBeVisible();
    await expect(
      page.locator(".assessment").filter({ hasText: "MOCK supplier S002" }),
    ).not.toBeVisible();
    await page
      .getByRole("link", {
        name: "Ver hipótesis y datos pendientes por proveedor →",
      })
      .click();
    await expect(
      page.locator(".assessment").filter({ hasText: "MOCK supplier S002" }),
    ).toBeVisible();
    await expect(page.locator("#provider-hypotheses > summary")).toBeFocused();
    await expect(
      page.locator(".assessment").filter({ hasText: "MOCK supplier S003" }),
    ).not.toBeVisible();
    await page
      .getByText("1 candidato descartado · sin revisión pendiente", {
        exact: true,
      })
      .click();
    await expect(
      page.locator(".assessment").filter({ hasText: "MOCK supplier S003" }),
    ).toBeVisible();
    await page
      .getByRole("link", { name: "MOCK supplier S002", exact: true })
      .click();
    await expect(page).toHaveURL(/proveedores\/S002\?context=rss/);
  });
