import { test, expect } from "@playwright/test";
for (const width of [360, 390, 768, 1440])
  test(`Candidata RSS explícita conserva historial y foco ${width}px · MOCK`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 940 });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    let generation = 0,
      state = "review",
      polls = 0;
    const posts: string[] = [];
    const result = (candidate = false) => ({
      analysis_profile: candidate ? "radar-1.0.0-candidate" : "1.0.0",
      question_version: candidate ? "decision-3.4.2" : "rss-2.2.0",
      analysis_versions: candidate ? { matching: "link-3.3.0", review: "review-1.3.1" } : {},
      analysis_status: "review",
      event_type: "logistics_disruption",
      is_risk: "Y",
      urgent: "N",
      affected_supplier_ids: ["S032"],
      review_reasons: ["association_support_insufficient:S032"],
      review_details: [
        {
          code: "association_support_insufficient",
          field: "final_link",
          supplier_id: "S032",
          relevance: "association",
          requires_review: true,
          value: 0.55,
          threshold: 0.65,
          resolution_hint:
            "Confirma la ruta declarada y las entregas afectadas.",
        },
      ],
      evidence: [
        {
          id: "e1",
          field: "headline",
          start: 0,
          end: 18,
          text: "MOCK ocean delay.",
        },
      ],
      assessments: [
        {
          supplier_id: "S032",
          p_link: 0.55,
          p_identity: 0.05,
          p_exposure: 0.55,
          p_risk: 0.9,
          p_urgent: 0.1,
          is_risk: "Y",
          urgent: "N",
          priority: 35,
          priority_band: "medium",
          severity: 5,
          impact_status: "active",
          needs_review: true,
          review_reasons: ["association_support_insufficient"],
          evidence_ids: ["e1"],
          factor_values: {},
          policy_version: "1.0.0",
          exposure_kind: "potential",
          requires_pathway_confirmation: true,
        },
      ],
    });
    const article = () => ({
      id: "MOCK-CANDIDATE",
      generation,
      version: 1,
      headline: "MOCK ocean delay.",
      summary: "MOCK source with uncertain operational scope.",
      source: "MOCK RSS",
      split: "rss",
      state,
      published_date: "2026-10-18",
      analysis: state === "pending" ? null : result(generation > 0),
    });
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname.slice(4);
      if (route.request().method() === "POST") {
        posts.push(path);
        expect(path).toBe("/articles/MOCK-CANDIDATE/analyze");
        expect(route.request().postDataJSON()).toEqual({
          analysis_profile: "radar-1.0.0-candidate",
        });
        generation = 1;
        state = "pending";
        return route.fulfill({ status: 202, json: { job_ids: ["MOCK-JOB"] } });
      }
      if (path === "/jobs/MOCK-JOB") {
        polls++;
        if (polls > 1) state = "review";
        return route.fulfill({
          json: { id: "MOCK-JOB", state: polls > 1 ? "done" : "running" },
        });
      }
      const data: any = {
        "/session": { presenter: true, csrf: "MOCK" },
        "/config": { bands: [], cooldown_seconds: 30 },
        "/overview": {},
        "/sources": [],
        "/suppliers": { items: [] },
        "/batches": [],
        "/alerts": { items: [], unread: 0, cursor: 0 },
        "/articles": [article()],
        "/articles/MOCK-CANDIDATE": article(),
        "/articles/MOCK-CANDIDATE/drafts": [],
        "/articles/MOCK-CANDIDATE/runs": [
          { generation: 0, created_at: "2026-10-18", result: result() },
          ...(generation > 0 && state === "review"
            ? [
                {
                  generation: 1,
                  created_at: "2026-10-18",
                  result: result(true),
                },
              ]
            : []),
        ],
      };
      return route.fulfill({ json: data[path] ?? {} });
    });
    await page.goto("/noticias/MOCK-CANDIDATE?context=rss");
    const history = page
      .locator("details")
      .filter({
        has: page
          .locator("summary")
          .filter({ hasText: "Historial de análisis" }),
      })
      .first();
    await history.locator(":scope > summary").click();
    await page
      .getByRole("combobox", { name: "Perfil de análisis RSS", exact: true })
      .selectOption("radar-1.0.0-candidate");
    const button = page.getByRole("button", {
      name: "Reanalizar con este perfil",
      exact: true,
    });
    await expect(button).toBeDisabled();
    await page
      .getByLabel("Confirmo una nueva ejecución.", { exact: false })
      .check();
    await button.click();
    await expect(
      page.getByText("JEV está analizando esta noticia", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("Trabajo completado · resultado actualizado", {
        exact: true,
      }),
    ).toBeVisible({ timeout: 12000 });
    await expect(
      page.getByText("Trabajo completado · resultado actualizado", {
        exact: true,
      }),
    ).toBeFocused();
    await expect(history.getByText("Análisis 2", { exact: false })).toBeVisible(
      { timeout: 12000 },
    );
    await page
      .getByText("Revisión por campo y relevancia", { exact: true })
      .click();
    await expect(
      page
        .getByRole("region", { name: "Qué confirmar antes de decidir" })
        .getByText("Confirma la ruta declarada y las entregas afectadas.", {
          exact: true,
        }),
    ).toBeVisible();
    await expect(
      page.getByText("Exposición potencial · confirmar entregas", {
        exact: true,
      }),
    ).toBeVisible();
    const select = page.getByRole("combobox", {
      name: "Perfil de análisis RSS",
      exact: true,
    });
    await select.focus();
    await page.waitForTimeout(3300);
    await expect(select).toBeFocused();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect(posts).toEqual(["/articles/MOCK-CANDIDATE/analyze"]);
    expect(errors).toEqual([]);
    await page.screenshot({
      path: `../reports/window-candidate-mock-${width}.png`,
      fullPage: true,
    });
  });
