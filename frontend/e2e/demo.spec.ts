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
    expect(selected).toEqual({
      selection: ["rss:ema"],
      mode: "delete",
      analysis_profile: "1.0.0",
    });
    await page
      .getByRole("radio", { name: "Volver a ejecutar el análisis" })
      .check();
    await expect(
      page.getByLabel("Escribe LIMPIAR DEMO para confirmar"),
    ).toHaveCount(0);
    await page.getByRole("button", { name: "Revisar alcance" }).click();
    expect(selected).toEqual({
      selection: ["rss:ema"],
      mode: "rerun",
      analysis_profile: "1.0.0",
    });
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
      path: `../reports/demo-profile-${width}.png`,
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
  await expect(
    page
      .getByText("Sin riesgo detectado · No urgente", { exact: false })
      .first(),
  ).toBeVisible();
  await expect(page.getByText(/Riesgo [YN]|Urgencia [YN]/)).toHaveCount(0);
});

test("reanálisis actualiza el historial abierto sin recargar y usa palabras en las decisiones", async ({
  page,
}) => {
  let phase: "initial" | "pending" | "done" = "initial";
  const timestamp = new Date().toISOString();
  const original = {
    analysis_status: "done",
    is_risk: "Y",
    urgent: "N",
    affected_supplier_ids: ["S032"],
    event_type: "fire_incident",
    evidence: [],
    review_reasons: [],
    model_id: "MOCK",
    assessments: [
      {
        supplier_id: "S032",
        p_link: 0.98,
        is_risk: "Y",
        urgent: "N",
        priority: 72,
        needs_review: false,
        review_reasons: [],
        evidence_ids: [],
      },
    ],
  };
  const updated = {
    ...original,
    urgent: "Y",
    assessments: [{ ...original.assessments[0], urgent: "Y" }],
  };
  await page.route("**/api/session", (r) =>
    r.fulfill({ json: { presenter: true, csrf: "MOCK-CSRF" } }),
  );
  await page.route("**/api/articles/MOCK-AUTO", (r) =>
    r.fulfill({
      json: {
        id: "MOCK-AUTO",
        split: "training",
        headline: "MOCK reanálisis automático",
        summary: "MOCK evidencia",
        source: "MOCK",
        published_date: timestamp,
        version: 1,
        cached: false,
        generation: phase === "initial" ? 0 : 1,
        state: phase === "pending" ? "pending" : "done",
        analysis:
          phase === "pending" ? null : phase === "done" ? updated : original,
      },
    }),
  );
  await page.route("**/api/articles/MOCK-AUTO/runs", (r) =>
    r.fulfill({
      json: [
        ...(phase === "done"
          ? [{ generation: 1, created_at: timestamp, result: updated }]
          : []),
        { generation: 0, created_at: timestamp, result: original },
      ],
    }),
  );
  await page.route("**/api/demo/options", (r) => r.fulfill({ json: [] }));
  await page.route("**/api/demo/preview", (r) =>
    r.fulfill({
      json: {
        mode: "rerun",
        token: "MOCK-SIGNED",
        blocked: null,
        maximum_requests: 6,
        counts: {
          batches: 0,
          articles: 1,
          analyses: 1,
          incidents: 0,
          alerts: 0,
          drafts: 0,
        },
      },
    }),
  );
  await page.route("**/api/demo/cleanup", (r) => {
    phase = "pending";
    return r.fulfill({
      json: { deleted: { mode: "rerun", job_ids: ["MOCK-JOB"] } },
    });
  });
  await page.goto("/noticias/MOCK-AUTO");
  await expect(page.locator(".assessment")).toContainText(
    "Riesgo detectado · No urgente",
  );
  await page.getByText("Historial de análisis", { exact: true }).click();
  const history = page.locator("details.comparison-panel");
  await history.getByText(/Análisis 1 ·/).click();
  const oldEntry = history
    .locator("details")
    .filter({ has: page.getByText(/Análisis 1 ·/) });
  await expect(oldEntry).toHaveAttribute("open", "");
  await page
    .getByRole("button", { name: "Reanalizar noticia", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Revisar alcance", exact: true })
    .click();
  await page.getByLabel("Escribe REANALIZAR para confirmar").fill("REANALIZAR");
  await page
    .getByRole("button", { name: "Encolar nuevo análisis", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(
    page.getByText(
      "Análisis pendiente. No se ha emitido una decisión de riesgo.",
    ),
  ).toBeVisible();
  phase = "done";
  await expect(history.getByText(/Análisis 2 ·/)).toBeVisible({
    timeout: 10000,
  });
  await expect(oldEntry).toHaveAttribute("open", "");
  await history.getByText(/Análisis 2 ·/).click();
  await expect(history).toContainText("Riesgo detectado · Urgente");
  await expect(page.locator(".assessment")).toContainText(
    "Riesgo detectado · Urgente",
  );
  await expect(page.getByText(/Riesgo [YN]|Urgencia [YN]/)).toHaveCount(0);
});

test("RSS sin presupuesto: permite todas las pendientes aunque los contadores antiguos estén agotados", async ({
  page,
}) => {
  let requestBody: any = null;
  await page.route("**/api/session", (r) =>
    r.fulfill({ json: { presenter: true, csrf: "MOCK-CSRF" } }),
  );
  await page.route("**/api/worker", (r) =>
    r.fulfill({ json: { online: true, compatible: true } }),
  );
  await page.route("**/api/analysis/budget", (r) =>
    r.fulfill({
      json: {
        limits_enforced: false,
        unlimited: true,
        remaining: null,
        daily_remaining: null,
        daily_limit: null,
        reserved: 100,
        network_requests: 200,
        request_budgets: [
          {
            id: "MOCK-OLD",
            request_limit: 200,
            remaining_requests: 0,
            requests_used: 200,
            enforced: false,
          },
        ],
      },
    }),
  );
  await page.route("**/api/articles?context=rss", (r) =>
    r.fulfill({
      json: Array.from({ length: 12 }, (_, n) => ({
        id: `MOCK-${n}`,
        state: "pending",
        headline: `MOCK RSS ${n}`,
        summary: "MOCK",
        source: "MOCK",
        published_date: new Date().toISOString(),
        version: 1,
        analysis: null,
        cached: false,
      })),
    }),
  );
  await page.route("**/api/analysis/rss", (r) => {
    requestBody = r.request().postDataJSON();
    return r.fulfill({
      status: 202,
      json: { articles: 12, job_ids: [], maximum_requests: 72 },
    });
  });
  await page.goto("/fuentes");
  await expect(
    page.getByText("Sin límites locales de presupuesto", { exact: false }),
  ).toBeVisible();
  const button = page.getByRole("button", {
    name: "Analizar 12 noticias pendientes con JEV",
    exact: true,
  });
  await expect(button).toBeEnabled();
  await expect(
    page.getByText("0 de 200 peticiones disponibles", { exact: false }),
  ).toHaveCount(0);
  await expect(
    page.getByText(
      "El cupo agotado no se restablece al reiniciar ni desplegar.",
    ),
  ).toHaveCount(0);
  await button.click();
  expect(requestBody).toEqual({});
});
