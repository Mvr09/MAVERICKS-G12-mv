import { test, expect } from "@playwright/test";
for (const width of [360, 390, 768, 1024, 1440])
  test(`Analizar directo respeta filtros, permisos y cola ${width} · MOCK`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 940 });
    let posts: string[] = [],
      queued = false;
    let selection: any = null;
    const row = (id: string, source: string, state = "pending") => ({
      id,
      headline: "MOCK noticia " + id,
      source,
      state,
      split: "training",
      published_date: "2026-10-19",
      summary: "MOCK",
      analysis: null,
    });
    const rows = [
      row("A", "Fuente A"),
      row("B", "Fuente B"),
      row("REVIEW", "Fuente B", "review"),
    ];
    await page.route("**/api/**", async (route) => {
      const u = new URL(route.request().url()),
        p = u.pathname.slice(4);
      if (route.request().method() === "POST" && p === "/analysis/pending") {
        posts.push(p);
        const body = route.request().postDataJSON();
        expect(body.article_ids).toEqual(["B"]);
        expect(body.analysis_profile).toBe("1.0.0");
        queued = true;
        selection = {
          id: body.request_id,
          context: "exercise",
          state: "running",
          total: 1,
          finished: 0,
          counts: { done: 0, queued: 1, running: 0, error: 0, skipped: 0 },
          items: [{ article_id: "B", job_id: "MOCK-J", state: "queued" }],
        };
        return route.fulfill({ status: 202, json: selection });
      }
      if (p.startsWith("/analysis/pending/"))
        return route.fulfill({ json: selection });
      const payload: any = {
        "/session": { presenter: true, csrf: "MOCK" },
        "/config": { bands: [] },
        "/overview": {},
        "/suppliers": { items: [] },
        "/articles": rows.map((r) => ({
          ...r,
          analysis_job:
            queued && r.id === "B" ? { id: "MOCK-J", state: "queued" } : null,
        })),
        "/articles/B": {
          ...rows[1],
          analysis_job: queued ? { id: "MOCK-J", state: "queued" } : null,
        },
        "/jobs/MOCK-J": { id: "MOCK-J", state: "queued" },
        "/sources": [],
        "/batches": [],
        "/alerts": { items: [], unread: 0, cursor: 0 },
        "/worker": { online: true, compatible: true },
      };
      await route.fulfill({ json: payload[p] || {} });
    });
    await page.goto("/noticias?context=exercise");
    await page.getByLabel("Fuente", { exact: true }).selectOption("Fuente B");
    await page
      .getByRole("button", {
        name: "Analizar todas las pendientes (1)",
        exact: true,
      })
      .click();
    await expect.poll(() => posts.length).toBe(1);
    expect(posts).toEqual(["/analysis/pending"]);
    await expect(
      page
        .locator(".news-item")
        .filter({ hasText: "MOCK noticia B" })
        .getByRole("button", { name: "Analizando…", exact: true }),
    ).toBeDisabled();
    await expect(
      page
        .locator(".news-item")
        .filter({ hasText: "MOCK noticia REVIEW" })
        .getByRole("button", { name: "Analizar", exact: true }),
    ).toHaveCount(0);
    await page.reload();
    await expect(page.getByLabel("Fuente", { exact: true })).toHaveValue(
      "Fuente B",
    );
    await expect(
      page
        .locator(".news-item")
        .filter({ hasText: "MOCK noticia B" })
        .getByRole("button", { name: "Analizando…", exact: true }),
    ).toBeDisabled();
    expect(posts.length).toBe(1);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });
