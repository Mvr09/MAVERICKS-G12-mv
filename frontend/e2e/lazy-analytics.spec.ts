import { test, expect } from "@playwright/test";
for (const width of [390, 1440])
  test(`Gráficos se descargan solo al abrir Analítica ${width}px · MOCK`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 940 });
    const chartRequests: string[] = [];
    page.on("request", (r) => {
      if (/\/assets\/charts-.*\.js/.test(r.url())) chartRequests.push(r.url());
    });
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname.slice(4);
      const data: any = {
        "/session": { presenter: false },
        "/config": { bands: [] },
        "/overview": {},
        "/sources": [
          {
            id: "MOCK-SOURCE",
            name: "MOCK RSS",
            received_count: 3,
            duplicates: 0,
            status: "ok",
          },
        ],
        "/suppliers": { items: [] },
        "/articles": [],
        "/alerts": { items: [], unread: 0, cursor: 0 },
        "/batches": [],
      };
      await route.fulfill({ json: data[path] ?? {} });
    });
    await page.goto("/noticias?context=rss");
    await page
      .getByRole("textbox", { name: "Buscar noticias", exact: true })
      .waitFor();
    expect(chartRequests).toEqual([]);
    await page.goto("/analitica?context=rss");
    await expect(page.locator(".recharts-wrapper")).toBeVisible();
    expect(chartRequests).toHaveLength(1);
    await expect(
      page.getByText("MOCK RSS: 3 recibidas, 0 duplicadas", { exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });

test("Un gráfico que no carga no rompe los recuentos · MOCK", async ({
  page,
}) => {
  await page.route(/\/assets\/charts-.*\.js$/, (route) => route.abort());
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname.slice(4);
    const data: any = {
      "/session": { presenter: false },
      "/config": { bands: [] },
      "/overview": {},
      "/sources": [
        {
          id: "MOCK",
          name: "MOCK RSS",
          received_count: 3,
          duplicates: 0,
          status: "ok",
        },
      ],
      "/suppliers": { items: [] },
      "/articles": [],
      "/alerts": { items: [], unread: 0, cursor: 0 },
      "/batches": [],
    };
    await route.fulfill({ json: data[path] ?? {} });
  });
  await page.goto("/analitica?context=rss");
  await expect(
    page.getByText(
      "No se pudo cargar el gráfico. Los recuentos por fuente siguen disponibles debajo.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    page.getByText("MOCK RSS: 3 recibidas, 0 duplicadas", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Recargar esta vista", exact: true }),
  ).toBeVisible();
});
