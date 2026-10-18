import { test, expect } from "@playwright/test";
for (const width of [360, 390, 768, 1440])
  test(`RSS a consulta verificable ${width}px · MOCK explícito`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 940 });
    let analyzed = false,
      enqueued = false,
      polls = 0,
      draft: any = null,
      posts: string[] = [];
    const supplier: any = {
      supplier_id: "S032",
      name: "MOCK marítimo",
      material: "Asia to Europe sea freight",
      category: "Logistics",
      criticality: "Medium",
      single_source: "N",
      inventory_days: null,
      lead_days: 35,
      alternate_id: "S033",
      products: [],
      materials: [],
      incidents: [],
      status: "pending",
    };
    const evidence = {
      id: "e1",
      field: "headline",
      start: 0,
      end: 18,
      text: "MOCK ocean delay.",
    };
    const article = () => ({
      id: "RSS-MOCK",
      version: 3,
      generation: 2,
      analysis_job: enqueued
        ? {
            id: "JOB-MOCK",
            state: analyzed ? "done" : "running",
            analysis_profile: "1.0.0",
          }
        : null,
      headline: evidence.text,
      summary: "MOCK explicit source.",
      source: "MOCK RSS",
      split: "rss",
      source_id: "MOCK",
      published_date: "2026-10-18",
      state: analyzed ? "review" : "pending",
      analysis: analyzed
        ? {
            question_version: "MOCK",
            analysis_status: "review",
            is_risk: "N",
            urgent: "N",
            affected_supplier_ids: [],
            assessments: [],
            evidence: [evidence],
            review_reasons: ["link_ambiguous:S032"],
            context_notes: [],
          }
        : null,
    });
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname.slice(4);
      const method = route.request().method();
      if (method === "POST") {
        posts.push(path);
        if (path === "/analysis/rss") {
          enqueued = true;
          expect(route.request().postDataJSON()).toEqual({
            limit: 1,
            article_ids: ["RSS-MOCK"],
          });
          return route.fulfill({
            json: { job_ids: ["JOB-MOCK"], articles: 1, maximum_requests: 6 },
          });
        }
        if (path === "/verification-drafts") {
          const body = route.request().postDataJSON();
          expect(body.evidence_ids).toEqual(["e1"]);
          expect(body.acknowledged).toBe(true);
          expect(body.generation).toBe(2);
          draft = {
            id: "D-MOCK",
            kind: "verification",
            supplier_id: "S032",
            text:
              "MOCK fuente literal: " +
              evidence.text +
              "\nHipótesis pendiente de confirmar.",
            evidence_snapshot: {
              generation: 2,
              version: 3,
              evidence: [evidence],
            },
          };
          return route.fulfill({ status: 201, json: draft });
        }
        throw new Error("Unexpected POST " + path);
      }
      if (path === "/jobs/JOB-MOCK") {
        polls++;
        if (polls >= 2) analyzed = true;
        return route.fulfill({
          json: { id: "JOB-MOCK", state: analyzed ? "done" : "running" },
        });
      }
      const data: any = {
        "/config": { bands: [], cooldown_seconds: 30 },
        "/session": { presenter: true, csrf: "MOCK" },
        "/suppliers": { items: [supplier] },
        "/overview": {},
        "/articles": [article()],
        "/articles/RSS-MOCK": article(),
        "/articles/RSS-MOCK/runs": [],
        "/articles/RSS-MOCK/drafts": draft
          ? [{ id: draft.id, supplier_id: "S032", kind: "verification" }]
          : [],
        "/drafts/D-MOCK": draft,
        "/sources": [],
        "/batches": [],
        "/alerts": { items: [], unread: 0, cursor: 0 },
      };
      return route.fulfill({ json: data[path] ?? {} });
    });
    await page.goto("/noticias/RSS-MOCK?context=rss");
    await page
      .getByRole("button", { name: "Analizar esta noticia", exact: true })
      .click();
    await expect(
      page.getByText("JEV está analizando esta noticia", { exact: true }),
    ).toBeVisible();
    if (width === 390) await page.reload(); // Resume the durable job, never enqueue another analysis.
    await expect(
      page.getByRole("button", {
        name: "Preparar consulta de verificación",
        exact: true,
      }),
    ).toBeEnabled({ timeout: 12000 });
    await page
      .getByRole("button", {
        name: "Preparar consulta de verificación",
        exact: true,
      })
      .click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    const box = (await dialog.boundingBox())!;
    expect(Math.abs(box.x - (width - box.width) / 2)).toBeLessThan(2);
    await page
      .getByLabel("Proveedor al que consultar", { exact: true })
      .selectOption("S032");
    await expect(
      page.getByText("Productos no mapeados", { exact: true }),
    ).toBeVisible();
    await page.getByLabel("MOCK ocean delay.", { exact: true }).check();
    await page
      .getByLabel(
        "Por qué podría ser relevante (hipótesis, no hecho confirmado)",
        { exact: true },
      )
      .fill("Confirmar si la ruta marítima declarada puede verse afectada.");
    await page
      .getByLabel(
        "He leído los fragmentos y entiendo que la exposición está pendiente de confirmar.",
        { exact: true },
      )
      .check();
    await page
      .getByRole("button", {
        name: "Crear borrador de verificación",
        exact: true,
      })
      .click();
    await expect(
      page.getByLabel("Texto editable de la consulta", { exact: true }),
    ).toContainText("Hipótesis pendiente de confirmar.");
    const event = page.waitForEvent("download");
    await page
      .getByRole("button", { name: "Descargar consulta TXT", exact: true })
      .click();
    expect((await event).suggestedFilename()).toBe("consulta-exposicion.txt");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `../reports/${process.env.SCREENSHOT_PREFIX || "rss-verification-mock"}-${width}.png`,
      fullPage: true,
    });
    await page
      .getByRole("button", { name: "Cerrar consulta", exact: true })
      .click();
    await expect(
      page.getByRole("button", {
        name: "Preparar consulta de verificación",
        exact: true,
      }),
    ).toBeFocused();
    await page.reload();
    await page.getByText("Consultas guardadas (1)", { exact: true }).click();
    await page
      .getByRole("button", { name: "Abrir consulta · S032", exact: true })
      .click();
    await expect(
      page.getByLabel("Texto editable de la consulta", { exact: true }),
    ).toContainText("MOCK fuente literal");
    expect(posts).toEqual(["/analysis/rss", "/verification-drafts"]);
  });
