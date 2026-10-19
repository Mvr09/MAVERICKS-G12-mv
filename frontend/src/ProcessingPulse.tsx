import { PendingAnalysis } from "./PendingAnalysis";
import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { scopedPath } from "./NewsContinuity";
import { Activity, ArrowUpRight } from "lucide-react";
import type { Article } from "./types";

/** Arrival signals follow real API state transitions; initial history is not new. */
export function ProcessingPulse({
  articles,
  analysisArticles = articles,
  presenter = false,
}: {
  articles: Article[];
  analysisArticles?: Article[];
  presenter?: boolean;
}) {
  const location = useLocation();
  const context =
    new URLSearchParams(location.search).get("context") === "rss"
      ? "rss"
      : "exercise";
  const previous = useRef<Map<string, string> | null>(null);
  const [updates, setUpdates] = useState<
    { id: string; headline: string; state: string }[]
  >([]);
  const [total, setTotal] = useState(0);
  const done = articles.filter((a) =>
    a.state === "done" || a.state === "human_resolved"
      ? "Revisión humana resuelta"
      : a.state === "review",
  ).length;
  const errors = articles.filter((a) => a.state === "error").length;
  const pending = articles.length - done - errors;
  useEffect(() => {
    if (!articles.length) return;
    const current = new Map(
      articles.map((a) => [
        a.id,
        `${a.generation || 0}:${a.version || 1}:${a.state}:${a.human_review?.updated_at || ""}:${a.human_review?.state || ""}`,
      ]),
    );
    if (!previous.current) {
      try {
        const saved = JSON.parse(
          localStorage.getItem("radar:last-news:" + context) || "null",
        );
        if (Array.isArray(saved)) previous.current = new Map(saved);
      } catch {
        /* Storage is optional. */
      }
    }
    if (previous.current) {
      const changed = articles.filter(
        (a) => current.get(a.id) !== previous.current!.get(a.id),
      );
      if (changed.length) {
        setTotal((n) => n + changed.length);
        setUpdates((old) =>
          [
            ...changed.map((a) => ({
              id: a.id,
              headline: a.headline,
              state:
                a.human_review?.state === "resolved"
                  ? "human_resolved"
                  : a.state,
            })),
            ...old.filter((a) => !changed.some((b) => a.id === b.id)),
          ].slice(0, 3),
        );
      }
    }
    previous.current = current;
    try {
      localStorage.setItem(
        "radar:last-news:" + context,
        JSON.stringify([...current].slice(0, 2000)),
      );
    } catch {
      /* Optional browser continuity. */
    }
  }, [articles]);
  return (
    <section className="processing-pulse" aria-label="Actividad de análisis">
      <div className="processing-status">
        <Activity size={18} />
        <div>
          <strong>
            {!articles.length
              ? "Sin noticias recibidas"
              : pending
                ? "Análisis por completar"
                : errors
                  ? "Resultados parciales"
                  : "Resultados disponibles"}
          </strong>
          <p>
            {done} de {articles.length} analizadas · {pending} pendientes ·{" "}
            {errors} con error
          </p>
        </div>
        <span className="processing-new" role="status" aria-live="polite">
          {total
            ? `${total} ${total === 1 ? "actualización" : "actualizaciones"} desde la última consulta en este navegador`
            : "Las novedades aparecerán aquí"}
        </span>
      </div>
      <PendingAnalysis articles={analysisArticles} presenter={presenter} />
      <div
        className="processing-track"
        role="progressbar"
        aria-label="Noticias con resultado"
        aria-valuenow={done}
        aria-valuemin={0}
        aria-valuemax={Math.max(articles.length, 1)}
      >
        <span
          style={{
            width: `${articles.length ? (done / articles.length) * 100 : 0}%`,
          }}
        />
      </div>
      <div className="processing-updates" aria-label="Últimos cambios">
        {!updates.length && (
          <small>
            Sin cambios nuevos desde la última consulta en este navegador.
          </small>
        )}
        {updates.map((a) => (
          <Link key={a.id} to={scopedPath("/noticias/" + a.id, context)}>
            <span>
              {a.state === "human_resolved"
                ? "Revisión humana resuelta"
                : a.state === "review"
                  ? "Revisar"
                  : a.state === "done"
                    ? "Analizada"
                    : a.state === "error"
                      ? "Error"
                      : "Pendiente"}
            </span>
            {a.headline}
            <ArrowUpRight size={14} />
          </Link>
        ))}
      </div>
    </section>
  );
}
