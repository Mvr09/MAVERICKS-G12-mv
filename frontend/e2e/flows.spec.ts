import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import ts from "typescript";

// Auth is read into this test process only; never bundled or printed.
function adminPassword() {
  const env = readFileSync("../.env", "utf8");
  const line = env.split(/\r?\n/).find((x) => /^ADMIN_PASSWORD\s*=/.test(x));
  if (!line) throw new Error("ADMIN_PASSWORD faltante");
  return line
    .slice(line.indexOf("=") + 1)
    .trim()
    .replace(/^(["'])(.*)\1$/, "$2");
}
test("flujo de presentador con mocks identificados: carga, borrador y exportación", async ({
  page,
  context,
}) => {
  test.skip(
    !process.env.E2E_FULL,
    "Requiere base dedicada radar_test y servidor de mocks identificado",
  );
  await page.goto("/");
  await expect(
    page.getByText("Demostración de interfaz · MOCKS IDENTIFICADOS.", {
      exact: false,
    }),
  ).toBeVisible();
  const session = await context.request.post("/api/session", {
    data: { password: adminPassword() },
  });
  expect(session.status()).toBe(200);
  await page.reload();
  await page
    .getByRole("link", { name: /Sunrise BioChem Ltd/ })
    .first()
    .click();
  await expect(
    page
      .getByText("MOCK IDENTIFICADO: interrupción sintética", { exact: false })
      .first(),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Consultar alternativo", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  const text = page.getByLabel("Texto de la consulta");
  await expect(text).toHaveValue(/no constituye un pedido/);
  await text.fill((await text.inputValue()) + "\nNota de ensayo sintético.");
  await page.getByRole("button", { name: "Guardar", exact: true }).click();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Descargar TXT" }).click();
  expect((await downloadPromise).suggestedFilename()).toBe(
    "consulta-proveedor.txt",
  );
  await page.getByRole("button", { name: "Copiar", exact: true }).click();
  await page.keyboard.press("Escape");
  await page
    .getByRole("link", { name: "Resumen", exact: true })
    .first()
    .click();
  const exportPromise = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Exportar", exact: true })
    .filter({ visible: true })
    .last()
    .click();
  expect((await exportPromise).suggestedFilename()).toBe(
    "supplier-risk-resultados.xlsx",
  );
  await page
    .getByLabel("Archivo Excel")
    .setInputFiles("../.runtime/e2e-upload.xlsx");
  await expect(page.getByRole("status")).toContainText("Archivo importado");
  await page.goto("/noticias");
  await expect(
    page.getByRole("link", { name: "Noticia sintética de carga" }),
  ).toBeVisible();
});

test("audio: gesto, historial, una emisión, cooldown, foco, mute y bloqueo", async ({
  page,
}) => {
  let cursor = 1;
  const item = (id: number) => ({
    id,
    incident_id: "synthetic",
    revision: 1,
    acknowledged: false,
    supplier_id: "S001",
    supplier_name: "MOCK AUDIO",
    priority: 90,
    headline: "MOCK IDENTIFICADO",
    needs_review: false,
    sound_eligible: true,
    created_at: new Date().toISOString(),
    state: "active",
  });
  await page.addInitScript(() => {
    (window as any).__tones = 0;
    const original = AudioContext.prototype.createOscillator;
    AudioContext.prototype.createOscillator = function () {
      (window as any).__tones++;
      return original.call(this);
    };
  });
  await page.route("**/api/alerts?*", (r) =>
    r.fulfill({
      json: {
        items: Array.from({ length: cursor }, (_, i) => item(i + 1)),
        cursor,
        unread: cursor,
      },
    }),
  );
  await page.goto("/");
  await expect(page).toHaveTitle(/\(1\)/);
  expect(await page.evaluate(() => (window as any).__tones)).toBe(0);
  await page
    .getByRole("button", { name: "Activar sonido", exact: true })
    .last()
    .click();
  await page
    .getByRole("button", { name: "Probar alarma", exact: true })
    .click();
  expect(await page.evaluate(() => (window as any).__tones)).toBe(1);
  cursor = 2;
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  await expect.poll(() => page.evaluate(() => (window as any).__tones)).toBe(2);
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  expect(await page.evaluate(() => (window as any).__tones)).toBe(2);
  cursor = 3;
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  await expect(page).toHaveTitle(/\(3\)/);
  expect(await page.evaluate(() => (window as any).__tones)).toBe(2);
  await page.clock.install();
  await page.clock.fastForward(31000);
  cursor = 4;
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  await expect.poll(() => page.evaluate(() => (window as any).__tones)).toBe(3);
  await page.getByRole("button", { name: "Silenciar", exact: true }).click();
  cursor = 5;
  await page.clock.fastForward(31000);
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  await expect(page).toHaveTitle(/\(5\)/);
  expect(await page.evaluate(() => (window as any).__tones)).toBe(3);
  // Browser logic only. This does not establish physical audibility.
});

test("estado visible cuando el navegador bloquea audio", async ({ page }) => {
  await page.addInitScript(() => {
    AudioContext.prototype.resume = () =>
      Promise.reject(new Error("MOCK browser blocked audio"));
  });
  await page.goto("/");
  await page
    .getByRole("button", { name: "Activar sonido", exact: true })
    .last()
    .click();
  await expect(page.getByText("Bloqueado", { exact: true })).toBeVisible();
});
