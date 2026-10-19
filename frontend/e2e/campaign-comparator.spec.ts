import { test, expect } from "@playwright/test";
const profiles = ["1.0.0", "radar-1.0.0-candidate"];
const metric = {
  tp: 1,
  fp: 0,
  fn: 0,
  tn: 1,
  n: 2,
  positives: 1,
  precision: 1,
  recall: 1,
  f1: 1,
};
const stats = (baseline = false) => ({
  total: 2,
  completed: 2,
  errors: 0,
  pending: 0,
  labelled_completed: 2,
  quality: {
    n: 2,
    risk: baseline
      ? { ...metric, tp: 0, fn: 1, precision: null, recall: 0, f1: 0 }
      : metric,
    urgent: {
      ...metric,
      tp: 0,
      tn: 2,
      positives: 0,
      precision: null,
      recall: null,
      f1: null,
    },
    suppliers: {
      ...metric,
      tp: baseline ? 0 : 1,
      fn: baseline ? 1 : 0,
      exact: baseline ? 1 : 2,
    },
  },
  automatic: 2,
  review: 0,
  automatic_rate: 1,
  review_rate: 0,
  automatic_errors: baseline ? 1 : 0,
  automatic_labelled: 2,
  automatic_positive: { n: 1, errors: baseline ? 1 : 0 },
  automatic_negative: { n: 1, errors: 0 },
  automatic_risks: baseline ? 0 : 1,
  automatic_urgencies: 0,
  new_requests: baseline ? 3 : 10,
  cache_stages: 0,
  retries: 0,
  http_errors: 0,
  tokens: { input_tokens: 20, output_tokens: 10 },
  analysis_wall_seconds_sum: 3,
  elapsed_seconds: 4,
});
function response(sample = "training") {
  const noLabels = ["test", "liveday"].includes(sample);
  const rows = ["MOCK-POS", "MOCK-NEG"].flatMap((id, i) =>
    profiles.map((profile, p) => ({
      id: id + profile,
      key: id,
      news_id: id,
      headline: i ? "MOCK noticia inocua" : "MOCK interrupción de proveedor",
      source: "MOCK controlled sample",
      profile,
      split: sample,
      state: "done",
      reference: noLabels
        ? null
        : {
            Is_Risk: i ? "N" : "Y",
            Urgent: "N",
            Affected_Supplier_IDs: i ? "" : "S001",
          },
      result: {
        analysis_status: "done",
        is_risk: !i && p ? "Y" : "N",
        urgent: "N",
        affected_supplier_ids: !i && p ? ["S001"] : [],
        evidence: [
          { id: "e1", field: "summary", text: "MOCK source evidence" },
        ],
        assessments:
          !i && p
            ? [{ supplier_id: "S001", priority: 42, review_reasons: [] }]
            : [],
        review_reasons: [],
      },
      supplier_added: [],
      supplier_omitted: !i && !p ? ["S001"] : [],
    })),
  );
  const aggregate = Object.fromEntries(
    profiles.map((p, i) => [
      p,
      {
        ...stats(!i),
        ...(noLabels
          ? {
              quality: null,
              labelled_completed: 0,
              quality_limit: "No disponible: sin etiquetas",
              automatic_errors: null,
              automatic_labelled: 0,
            }
          : {}),
      },
    ]),
  );
  return {
    id: "MOCK-C",
    name: "MOCK campaign",
    state: "complete",
    created_at: "2026-10-19",
    started_at: "2026-10-19",
    completed_at: "2026-10-19",
    elapsed_seconds: 4,
    freeze: {
      created_commit: "MOCK123",
      versions: {
        "1.0.0": { questions: "1.0.0" },
        "radar-1.0.0-candidate": {
          questions: "decision-3.4.2",
          review: "review-1.3.1",
        },
      },
      manifest: { MOCK: true },
      request_estimate: { max_http_attempts_including_retries: 84 },
    },
    progress: { done: 4 },
    aggregate,
    rows,
  };
}
for (const width of [360, 390, 768, 1024, 1440])
  test(`Comparador gráfico, drill-down y consulta sin JEV ${width} · MOCK`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 940 });
    let posts = 0;
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.route("**/api/**", async (route) => {
      const u = new URL(route.request().url()),
        p = u.pathname.slice(4);
      if (route.request().method() !== "GET") posts++;
      const defaults: any = {
        "/session": { presenter: true, csrf: "MOCK" },
        "/config": { bands: [] },
        "/overview": {},
        "/suppliers": { items: [] },
        "/articles": [],
        "/sources": [],
        "/batches": [],
        "/alerts": { items: [], cursor: 0, unread: 0 },
        "/campaigns": [
          { id: "MOCK-C", name: "MOCK campaign", state: "complete" },
        ],
      };
      await route.fulfill({
        json:
          p === "/campaigns/MOCK-C"
            ? response(u.searchParams.get("split") || "training")
            : defaults[p] || {},
      });
    });
    await page.goto("/modelo?context=exercise");
    await expect(
      page.getByRole("heading", { name: "Dos perfiles. Las mismas noticias." }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", {
        name: "A riesgo fn: 1 noticias",
        exact: true,
      }),
    ).toBeVisible();
    // Exercise the same mounted chart across sidebar and mobile breakpoints.
    for (const resized of [width, 650, 820, 1100, 390, width]) {
      await page.setViewportSize({ width: resized, height: 940 });
      await expect
        .poll(async () =>
          page.locator(".compare-chart").evaluate((e) => {
            const svg = e.querySelector("svg.recharts-surface");
            return Boolean(
              svg &&
                svg.getBoundingClientRect().width > 0 &&
                svg.getBoundingClientRect().width <=
                  e.getBoundingClientRect().width + 1,
            );
          }),
        )
        .toBe(true);
      expect(
        await page
          .locator(".campaign-page > .card")
          .first()
          .evaluate((e) => parseFloat(getComputedStyle(e).paddingLeft)),
      ).toBeGreaterThanOrEqual(16);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
    }
    await expect(
      page.getByRole("region", { name: /Tabla de métricas/ }),
    ).toHaveAttribute("tabindex", "0");
    await page.emulateMedia({ media: "print" });
    await expect(page.locator(".sidebar")).toBeHidden();
    await expect(page.locator(".mobile-nav")).toBeHidden();
    await page.emulateMedia({ media: "screen" });
    await page
      .getByRole("button", { name: "A riesgo fn: 1 noticias", exact: true })
      .click();
    await expect(
      page.getByRole("status").filter({ hasText: "1 noticias de 2" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Evidencia y prioridad" }).click();
    await expect(
      page.getByRole("heading", {
        name: "Prioridad empresarial por unidad noticia–proveedor",
      }),
    ).toBeVisible();
    await expect(
      page.getByText("S001: A Sin estimación · B 42 · Δ No comparable"),
    ).toBeVisible();
    await page.getByRole("button", { name: /Quitar filtro FN/ }).click();
    await expect(
      page.getByRole("status").filter({ hasText: "2 noticias de 2" }),
    ).toBeVisible();
    await page.getByLabel("Muestra", { exact: true }).selectOption("test");
    await expect(
      page.getByText("No disponible: sin etiquetas", { exact: true }).first(),
    ).toBeVisible();
    await page.reload();
    await expect(page.getByLabel("Muestra", { exact: true })).toHaveValue(
      "test",
    );
    await page
      .getByRole("button", { name: "Ejecuciones", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Ejecución explícita" }),
    ).toBeVisible();
    expect(posts).toBe(0);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect(errors).toEqual([]);
  });
