import { DEFAULT_ANALYSIS_PROFILE } from "./AnalysisProfile";
import { useEffect, useState, useRef } from "react";
import { useLocation } from "react-router-dom";
import { api } from "./api";
import type { Article } from "./types";

/** A direct, bounded action: only pending inputs; never resets or supersedes results. */
function SinglePendingAnalysis({
  articles,
  presenter,
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
  const chosen = available.slice(0, 1);
  const running =
    active.length ||
    pending.filter((a) =>
      ["queued", "running"].includes(a.analysis_job?.state || ""),
    ).length;
  return (
    <div className="pending-analysis compact">
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
                  body: JSON.stringify({
                    analysis_profile: DEFAULT_ANALYSIS_PROFILE,
                  }),
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
            : "Analizar"}
      </button>
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

function BulkPendingAnalysis({
  articles,
  presenter,
}: {
  articles: Article[];
  presenter: boolean;
}) {
  const location = useLocation();
  const progressRef = useRef<HTMLDivElement>(null),
    focusAfterStart = useRef(false);
  const context = articles.length
    ? articles[0].split === "rss"
      ? "rss"
      : "exercise"
    : new URLSearchParams(location.search).get("context") === "rss"
      ? "rss"
      : "exercise";
  const storageKey = "radar:pending-selection:" + context;
  const readId = () => {
    try {
      return sessionStorage.getItem(storageKey) || "";
    } catch {
      return "";
    }
  };
  const savedRequest = useRef<any>(null);
  const [trackingVersion, setTrackingVersion] = useState(0);
  const [id, setId] = useState(readId),
    [group, setGroup] = useState<any>(null),
    [busy, setBusy] = useState(false),
    [preparingTotal, setPreparingTotal] = useState(0),
    [error, setError] = useState("");
  useEffect(() => {
    try {
      savedRequest.current = JSON.parse(
        sessionStorage.getItem(storageKey + ":request") || "null",
      );
    } catch {
      savedRequest.current = null;
    }
    setId(readId());
    setGroup(null);
    setError("");
  }, [storageKey, presenter]);
  useEffect(() => {
    if (!id || !presenter || (group?.id === id && group.state !== "running"))
      return;
    let alive = true,
      inFlight = false;
    let timer: ReturnType<typeof window.setInterval>;
    const load = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const result = await api("/analysis/pending/" + id);
        if (alive) {
          setGroup(result);
          setError("");
        }
      } catch (e) {
        if (alive)
          setError("No se pudo recuperar el progreso: " + (e as Error).message);
        clearInterval(timer);
      } finally {
        inFlight = false;
      }
    };
    void load();
    timer = window.setInterval(() => {
      if (document.visibilityState !== "hidden") void load();
    }, 2000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [id, presenter, group?.state, trackingVersion]);
  useEffect(() => {
    if (group && focusAfterStart.current) {
      focusAfterStart.current = false;
      progressRef.current?.focus({ preventScroll: true });
      progressRef.current?.scrollIntoView({
        block: "center",
        behavior: "instant",
      });
    }
  }, [group?.id]);
  const pending = articles.filter((a) => a.state === "pending");
  if (!pending.length && !group && !busy && !error) return null;
  const running = group?.state === "running";
  const counts = group?.counts || {};
  return (
    <div className="pending-analysis pending-bulk">
      <button
        className="button primary"
        disabled={!presenter || busy || running || !pending.length}
        title={
          !presenter
            ? "Acceso de presentador necesario"
            : "Analiza todas las pendientes de esta vista sin repetir análisis en curso"
        }
        onClick={async () => {
          focusAfterStart.current = true;
          const recovering = Boolean(error && savedRequest.current);
          const request = recovering
            ? savedRequest.current
            : {
                request_id: crypto.randomUUID(),
                article_ids: pending.map((a) => a.id),
                context,
                analysis_profile: DEFAULT_ANALYSIS_PROFILE,
              };
          const requestId = request.request_id;
          savedRequest.current = request;
          setPreparingTotal(pending.length);
          setBusy(true);
          setError("");
          setGroup(null);
          try {
            sessionStorage.setItem(storageKey, requestId);
            sessionStorage.setItem(
              storageKey + ":request",
              JSON.stringify(request),
            );
          } catch {
            /* Optional browser continuity. */
          }
          try {
            if (recovering) {
              try {
                const recovered = await api("/analysis/pending/" + requestId);
                setGroup(recovered);
                setId(recovered.id);
                return;
              } catch (e) {
                if ((e as { status?: number }).status !== 404) throw e;
              }
            }
            const result = await api("/analysis/pending", {
              method: "POST",
              body: JSON.stringify(request),
            });
            setGroup(result);
            setId(result.id);
            // The list refresh already reads all active jobs in one query.
            // Avoid starting one polling loop per row for a large selection.
          } catch (e) {
            setId(requestId);
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy
          ? `Preparando ${preparingTotal} noticias…`
          : running
            ? `Analizando ${group.total} noticias…`
            : pending.length
              ? `Analizar todas las pendientes (${pending.length})`
              : "Sin noticias pendientes"}
      </button>
      <small>
        Todas las pendientes de esta vista y sus filtros · perfil predeterminado
        para nuevas ejecuciones. Las que ya están en curso conservan su perfil;
        se respetan los límites técnicos del servicio.
      </small>
      {!presenter && (
        <small>Inicia sesión como presentador para analizar.</small>
      )}
      {presenter && group && (
        <div
          className="pending-progress"
          ref={progressRef}
          tabIndex={-1}
          role="region"
          aria-label="Progreso de la selección actual"
        >
          <div role="status" aria-live="polite">
            <strong>
              {counts.done || 0} de {group.total} analizadas
            </strong>{" "}
            · {counts.queued || 0} en cola · {counts.running || 0} en proceso ·{" "}
            {counts.error || 0} {counts.error === 1 ? "error" : "errores"}
            {counts.skipped
              ? ` · ${counts.skipped} omitidas porque ya no están pendientes`
              : ""}
          </div>
          <progress
            max={group.total || 1}
            value={group.finished}
            aria-label="Progreso del lote de análisis"
            aria-valuetext={`${group.finished} de ${group.total} terminadas; ${counts.done || 0} analizadas, ${counts.error || 0} ${counts.error === 1 ? "error" : "errores"}`}
          />
          <small>
            {Math.round((group.finished / Math.max(group.total, 1)) * 100)}% del
            lote terminado. El total se fija al pulsar el botón; las noticias
            nuevas no lo modifican.
          </small>
          {group.state !== "running" && (
            <p>
              {counts.error
                ? "Lote finalizado con errores; revisa los detalles antes de reintentar."
                : "Lote finalizado. Los resultados están disponibles; las dudas de clasificación conservan su revisión."}
            </p>
          )}
          {!!counts.error && (
            <details>
              <summary>
                Ver {counts.error} {counts.error === 1 ? "error" : "errores"}
              </summary>
              {group.items
                .filter((i: any) => i.state === "error")
                .map((i: any) => (
                  <p key={i.article_id}>
                    {i.headline || i.article_id}:{" "}
                    {i.error || "Abre la noticia para diagnosticar el fallo."}
                  </p>
                ))}
            </details>
          )}
        </div>
      )}
      {error && (
        <p role="alert">
          {error} La cola se conserva.
          <button
            className="button"
            onClick={() => {
              setTrackingVersion((n) => n + 1);
            }}
          >
            Recuperar progreso guardado
          </button>
        </p>
      )}
    </div>
  );
}

export function PendingAnalysis(props: {
  articles: Article[];
  presenter: boolean;
  single?: boolean;
}) {
  return props.single ? (
    <SinglePendingAnalysis {...props} />
  ) : (
    <BulkPendingAnalysis {...props} />
  );
}
