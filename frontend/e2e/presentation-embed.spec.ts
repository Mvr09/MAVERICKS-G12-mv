import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
const site = "https://helixa-signal-to-action.jvaswiss-9277.chatgpt.site",
  app = "https://mavericks-g12-mv-production.up.railway.app";
test.afterEach(async ({ context }) => {
  await context.unrouteAll({ behavior: "ignoreErrors" });
});
const host = readFileSync(resolve("e2e/fixtures/embed-host.html"), "utf8");
async function routes(page: any, { hold = false, dropCookies = false } = {}) {
  let release: () => void = () => {};
  const gate = new Promise<void>((r) => (release = r));
  await page
    .context()
    .route(site + "/**", (r: any) =>
      r.fulfill({ body: host, contentType: "text/html" }),
    );
  await page.context().route(app + "/**", async (r: any) => {
    const req = r.request(),
      u = new URL(req.url());
    if (hold && u.pathname === "/api/overview") await gate;
    if (
      dropCookies &&
      u.pathname === "/api/session" &&
      req.method() === "GET" &&
      (await req.allHeaders())["x-radar-embed"] === "1"
    ) {
      await r.fulfill({ json: { presenter: false } });
      return; // Explicit simulation of unavailable third-party session.
    }
    const response = await r.fetch({
      url: "http://127.0.0.1:4188" + u.pathname + u.search,
      headers: await req.allHeaders(),
    });
    if (
      dropCookies &&
      u.pathname === "/api/session" &&
      req.method() === "POST" &&
      (await req.allHeaders())["x-radar-embed"] === "1"
    ) {
      const headers = { ...response.headers() };
      delete headers["set-cookie"];
      await r.fulfill({ response, headers });
    } else await r.fulfill({ response });
  });
  return release;
}
async function login(frame: any) {
  await frame
    .getByRole("button", { name: "Acceso presentador", exact: true })
    .click();
  await frame
    .getByLabel("Contraseña", { exact: true })
    .fill("MOCK-iframe-password");
  await frame.getByRole("button", { name: "Entrar", exact: true }).click();
}
for (const width of [390, 1440])
  test(`Sesión real, CSRF y recarga ${width}px · catálogo MOCK`, async ({
    page,
    context,
    browserName,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await routes(page);
    await page.goto(site);
    await page
      .getByRole("button", { name: "Abrir aplicación", exact: true })
      .click();
    await expect(page.getByRole("status")).toHaveText("App lista");
    const f = page.frameLocator("#app");
    await login(f);
    await expect(
      f.getByRole("button", { name: "Salir", exact: true }),
    ).toBeVisible();
    const cookies = await context.cookies(app);
    const embedded = cookies.find((c) => c.name === "radar_embed_session");
    expect(embedded).toBeTruthy();
    expect(embedded!.httpOnly).toBe(true);
    expect(embedded!.secure).toBe(true);
    expect(embedded!.sameSite).toBe("None");
    await page.reload();
    await page
      .getByRole("button", { name: "Abrir aplicación", exact: true })
      .click();
    await expect(
      f.getByRole("button", { name: "Salir", exact: true }),
    ).toBeVisible();
    const csrfResult = await f.locator("body").evaluate(async () => {
      const r = await fetch("/api/qa/audio", { method: "POST" });
      return r.status;
    });
    expect(csrfResult).toBe(403);
    expect(
      await f
        .locator("body")
        .evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    ).toBe(true);
    await f.getByRole("button", { name: "Salir", exact: true }).click();
    await expect(
      f.getByRole("button", { name: "Acceso presentador", exact: true }),
    ).toBeVisible();
    expect(errors).toEqual([]);
  });
test("load y mensajes falsos no certifican disponibilidad · MOCK", async ({
  page,
}) => {
  const release = await routes(page, { hold: true });
  await page.goto(site);
  await page
    .getByRole("button", { name: "Abrir aplicación", exact: true })
    .click();
  await expect(
    page
      .frameLocator("#app")
      .getByRole("heading", { name: "Resumen.", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("status")).toContainText("Cargando");
  await page.evaluate(() =>
    window.postMessage(
      { type: "radar:ready", version: 1, requestId: "forged-message-0000" },
      "*",
    ),
  );
  await expect(page.getByRole("status")).toContainText("Cargando");
  release();
  await expect(page.getByRole("status")).toHaveText("App lista");
});
test("Cookie bloqueada muestra recuperación y ventana independiente · MOCK de fallo", async ({
  page,
}) => {
  await routes(page, { dropCookies: true });
  await page.goto(site);
  await page
    .getByRole("button", { name: "Abrir aplicación", exact: true })
    .click();
  await expect(page.getByRole("status")).toHaveText("App lista");
  const f = page.frameLocator("#app");
  await login(f);
  await expect(
    f.getByRole("alert").filter({ hasText: "no ha conservado la sesión" }),
  ).toBeVisible();
  await expect(
    f.getByRole("button", { name: "Salir", exact: true }),
  ).toHaveCount(0);
  const popup = page.waitForEvent("popup");
  await f
    .getByRole("link", { name: "Abrir app en una ventana ↗", exact: true })
    .click();
  const separate = await popup;
  await expect(separate).toHaveURL(/railway\.app/);
  await expect(
    separate.getByRole("heading", { name: "Resumen.", exact: true }),
  ).toBeVisible();
  const recovered = await separate.evaluate(async () => (await (await fetch("/api/session")).json()).presenter);
  if (!recovered) await login(separate);
  await expect(
    separate.getByRole("button", { name: "Salir", exact: true }),
  ).toBeVisible();
});
test("Un padre no autorizado queda bloqueado por CSP real · MOCK de origen", async ({
  page,
}) => {
  await routes(page);
  await page.route("https://untrusted.example/**", (r) =>
    r.fulfill({ body: host, contentType: "text/html" }),
  );
  let violations: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error") violations.push(m.text());
  });
  await page.goto("https://untrusted.example");
  await page
    .getByRole("button", { name: "Abrir aplicación", exact: true })
    .click();
  await expect
    .poll(() =>
      violations.some((v) =>
        /frame-ancestors|framing|Content.Security.Policy/i.test(v),
      ),
    )
    .toBe(true);
  await expect(page.getByRole("status")).not.toHaveText("App lista");
});