test("Todas las pendientes, progreso fijo y errores parciales recuperables · MOCK", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 940 });
  let phase = 0,
    selectionId = "",
    posts: any[] = [];
  const rows = Array.from({ length: 12 }, (_, i) => ({
    id: "RSS" + i,
    headline: "MOCK RSS " + i,
    source: "MOCK",
    state:
      phase === 2
        ? i === 3
          ? "error"
          : i === 0
            ? "review"
            : "done"
        : phase === 1 && i < 5
          ? "done"
          : "pending",
    split: "rss",
    published_date: "2026-10-19",
    summary: "MOCK",
  }));
  const group = () => ({
    id: selectionId,
    context: "rss",
    state: phase === 2 ? "partial" : "running",
    total: 12,
    finished: phase === 2 ? 12 : phase === 1 ? 6 : 0,
    counts:
      phase === 2
        ? { done: 11, error: 1, queued: 0, running: 0, skipped: 0 }
        : phase === 1
          ? { done: 5, error: 1, queued: 4, running: 2, skipped: 0 }
          : { done: 0, error: 0, queued: 10, running: 2, skipped: 0 },
    items: rows.map((r, i) => ({
      article_id: r.id,
      headline: r.headline,
      state: i === 3 ? "error" : "done",
      error: i === 3 ? "MOCK límite técnico: no reservado" : null,
    })),
  });
  await page.route("**/api/**", async (route) => {
    const p = new URL(route.request().url()).pathname.slice(4);
    if (route.request().method() === "POST") {
      expect(p).toBe("/analysis/pending");
      const body = route.request().postDataJSON();
      posts.push(body);
      selectionId = body.request_id;
      expect(body.article_ids).toHaveLength(12);
      return route.fulfill({ status: 202, json: group() });
    }
    if (p.startsWith("/analysis/pending/"))
      return route.fulfill({ json: group() });
    const data: any = {
      "/session": { presenter: true, csrf: "MOCK" },
      "/config": { bands: [] },
      "/overview": {},
      "/suppliers": { items: [] },
      "/articles": rows,
      "/sources": [],
      "/batches": [],
      "/alerts": { items: [], cursor: 0, unread: 0 },
    };
    await route.fulfill({ json: data[p] || {} });
  });
  await page.goto("/noticias?context=rss");
  await page
    .getByRole("button", {
      name: "Analizar todas las pendientes (12)",
      exact: true,
    })
    .click();
  const bar = page.getByRole("progressbar", {
    name: "Progreso del lote de análisis",
    exact: true,
  });
  await expect(bar).toHaveAttribute("max", "12");
  await expect(bar).toHaveAttribute("value", "0");
  phase = 1;
  await expect(bar).toHaveAttribute("value", "6", { timeout: 7000 });
  await page.setViewportSize({ width: 390, height: 940 });
  await page
    .locator(".pending-progress")
    .screenshot({ path: ".runtime/all-pending-progress-390.png" });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await expect(
    page.getByText("5 de 12 analizadas", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(bar).toHaveAttribute("max", "12");
  await expect(bar).toHaveAttribute("value", "6");
  phase = 2;
  await expect(bar).toHaveAttribute("value", "12", { timeout: 7000 });
  await expect(
    page.getByText("11 de 12 analizadas", { exact: true }),
  ).toBeVisible();
  await page.getByText("Ver 1 error", { exact: true }).click();
  await expect(
    page.getByText(/MOCK límite técnico: no reservado/),
  ).toBeVisible();
  expect(posts).toHaveLength(1);
  expect(posts[0].article_ids).toHaveLength(12);
});
test("Lectura pública muestra acción protegida sin inferencia · MOCK", async ({
  page,
}) => {
  await page.route("**/api/**", async (route) => {
    expect(route.request().method()).toBe("GET");
    const p = new URL(route.request().url()).pathname.slice(4);
    await route.fulfill({
      json:
        (
          {
            "/session": { presenter: false },
            "/config": { bands: [] },
            "/articles": [
              {
                id: "P",
                headline: "MOCK pendiente",
                state: "pending",
                split: "training",
                source: "MOCK",
                published_date: "2026-10-19",
              },
            ],
            "/suppliers": { items: [] },
            "/sources": [],
            "/batches": [],
            "/alerts": { items: [], cursor: 0, unread: 0 },
          } as any
        )[p] || {},
    });
  });
  await page.goto("/noticias");
  await expect(
    page.getByRole("button", { name: "Analizar", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByText("Inicia sesión como presentador para analizar.").first(),
  ).toBeVisible();
});
for (const state of ["pending", "done"])
  test(`Ficha Excel ${state}: análisis directo sin comando de demo · MOCK`, async ({
    page,
  }) => {
    let posted = false;
    const a = {
      id: "EXCEL-MOCK",
      headline: "MOCK noticia Excel",
      source: "MOCK",
      summary: "MOCK",
      split: "training",
      state,
      version: 1,
      generation: 0,
      published_date: "2026-10-19",
      analysis:
        state === "done"
          ? {
              analysis_status: "done",
              is_risk: "N",
              urgent: "N",
              affected_supplier_ids: [],
              assessments: [],
              evidence: [],
              review_reasons: [],
              context_notes: [],
              question_version: "1.0.0",
            }
          : null,
    };
    await page.route("**/api/**", async (route) => {
      const p = new URL(route.request().url()).pathname.slice(4);
      if (route.request().method() === "POST") {
        expect(p).toBe("/articles/EXCEL-MOCK/analyze");
        expect(route.request().postDataJSON()).toEqual({
          analysis_profile: "1.0.0",
        });
        posted = true;
        return route.fulfill({
          status: 202,
          json: { job_ids: ["MOCK-EXCEL-J"] },
        });
      }
      const data: any = {
        "/session": { presenter: true, csrf: "MOCK" },
        "/config": { bands: [] },
        "/suppliers": { items: [] },
        "/articles": [],
        "/articles/EXCEL-MOCK": a,
        "/sources": [],
        "/batches": [],
        "/alerts": { items: [], cursor: 0, unread: 0 },
        "/articles/EXCEL-MOCK/runs": [],
        "/articles/EXCEL-MOCK/drafts": [],
        "/articles/EXCEL-MOCK/review": { state: "pending", decisions: [] },
        "/jobs/MOCK-EXCEL-J": { id: "MOCK-EXCEL-J", state: "queued" },
      };
      await route.fulfill({ json: data[p] || {} });
    });
    await page.goto("/noticias/EXCEL-MOCK?context=exercise");
    const button = page.getByRole("button", {
      name:
        state === "done"
          ? "Reanalizar con este perfil"
          : "Analizar esta noticia",
      exact: true,
    });
    if (state === "done") {
      await expect(button).toBeDisabled();
      await page
        .getByText("Confirmo una nueva ejecución.", { exact: false })
        .click();
    }
    await button.click();
    await expect.poll(() => posted).toBe(true);
    await expect(
      page.getByText("En cola · esperando worker", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("textbox", { name: /confirmación/i }),
    ).toHaveCount(0);
  });
