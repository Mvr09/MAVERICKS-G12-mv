import { test, expect } from "@playwright/test";

for (const width of [360, 390, 768, 1440]) {
  test(`Diagnóstico privado, trazado y actualización a ${width}px (mocks identificados)`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    const binary = {
      n: 1,
      tp: 0,
      tn: 0,
      fp: 0,
      fn: 1,
      positives: 1,
      precision: null,
      recall: 0,
      f1: 0,
    };
    const metrics = {
      n: 1,
      risk: binary,
      urgent: binary,
      suppliers: { ...binary, exact: 0, exact_set_accuracy: 0 },
      review_count: 1,
      review_rate: 1,
      automatic_coverage: 0,
      automatic: null,
      under_review: null,
    };
    const data = {
      evaluations: [
        {
          id: "MOCK-BATCH",
          split: "validation",
          label: "MOCK.xlsx",
          count: 1,
          metrics,
        },
      ],
      execution: {
        requests: 1,
        retries: 0,
        failed_requests: 0,
        cache_hits: 0,
        jobs: {},
        http_latency: {},
        analysis_latency: {},
        usage: {},
        calls_with_token_usage: 0,
        http_statuses: [],
        consistency: { articles: 0 },
        versions: [],
      },
    };
    let calls = 0;
    await page.route("**/api/session", (r) =>
      r.fulfill({ json: { presenter: true, csrf: "MOCK" } }),
    );
    await page.route("**/api/model/metrics?**", (r) =>
      r.fulfill({ json: data }),
    );
    await page.route("**/api/model/diagnostics/MOCK-BATCH", (r) => {
      expect(r.request().method()).toBe("GET");
      calls++;
      return r.fulfill({
        json: {
          filename: "MOCK.xlsx",
          split: "validation",
          created_at: new Date().toISOString(),
          thresholds: {
            link: 0.5,
            risk: 0.5,
            urgent: 0.5,
            review_low: 0.35,
            review_high: 0.65,
            choice_score_confidence: 0.6,
          },
          summary: {
            risk_false_negatives: 1,
            missing_supplier_associations: 1,
            reviewed_news: 1,
          },
          rows: [
            {
              article_id: "MOCK-A",
              news_id: "MOCK-001",
              headline: "MOCK evento sintético",
              reference: {
                is_risk: "Y",
                urgent: "N",
                affected_supplier_ids: ["S001"],
                explanation: "MOCK referencia privada",
              },
              prediction: {
                is_risk: "N",
                urgent: "N",
                affected_supplier_ids: [],
                analysis_status: "review",
              },
              risk_false_negative: true,
              missing_suppliers: ["S001"],
              extra_suppliers: [],
              supplier_gates: [
                {
                  supplier_id: "S001",
                  p_link: 0.42,
                  p_risk: 0.98,
                  p_urgent: 0.02,
                  stage_b_evaluated: true,
                  gate: "below_link_threshold",
                },
              ],
              review: {
                root_scopes: ["discarded_candidate"],
                decision_gates: [
                  {
                    supplier_id: "S001",
                    field: "p_link",
                    value: 0.42,
                    scope: "discarded_candidate",
                    rule: "review_low <= value <= review_high",
                  },
                ],
                raw_available: true,
                causes: [
                  {
                    code: "link_ambiguous:S001",
                    supplier_id: "S001",
                    scope: "discarded_candidate",
                    details: { p_link: 0.42 },
                  },
                  {
                    code: "decision_ambiguous_or_contradictory",
                    supplier_id: "S002",
                    scope: "inherited",
                    details: {
                      direct_causes: [],
                      inherited_from: ["link_ambiguous:S001"],
                    },
                  },
                ],
              },
            },
          ],
        },
      });
    });
    await page.goto("/modelo");
    await page
      .getByText("Diagnóstico por noticia · acceso de presentador", {
        exact: true,
      })
      .click();
    await expect(
      page.getByText("1 omisiones de riesgo", { exact: false }),
    ).toBeVisible();
    await expect(
      page.getByText("Validación ya inspeccionada.", { exact: false }),
    ).toBeVisible();
    await page
      .getByText("Puertas de decisión que también generan revisión", {
        exact: true,
      })
      .click();
    await expect(
      page.getByText("Valores que activan la regla", { exact: false }),
    ).toBeVisible();
    await page
      .getByText("Motivos exactos de revisión (2)", { exact: true })
      .click();
    await expect(
      page.getByText("Revisión heredada", { exact: false }),
    ).toBeVisible();
    await expect(
      page.getByText('"p_link": 0.42', { exact: false }),
    ).toBeVisible();
    await expect.poll(() => calls, { timeout: 8000 }).toBeGreaterThan(1);
    const downloaded = page.waitForEvent("download");
    await page
      .getByRole("button", { name: "Descargar diagnóstico privado" })
      .click();
    expect((await downloaded).suggestedFilename()).toBe(
      "diagnostico-privado-validation.json",
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });
}
