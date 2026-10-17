import { test, expect } from "@playwright/test";

for (const width of [360, 1440]) {
  test(`materiales: listado, búsqueda, especificaciones y proveedor a ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/materiales");
    await expect(
      page.getByRole("heading", { name: "Catálogo de materiales" }),
    ).toBeVisible();
    await expect(
      page.getByText("20 materiales", { exact: true }),
    ).toBeVisible();
    await page.screenshot({path:`../reports/materials-${width}.png`,fullPage:true});
    const card = page.locator(".materials-grid article").first();
    const id = (await card.locator(".eyebrow").textContent())!.split(" · ")[0];
    await page.getByRole("searchbox", { name: "Buscar material" }).fill(id);
    await expect(page.locator(".materials-grid article")).toHaveCount(1);
    await page.getByRole("link", { name: "Ver especificaciones" }).click();
    await expect(
      page.getByRole("heading", { name: "Datos del material" }),
    ).toBeVisible();
    await expect(
      page.getByText("Necesidad mensual", { exact: true }),
    ).toBeVisible();
    const principal = page.locator(".fact-box").filter({
      has: page.getByRole("heading", { name: "Proveedor principal" }),
    });
    await principal.getByRole("link").click();
    await expect(page).toHaveURL(/\/proveedores\//);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });
}

test("RSS: feedback inmediato, worker desconectado y llegada de noticias con mocks identificados", async ({
  page,
}) => {
  let requested = false;
  const timestamp = new Date().toISOString();
  const ids = [
    "biopharma_dive",
    "supply_chain_dive",
    "the_loadstar",
    "gdacs",
    "ema",
    "el_pais",
  ];
  await page.route("**/api/session", (r) =>
    r.fulfill({ json: { presenter: true, csrf: "MOCK-CSRF" } }),
  );
  await page.route("**/api/worker", (r) =>
    r.fulfill({
      json: { online: requested, last_seen_at: requested ? timestamp : null },
    }),
  );
  await page.route("**/api/analysis/budget", (r) =>
    r.fulfill({ json: { remaining: 0, reserved: 0, network_requests: 0 } }),
  );
  await page.route("**/api/sources", (r) =>
    r.fulfill({
      json: ids.map((id) => ({
        id,
        name: id,
        status: requested ? "ok" : "pending",
        job_state: requested ? "done" : null,
        last_attempt_at: requested ? timestamp : null,
        last_success_at: requested ? timestamp : null,
        http_status: requested ? 200 : null,
        item_count: requested ? 1 : 0,
        received_count: requested ? 1 : 0,
        duplicates: 0,
        error: null,
      })),
    }),
  );
  await page.route("**/api/articles?context=rss", (r) =>
    r.fulfill({
      json: requested
        ? [
            {
              id: "MOCK-RSS",
              headline: "MOCK IDENTIFICADO: noticia recibida",
              summary: "Ensayo de feedback RSS",
              source: "MOCK RSS",
              published_date: timestamp,
              fetched_at: timestamp,
              state: "pending",
              analysis: null,
              version: 1,
              cached: false,
            },
          ]
        : [],
    }),
  );
  await page.route("**/api/sources/sync", async (r) => {
    requested = true;
    await r.fulfill({
      status: 202,
      json: { job_ids: ids, worker: { online: true, last_seen_at: timestamp } },
    });
  });
  await page.goto("/fuentes");
  await expect(
    page.getByText("Procesamiento sin conexión.", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Actualizar ahora", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "6 consultas registradas",
  );
  await expect(
    page.getByRole("link", { name: "MOCK IDENTIFICADO: noticia recibida" }),
  ).toBeVisible();
  await expect(
    page.getByText("1 noticias recibidas", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Procesamiento sin conexión.", { exact: false }),
  ).toHaveCount(0);
});

test("limpieza: vista previa, confirmación explícita y cancelar no borra datos", async ({
  page,
}) => {
  let deletes = 0;
  await page.route("**/api/session", (r) =>
    r.fulfill({ json: { presenter: true, csrf: "MOCK-CSRF" } }),
  );
  await page.route("**/api/demo/cleanup-preview", (r) =>
    r.fulfill({
      json: {
        counts: {
          batches: 2,
          articles: 44,
          analyses: 0,
          incidents: 0,
          alerts: 0,
          drafts: 0,
        },
        blocked: null,
        token: "MOCK",
      },
    }),
  );
  await page.route("**/api/demo/cleanup", (r) => {
    deletes++;
    return r.fulfill({ json: { deleted: {} } });
  });
  await page.goto("/");
  await page
    .getByRole("button", { name: "Preparar demo", exact: true })
    .click();
  await expect(
    page.getByText("2 lotes · 44 noticias · 0 análisis", { exact: true }),
  ).toBeVisible();
  const confirm = page.getByRole("button", {
    name: "Eliminar Entrenamiento y LiveDay",
    exact: true,
  });
  await expect(confirm).toBeDisabled();
  await page
    .getByLabel("Escribe LIMPIAR DEMO para confirmar")
    .fill("LIMPIAR DEMO");
  await expect(confirm).toBeEnabled();
  await page.getByRole("button", { name: "Cancelar", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(deletes).toBe(0);
});
