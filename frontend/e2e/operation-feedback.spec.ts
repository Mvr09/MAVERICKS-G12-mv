import { test, expect } from "@playwright/test";
test("Descarga: progreso real, fallo de red y recuperación sin falso éxito · MOCK", async ({
  page,
}) => {
  let requests = 0,
    fail = true,
    release: () => void = () => {};
  let hold = new Promise<void>((r) => (release = r));
  await page.route("**/api/**", async (route) => {
    const p = new URL(route.request().url()).pathname.slice(4);
    if (p === "/batches/MOCK/export.xlsx") {
      requests++;
      await hold;
      if (fail) return route.abort("failed");
      return route.fulfill({
        body: Buffer.from("MOCK archivo"),
        contentType:
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
    }
    const data: any = {
      "/session": { presenter: true, csrf: "MOCK" },
      "/config": { bands: [] },
      "/overview": {},
      "/suppliers": { items: [] },
      "/articles": [],
      "/sources": [],
      "/alerts": { items: [], unread: 0, cursor: 0 },
      "/batches": [
        {
          id: "MOCK",
          split: "training",
          filename: "MOCK.xlsx",
          count: 1,
          done: 1,
          pending: 0,
          errors: 0,
        },
      ],
    };
    await route.fulfill({ json: data[p] ?? {} });
  });
  await page.goto("/?context=exercise");
  const box = page.locator(".batch-row");
  await box.getByRole("button", { name: "Exportar", exact: true }).click();
  await expect(
    box.getByRole("button", { name: "Preparando descarga…" }),
  ).toBeDisabled();
  expect(requests).toBe(1);
  release();
  await expect(box.getByRole("alert")).toContainText("Comprueba la conexión");
  await expect(
    box.getByText("Archivo preparado.", { exact: false }),
  ).toHaveCount(0);
  fail = false;
  const download = page.waitForEvent("download");
  await box.getByRole("button", { name: "Exportar", exact: true }).click();
  await download;
  await expect(box.getByRole("status")).toContainText("Archivo preparado");
  expect(requests).toBe(2);
});
