import { useEffect, useState } from "react";
import { api } from "./api";
import type { Article } from "./types";

/** A direct, bounded action: only pending inputs; never resets or supersedes results. */
export function PendingAnalysis({
  articles,
  presenter,
  single = false,
}: {
  articles: Article[];
  presenter: boolean;
  single?: boolean;
}) {
  const [busy, setBusy] = useState(false),
    [jobs, setJobs] = useState<Record<string, any>>({}),
    [errors, setErrors] = useState<string[]>([]);
  useEffect(() => {
    const queued = (event: Event) => {
      const d = (event as CustomEvent).detail;
      if (articles.some((a) => a.id === d?.article_id))
        setJobs((old) => ({
          ...old,
          [d.article_id]: { id: d.job_id, state: "queued" },
        }));
    };
    window.addEventListener("radar:analysis-queued", queued);
    return () => window.removeEventListener("radar:analysis-queued", queued);
  }, [articles]);
  const active = Object.entries(jobs).filter(([, j]) =>
    ["queued", "running"].includes(j.state),
  );
  const activeKey = active.map(([id, j]) => id + ":" + j.id).join("|");
  useEffect(() => {
    if (!active.length) return;
    let alive = true,
      inFlight = false;
    const update = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const values = await Promise.all(
          active.map(
            async ([aid, j]) => [aid, await api("/jobs/" + j.id)] as const,
          ),
        );
        if (alive)
          setJobs((old) => ({ ...old, ...Object.fromEntries(values) }));
      } catch {
        if (alive)
          setErrors([
            "No se pudo actualizar el progreso. El trabajo se conserva; vuelve a consultar.",
          ]);
      } finally {
        inFlight = false;
      }
    };
    void update();
    const timer = window.setInterval(update, 2000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [activeKey]);
  const pending = articles.filter((a) => a.state === "pending");
  if (!pending.length && !active.length) return null;
  const available = pending.filter(
    (a) =>
      !["queued", "running"].includes((jobs[a.id] || a.analysis_job)?.state),
  );
  const chosen = available.slice(0, single ? 1 : 10);
  const running =
    active.length ||
    pending.filter((a) =>
      ["queued", "running"].includes(a.analysis_job?.state || ""),
    ).length;
  return (
    <div className={"pending-analysis" + (single ? " compact" : "")}>
      <button
        className="button primary"
        disabled={!presenter || busy || !chosen.length}
        title={
          !presenter
            ? "Acceso de presentador necesario"
            : "Analiza solo pendientes con el perfil predeterminado; conserva resultados anteriores"
        }
        onClick={async () => {
          setBusy(true);
          setErrors([]);
          const failures: string[] = [];
          for (const item of chosen) {
            try {
              // Another view or presenter may already have queued this item.
              const current = await api("/articles/" + item.id);
              if (current.state !== "pending") continue;
              let id = current.analysis_job?.id;
              if (
                !id ||
                !["queued", "running"].includes(current.analysis_job.state)
              ) {
                const r = await api("/articles/" + item.id + "/analyze", {
                  method: "POST",
                  body: JSON.stringify({ analysis_profile: "1.0.0" }),
                });
                id = r.job_ids[0];
              }
              window.dispatchEvent(
                new CustomEvent("radar:analysis-queued", {
                  detail: { article_id: item.id, job_id: id },
                }),
              );
            } catch (e) {
              failures.push(item.headline + ": " + (e as Error).message);
            }
          }
          setErrors(failures);
          setBusy(false);
        }}
      >
        {busy
          ? "Encolando…"
          : running && !chosen.length
            ? "Analizando…"
            : single
              ? "Analizar"
              : `Analizar pendientes (${chosen.length}${available.length > chosen.length ? " de " + available.length : ""})`}
      </button>
      {!single && (
        <small>
          Solo pendientes de esta vista · hasta 10 · perfil predeterminado.
          Otros perfiles en la ficha o selección manual.
        </small>
      )}
      {!presenter && (
        <small>Inicia sesión como presentador para analizar.</small>
      )}
      {!!Object.keys(jobs).length && (
        <small role="status" aria-live="polite">
          {Object.values(jobs).filter((j) => j.state === "done").length}{" "}
          completados · {active.length} en cola o analizando ·{" "}
          {Object.values(jobs).filter((j) => j.state === "error").length}{" "}
          errores
        </small>
      )}
      {errors.length > 0 && (
        <div role="alert">
          {errors.map((error, i) => (
            <p key={i}>{error}</p>
          ))}
        </div>
      )}
      {Object.values(jobs).some((j) => j.state === "error") && (
        <p role="alert">
          Un análisis falló. Abre su noticia para diagnosticarlo; no se
          considera «sin riesgo».
        </p>
      )}
    </div>
  );
}
