import { test, expect } from "@playwright/test";

const binary = (tp: number, fn: number, fp = 0, tn = 5) => ({
  n: tp + fn + fp + tn,
  tp,
  fn,
  fp,
  tn,
  positives: tp + fn,
  precision: tp / (tp + fp),
  recall: tp / (tp + fn),
  f1: (2 * tp) / (2 * tp + fp + fn),
});
function report(refreshed = false) {
  const risk = binary(refreshed ? 4 : 3, refreshed ? 1 : 2);
  const urgent = binary(2, 0, 0, 8);
  const suppliers = {
    tp: 7,
    fp: 0,
    fn: 3,
    precision: 1,
    recall: 0.7,
    f1: 14 / 17,
    exact: 8,
    exact_set_accuracy: 0.8,
  };
  const m = {
    n: 10,
    risk,
    urgent,
    suppliers,
    model_id: "jev-1.13.0",
    question_version: "1.0.0",
    policy_version: "1.0.0",
    review_count: 8,
    review_rate: 0.8,
    automatic_coverage: 0.2,
    automatic: null,
    under_review: null,
  };
  return {
    updated_at: new Date().toISOString(),
    evaluations: [
      {
        id: "MOCK-VAL",
        split: "validation",
        label: "MOCK validación.xlsx",
        count: 10,
        status: "evaluated",
        metrics: m,
      },
      {
        id: "MOCK-TEST",
        split: "test",
        label: "MOCK test.xlsx",
        count: 20,
        status: "unlabelled",
        metrics: null,
        reason: "Sin etiquetas de referencia",
      },
    ],
    execution: {
      requests: refreshed ? 19 : 18,
      retries: 2,
      failed_requests: 2,
      cache_hits: 1,
      jobs: { queued: 0, running: 0 },
      http_latency: { p50: 0.4, p95: 0.9, n: 18 },
      analysis_latency: { p50: 1, p95: 2, n: 10 },
      usage: { input_tokens: 123, output_tokens: 45 },
      calls_with_token_usage: 18,
      http_statuses: [
        { status: 200, count: 16 },
        { status: 429, count: 2 },
      ],
      consistency: { articles: 0, unanimous: 0, unanimous_rate: null },
      versions: [
        { model: "jev-1.13.0", questions: "1.0.0", policy: "1.0.0", count: 10 },
      ],
      scope_note: "MOCK: peticiones de noticias conservadas",
    },
  };
}

for (const width of [360, 390, 768, 1440]) {
  test(`Modelo: calidad, actualización sin JEV y revisión a ${width}px (mocks identificados)`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    let refresh = false;
    let requests = 0;
    await page.route("**/api/session", (r) =>
      r.fulfill({ json: { presenter: true, csrf: "MOCK" } }),
    );
    await page.route("**/api/model/metrics?**", (r) => {
      expect(r.request().method()).toBe("GET");
      requests++;
      return r.fulfill({ json: report(refresh) });
    });
    await page.goto("/");
    if (width <= 640) {
      await page.getByRole("button", { name: "Más", exact: true }).click();
    }
    await page
      .getByRole("link", { name: "Modelo", exact: true })
      .filter({ visible: true })
      .click();
    await expect(
      page.getByRole("heading", {
        name: "Calidad con etiquetas de referencia",
      }),
    ).toBeVisible();
    await expect(page.getByText("0,75", { exact: true }).first()).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Matriz de riesgo", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("8/10 noticias en revisión", { exact: false }),
    ).toBeVisible();
    await expect(
      page.getByText("no mide precisión", { exact: false }),
    ).toBeVisible();
    await page.getByLabel("Lote de evaluación").selectOption("MOCK-TEST");
    await expect(
      page.getByText("Sin etiquetas de referencia", { exact: false }).first(),
    ).toBeVisible();
    await expect(page.getByText("0,75", { exact: true })).toHaveCount(0);
    await page.getByLabel("Lote de evaluación").selectOption("MOCK-VAL");
    refresh = true;
    await expect(page.getByText("0,889", { exact: true }).first()).toBeVisible({
      timeout: 8000,
    });
    expect(requests).toBeGreaterThan(1);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.getByLabel("Lote de evaluación").focus();
    await expect(page.getByLabel("Lote de evaluación")).toBeFocused();
    if ([360, 1440].includes(width))
      await page.screenshot({
        path: `../reports/model-mock-${width}.png`,
        fullPage: true,
      });
  });
}

test("Modelo privado y Analítica sin telemetría JEV (mocks identificados)", async ({
  page,
}) => {
  await page.route("**/api/session", (r) =>
    r.fulfill({ json: { presenter: false } }),
  );
  let calls = 0;
  await page.route("**/api/model/metrics?**", (r) => {
    calls++;
    return r.fulfill({ status: 401, json: { message: "Privado" } });
  });
  await page.goto("/modelo");
  await expect(
    page.getByRole("heading", { name: "Acceso de presentador" }),
  ).toBeVisible();
  expect(calls).toBe(0);
  await page.goto("/analitica");
  await expect(
    page.getByRole("heading", { name: "Motivos de revisión" }),
  ).toBeVisible();
  await expect(page.getByText("Latencia p50:", { exact: false })).toHaveCount(
    0,
  );
  await expect(
    page.getByText("Cobertura automática", { exact: true }),
  ).toBeVisible();
});

test("Incendio forestal muestra categoría y confianza independientes (mock identificado)", async ({
  page,
}) => {
  await page.route("**/api/session", (r) =>
    r.fulfill({ json: { presenter: false } }),
  );
  await page.route("**/api/articles/MOCK-FIRE", (r) =>
    r.fulfill({
      json: {
        id: "MOCK-FIRE",
        headline: "MOCK Green forest fire notification",
        source: "GDACS",
        summary: "MOCK: a forest fire started.",
        split: "rss",
        state: "done",
        published_date: "2026-10-17",
        version: 1,
        analysis: {
          event_type: "natural_disaster",
          event_classification: {
            category: "wildfire",
            label_es: "Incendio forestal",
            confidence: 0.98,
            taxonomy_version: "rss-events-1.1.0",
          },
          question_version: "rss-2.1.0",
          analysis_status: "done",
          review_reasons: [],
          assessments: [],
          evidence: [],
          context_notes: [],
          model_id: "jev-1.13.0",
        },
      },
    }),
  );
  await page.goto("/noticias/MOCK-FIRE");
  await expect(
    page.getByText("Tipo de evento: Incendio forestal", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Confianza de clasificación: 98%", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Tipo de evento incierto", { exact: true }),
  ).toHaveCount(0);
});
