import { test, expect } from "@playwright/test";
for (const width of [360, 390, 768, 1440]) {
  test(`catálogo y ficha a ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Prioridad de proveedores" }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Sunrise BioChem Ltd/ }).first(),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `../reports/ui-${width}.png`,
      fullPage: true,
    });
    await page
      .getByRole("link", { name: /Sunrise BioChem Ltd/ })
      .first()
      .click();
    await expect(
      page.getByRole("heading", { name: "Sunrise BioChem Ltd" }),
    ).toBeVisible();
    await expect(
      page.getByText("Amoxira 500 mg capsules", { exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `../reports/detail-${width}.png`,
      fullPage: true,
    });
    for (const route of [
      "/noticias",
      "/fuentes",
      "/analitica",
      "/materiales/M01",
    ]) {
      await page.goto(route);
      await expect(page.locator("main .card").first()).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
    }
  });
}
test("filtros con teclado y acceso de presentador", async ({ page }) => {
  await page.goto("/proveedores");
  await page.getByRole("button", { name: "Filtros", exact: true }).click();
  await page.getByLabel("Fuente única", { exact: true }).selectOption("Y");
  await page.getByRole("button", { name: "Aplicar", exact: true }).click();
  await expect(
    page.getByText("14 de 14 proveedores", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Acceso presentador" }).click();
  await expect(page.getByLabel("Contraseña", { exact: true })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(
    page.getByRole("button", { name: "Acceso presentador" }),
  ).toBeFocused();
});
