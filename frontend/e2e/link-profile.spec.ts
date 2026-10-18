import { test, expect } from "@playwright/test";
for (const width of [360, 390, 768, 1440]) {
  test(`Vínculo final, revisión por campo y perfil explícito a ${width}px (mocks identificados)`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    let proposed: any;
    let oldServer = true;
    const analysis = {
      analysis_status: "review",
      event_type: "natural_disaster",
      context_notes: [],
      model_id: "MOCK",
      question_version: "link-2.2.0",
      policy_version: "1.0.0",
      review_reasons: ["association_support_insufficient:S001"],
      review_details: [
        {
          code: "event_type_confidence_low",
          field: "event_type",
          supplier_id: null,
          relevance: "auxiliary",
          requires_review: false,
          value: 0.4,
          threshold: 0.6,
        },
        {
          code: "association_support_insufficient",
          field: "scope_and_link_evidence",
          supplier_id: "S001",
          relevance: "association",
          requires_review: true,
          value: 0.5,
          threshold: 0.65,
        },
      ],
      evidence: [],
      assessments: [
        {
          supplier_id: "S001",
          p_link: 0.81,
          p_candidate: 0.1,
          p_identity: 0.02,
          p_exposure: 0.81,
          association_status: "review",
          geography_version: "geo-1.0.0",
          p_risk: 0.8,
          p_urgent: 0.1,
          is_risk: "Y",
          urgent: "N",
          priority: 50,
          review_reasons: ["association_support_insufficient"],
          needs_review: true,
          evidence_ids: [],
        },
      ],
      affected_supplier_ids: ["S001"],
      is_risk: "Y",
      urgent: "N",
    };
    const article = {
      id: "MOCK-GEO",
      split: "training",
      headline: "MOCK interrupción regional",
      summary: "MOCK noticia sintética",
      source: "MOCK",
      state: "review",
      published_date: "2026-10-18T00:00:00Z",
      analysis,
    };
    await page.route("**/api/**", async (r) => {
      const path = new URL(r.request().url()).pathname.replace("/api", "");
      if (path === "/demo/preview") {
        proposed = r.request().postDataJSON();
        return r.fulfill({
          json: {
            mode: "rerun",
            analysis_profile: oldServer ? "1.0.0" : proposed.analysis_profile,
            token: "MOCK-SIGNED",
            blocked: null,
            maximum_requests: 6,
            counts: {
              batches: 1,
              articles: 1,
              analyses: 1,
              incidents: 0,
              alerts: 0,
              drafts: 0,
            },
          },
        });
      }
      expect(r.request().method()).toBe("GET");
      const data: Record<string, any> = {
        "/config": { bands: [], fixtures: true },
        "/session": { presenter: true, csrf: "MOCK" },
        "/overview": {},
        "/suppliers": { items: [] },
        "/articles": [article],
        "/articles/MOCK-GEO": article,
        "/articles/MOCK-GEO/runs": [],
        "/batches": [],
        "/sources": [],
        "/alerts": { items: [], unread: 0, cursor: 0 },
        "/demo/options": [],
      };
      await r.fulfill({ json: data[path] ?? {} });
    });
    await page.goto("/noticias/MOCK-GEO");
    await expect(
      page.getByText("Candidatura inicial: 10%", { exact: false }),
    ).toBeVisible();
    await expect(
      page.getByText("Asociación final: Por confirmar", { exact: false }),
    ).toBeVisible();
    await expect(
      page.getByText("Compatibilidad de exposición: 81%", { exact: false }),
    ).toBeVisible();
    await expect(
      page.getByText(
        "no confirma afectación individual ni embarques de Helixa",
        { exact: false },
      ),
    ).toBeVisible();
    await page
      .getByText("Revisión por campo y relevancia", { exact: true })
      .click();
    await expect(
      page.getByText("Observación auxiliar · no bloquea la decisión", {
        exact: false,
      }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Reanalizar noticia", exact: true })
      .click();
    const select = page.getByLabel("Perfil del ejercicio", { exact: true });
    await expect(select).toHaveValue("1.0.0");
    await select.selectOption("link-2.2.0");
    await select.focus();
    await expect(select).toBeFocused();
    await page
      .getByRole("button", { name: "Revisar alcance", exact: true })
      .click();
    await expect(
      page.getByText("El servidor no confirmó el perfil elegido.", {
        exact: false,
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Encolar nuevo análisis", exact: true }),
    ).toBeDisabled();
    oldServer = false;
    await page
      .getByRole("button", { name: "Revisar alcance", exact: true })
      .click();
    expect(proposed.analysis_profile).toBe("link-2.2.0");
    expect(proposed.selection).toEqual(["article:MOCK-GEO"]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect(errors).toEqual([]);
    if ([360, 1440].includes(width))
      await page.screenshot({
        path: `../reports/link-profile-mock-${width}.png`,
        fullPage: true,
      });
  });
}
