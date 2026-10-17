import { test, expect } from "@playwright/test";

for (const width of [360, 1440]) {
  test(`demo seleccionada y reanálisis con confirmación a ${width}px (mocks identificados)`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    let selected: any = null,
      committed: any = null;
    await page.route("**/api/session", (r) =>
      r.fulfill({ json: { presenter: true, csrf: "MOCK-CSRF" } }),
    );
    await page.route("**/api/demo/options", (r) =>
      r.fulfill({
        json: [
          {
            id: "batch:MOCK",
            label: "MOCK Entrenamiento",
            kind: "exercise",
            count: 3,
          },
          { id: "rss:ema", label: "MOCK EMA", kind: "rss", count: 2 },
          { id: "catalog", label: "Catálogo", kind: "catalog", count: 40 },
        ],
      }),
    );
    await page.route("**/api/demo/preview", (r) => {
      selected = r.request().postDataJSON();
      return r.fulfill({
        json: {
          mode: selected.mode,
          token: "MOCK-SIGNED",
          blocked: null,
          maximum_requests: 12,
          counts: {
            batches: 0,
            articles: 2,
            analyses: 2,
            incidents: 0,
            alerts: 0,
            drafts: 0,
          },
        },
      });
    });
    await page.route("**/api/demo/cleanup", (r) => {
      committed = r.request().postDataJSON();
      return r.fulfill({
        json: { deleted: { mode: "rerun", job_ids: ["MOCK-JOB"] } },
      });
    });
    await page.goto("/");
    await page
      .getByRole("button", { name: "Preparar demo", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "Revisar alcance" }),
    ).toBeDisabled();
    await page.getByRole("checkbox", { name: "MOCK EMA" }).check();
    await page.getByRole("button", { name: "Revisar alcance" }).click();
    expect(selected).toEqual({ selection: ["rss:ema"], mode: "delete" });
    await page
      .getByRole("radio", { name: "Volver a ejecutar el análisis" })
      .check();
    await expect(
      page.getByLabel("Escribe LIMPIAR DEMO para confirmar"),
    ).toHaveCount(0);
    await page.getByRole("button", { name: "Revisar alcance" }).click();
    expect(selected).toEqual({ selection: ["rss:ema"], mode: "rerun" });
    await expect(
      page.getByRole("checkbox", { name: "Catálogo" }),
    ).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Encolar nuevo análisis" }),
    ).toBeDisabled();
    await page
      .getByLabel("Escribe REANALIZAR para confirmar")
      .fill("REANALIZAR");
    await expect(
      page.getByRole("button", { name: "Encolar nuevo análisis" }),
    ).toBeEnabled();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `../reports/demo-selection-${width}.png`,
      fullPage: true,
    });
    await page.getByRole("button", { name: "Encolar nuevo análisis" }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    expect(committed).toEqual({
      confirmation: "REANALIZAR",
      token: "MOCK-SIGNED",
    });
  });
}

test("contraste triple muestra desacuerdo sin retirar revisión (mocks identificados)", async ({
  page,
}) => {
  let started = false;
  await page.route("**/api/session", (r) =>
    r.fulfill({ json: { presenter: true, csrf: "MOCK-CSRF" } }),
  );
  await page.route("**/api/articles/MOCK-RSS", (r) =>
    r.fulfill({
      json: {
        id: "MOCK-RSS",
        split: "rss",
        headline: "MOCK noticia de contraste",
        summary: "MOCK evidencia",
        source: "MOCK RSS",
        published_date: new Date().toISOString(),
        state: "review",
        version: 1,
        analysis: {
          analysis_status: "review",
          review_reasons: ["event_type_confidence_low"],
          assessments: [],
          evidence: [],
          model_id: "MOCK",
        },
        cached: false,
      },
    }),
  );
  await page.route("**/api/articles/MOCK-RSS/comparisons", (r) =>
    r.fulfill({
      json: started
        ? [
            {
              id: "MOCK-COMP",
              state: "done",
              ballots: [
                {
                  analysis_status: "done",
                  is_risk: "N",
                  urgent: "N",
                  affected_supplier_ids: [],
                  review_reasons: [],
                  event_type: "not_relevant",
                },
                {
                  analysis_status: "review",
                  is_risk: "N",
                  urgent: "N",
                  affected_supplier_ids: [],
                  review_reasons: ["event_type_confidence_low"],
                  event_type: "not_relevant",
                },
                {
                  analysis_status: "review",
                  is_risk: "Y",
                  urgent: "N",
                  affected_supplier_ids: ["S001"],
                  review_reasons: ["event_state_confidence_low"],
                  event_type: "other",
                },
              ],
              summary: {
                done_votes: 1,
                review_votes: 2,
                errors: 0,
                decision_agreement: 2,
                message:
                  "La mayoría sigue sin una conclusión suficiente para retirar la revisión.",
              },
            },
          ]
        : [],
    }),
  );
  await page.route("**/api/articles/MOCK-RSS/compare", (r) => {
    started = true;
    return r.fulfill({
      status: 202,
      json: {
        comparison_id: "MOCK-COMP",
        job_id: "MOCK-JOB",
        maximum_requests: 18,
      },
    });
  });
  await page.goto("/noticias/MOCK-RSS");
  await page.getByRole("button", { name: "Contrastar con 3 JEV" }).click();
  await expect(
    page.getByText("Se harán hasta 18 peticiones JEV", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Iniciar contraste", exact: true })
    .click();
  await expect(
    page.getByText("3/3 evaluaciones terminadas", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "La mayoría sigue sin una conclusión suficiente para retirar la revisión.",
    ),
  ).toBeVisible();
  await expect(
    page.getByText(
      "El análisis vigente, su prioridad, sus alarmas y las exportaciones se conservan.",
    ),
  ).toBeVisible();
});
