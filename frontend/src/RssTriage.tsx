import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "./api";
import { AnalysisProfile, CANDIDATE } from "./AnalysisProfile";
export function RssTriage({ articles }: { articles: any[] }) {
  const [selected, setSelected] = useState<string[]>([]),
    [selectedTitles, setSelectedTitles] = useState<Record<string, string>>({}),
    [profile, setProfile] = useState("1.0.0"),
    [ack, setAck] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [jobs, setJobs] = useState<any[]>([]),
    [ids, setIds] = useState<string[]>([]);
  useEffect(() => {
    if (!ids.length) return;
    let active = true;
    async function update() {
      try {
        const values = await Promise.all(ids.map((id) => api("/jobs/" + id)));
        if (active) setJobs(values);
      } catch (e) {
        if (active) setError((e as Error).message);
      }
    }
    void update();
    const timer = setInterval(update, 3000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [ids]);
  const pending = articles
    .filter((a) => a.state === "pending")
    .sort(
      (a, b) =>
        (({ named: 0, service: 1, geography: 2, none: 3 })[
          a.preliminary_relevance?.level as
            | "named"
            | "service"
            | "geography"
            | "none"
        ] ?? 3) -
        ({ named: 0, service: 1, geography: 2, none: 3 }[
          b.preliminary_relevance?.level as
            | "named"
            | "service"
            | "geography"
            | "none"
        ] ?? 3),
    );
  const inProgress = jobs.some((j) => ["queued", "running"].includes(j.state));
  return (
    <details className="rss-triage">
      <summary>
        Seleccionar noticias para análisis manual · {pending.length} pendientes
        en esta vista
      </summary>
      <p>
        Selecciona hasta10entradas, revisa su alcance yelige el perfil. Los
        indicios preliminares ayudan a ordenar lectura; no prueban afectación.
      </p>
      <AnalysisProfile
        rss
        value={profile}
        onChange={(value) => {
          setProfile(value);
          setAck(false);
        }}
        disabled={busy || inProgress}
      />
      {pending.slice(0, 30).map((a) => (
        <label className="triage-option" key={a.id}>
          <input
            type="checkbox"
            data-article-id={a.id}
            aria-label={"Seleccionar noticia " + a.headline}
            checked={selected.includes(a.id)}
            disabled={
              busy ||
              inProgress ||
              (!selected.includes(a.id) && selected.length >= 10)
            }
            onChange={(e) => {
              setSelectedTitles((old) => ({ ...old, [a.id]: a.headline }));
              setSelected((old) =>
                e.target.checked
                  ? [...new Set([...old, a.id])]
                  : old.filter((id) => id !== a.id),
              );
              setAck(false);
            }}
          />
          <span>
            <strong>{a.headline}</strong>
            <small>
              {a.preliminary_relevance?.reasons?.join(" · ") ||
                "Sin indicio preliminar; no significa irrelevante"}
            </small>
          </span>
        </label>
      ))}
      {pending.length > 30 && (
        <p>
          Se muestran30pendientes; usa los filtros para acotar la selección.
        </p>
      )}
      <button
        className="button"
        disabled={busy || inProgress}
        onClick={() => {
          setSelected([]);
          setSelectedTitles({});
          setAck(false);
          setIds([]);
        }}
      >
        Limpiar selección
      </button>
      <p role="status">
        {selected.length} seleccionadas · máximo técnico de
        {selected.length * (profile === CANDIDATE ? 36 : 6)}peticiones,
        incluidos reintentos. No es una estimación de coste.
      </p>
      {selected.length > 0 && (
        <ul>
          {selected.map((id) => (
            <li key={id}>
              {selectedTitles[id] ||
                articles.find((a) => a.id === id)?.headline ||
                id}
            </li>
          ))}
        </ul>
      )}
      <label className="checkbox">
        <input
          type="checkbox"
          checked={ack}
          disabled={busy || inProgress}
          onChange={(e) => setAck(e.target.checked)}
        />
        Confirmo esta selección y su análisis manual. El periódico de pago
        continúa desactivado.
      </label>
      <button
        className="button primary"
        disabled={!selected.length || !ack || busy || inProgress}
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            const result = await api("/analysis/rss", {
              method: "POST",
              body: JSON.stringify({
                article_ids: selected,
                analysis_profile: profile,
              }),
            });
            setIds(result.job_ids);
            setJobs(
              result.job_ids.map((id: string) => ({ id, state: "queued" })),
            );
            setAck(false);
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy
          ? "Encolando…"
          : inProgress
            ? "Procesando selección…"
            : "Analizar selección"}
      </button>
      {error && (
        <p className="notice error" role="alert">
          {error}
        </p>
      )}
      {jobs.length > 0 && (
        <div aria-live="polite">
          <p>
            {jobs.filter((j) => j.state === "done").length}/{jobs.length}{" "}
            análisis terminados ·{" "}
            {jobs.filter((j) => j.state === "error").length} errores. Los
            errores no se convierten en «sin riesgo».
          </p>
          {jobs.map((j) => (
            <p key={j.id}>
              {j.state === "done"
                ? "Terminado"
                : j.state === "error"
                  ? "Error: " + j.error
                  : j.state === "running"
                    ? "Analizando"
                    : "En cola"}{" "}
              · {j.network_requests || 0} peticiones
              {j.last_completed_step ? " · " + j.last_completed_step : ""}
              {j.article_id && (
                <>
                  {" "}
                  ·{" "}
                  <Link to={"/noticias/" + j.article_id + "?context=rss"}>
                    Ver resultado o diagnosticar error
                  </Link>
                </>
              )}
            </p>
          ))}
        </div>
      )}
    </details>
  );
}
