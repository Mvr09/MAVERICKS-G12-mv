import { useEffect, useState, useRef } from "react";
import { api, date, number } from "./api";
import { LoadingBlock } from "./OperationFeedback";
import { estimate, amount } from "./simulator";
const pct = (v: any) => (v == null ? "No calculable" : number(v * 100) + "%");
const secs = (v: any) => (v == null ? "No disponible" : number(v) + " s");
const read = () => {
  try {
    return JSON.parse(sessionStorage.getItem("radar:final-model") || "{}");
  } catch {
    return {};
  }
};
function Matrix({ title, m }: { title: string; m: any }) {
  return (
    <section className="card final-matrix">
      <h3>{title}</h3>
      {m ? (
        <>
          <p>
            {m.n} noticias · {m.positives} positivas de referencia
          </p>
          <table>
            <caption>Referencia en filas · predicción en columnas</caption>
            <thead>
              <tr>
                <th>Referencia</th>
                <th>Predicción: Sí</th>
                <th>Predicción: No</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th>Sí</th>
                <td>
                  <strong>{m.tp}</strong>
                  <span>Acierto positivo · TP</span>
                </td>
                <td>
                  <strong>{m.fn}</strong>
                  <span>Omisión · FN</span>
                </td>
              </tr>
              <tr>
                <th>No</th>
                <td>
                  <strong>{m.fp}</strong>
                  <span>Falsa alarma · FP</span>
                </td>
                <td>
                  <strong>{m.tn}</strong>
                  <span>Acierto negativo · TN</span>
                </td>
              </tr>
            </tbody>
          </table>
        </>
      ) : (
        <p>No disponible: faltan predicciones con referencia.</p>
      )}
    </section>
  );
}
export function ModelPage(_props: any) {
  const rateEdited = useRef(false);
  const initial = read(),
    [sample, setSample] = useState(initial.sample || "labelled"),
    [data, setData] = useState<any>(null),
    [error, setError] = useState(""),
    [reload, setReload] = useState(0),
    [loading, setLoading] = useState(true),
    [x, setX] = useState(initial.x ?? "10"),
    [y, setY] = useState(initial.y ?? ""),
    [rate, setRate] = useState(initial.rate ?? "0.03941248835"),
    [dirtyY, setDirtyY] = useState(Boolean(initial.dirtyY));
  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError("");
    api("/model/final?sample=" + sample)
      .then((d) => {
        if (alive) {
          setData(d);
          if (!rateEdited.current && initial.rate === undefined)
            setRate(String(d.profile.historical_rate.per_million_tokens));
          if (!dirtyY && d.performance?.tokens_reported?.mean != null)
            setY(String(Math.round(d.performance.tokens_reported.mean)));
        }
      })
      .catch((e) => {
        if (alive) setError(e.message);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [sample, reload]);
  useEffect(() => {
    try {
      sessionStorage.setItem(
        "radar:final-model",
        JSON.stringify({ sample, x, y, rate, dirtyY }),
      );
    } catch {}
  }, [sample, x, y, rate, dirtyY]);
  if (!data && loading)
    return <LoadingBlock label="Cargando perfil, métricas y telemetría…" />;
  if (!data)
    return (
      <section className="card detail-card" role="alert">
        <p>{error || "No se pudo cargar el perfil."}</p>
        <button className="button" onClick={() => setReload((n) => n + 1)}>
          Reintentar carga de Modelo
        </button>
      </section>
    );
  const q = data.quality,
    p = data.performance,
    mean = p?.fresh?.mean ?? null,
    simulation = estimate(x, y, rate, mean),
    profile = data.profile;
  return (
    <div className="final-model" aria-busy={loading}>
      <section className="card">
        <div className="section-heading">
          <div>
            <span className="badge purple">Recomendado · perfil actual</span>
            <h2>Perfil final de Supplier Risk Radar</h2>
            <p>
              Preguntas 3.4.2 · revisión 1.3.1 · JEV {profile.components.model}
            </p>
          </div>
        </div>
        <p>
          Evaluación: {data.evaluation?.name || "No disponible"} ·{" "}
          {date(data.evaluation?.completed_at)}. Commit de ejecución{" "}
          {profile.evaluation_commit}.
        </p>
        <details>
          <summary>Componentes, procedencia y rollback</summary>
          <dl className="version-grid">
            {Object.entries(profile.components).map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{String(v)}</dd>
              </div>
            ))}
          </dl>
          <p>
            El identificador histórico se conserva: {profile.profile}. 1.0.0
            sigue disponible en las opciones avanzadas de análisis. No se han
            reanalizado históricos por la promoción.
          </p>
        </details>
        <p className="notice info">
          {data.limit} A06 sigue abierto: errores del motor y provincia de S003
          desconocida. Promover el perfil no resuelve esas limitaciones.
        </p>
      </section>
      {error && (
        <div className="notice error" role="alert">
          {error}
          <button className="button" onClick={() => setReload((n) => n + 1)}>
            Reintentar consulta
          </button>
        </div>
      )}
      <section className="card">
        <div className="final-section-heading">
          <h2>Calidad medida</h2>
          <label>
            Muestra
            <select
              aria-label="Muestra evaluada"
              value={sample}
              onChange={(e) => setSample(e.target.value)}
            >
              <option value="training">Training · 30 · desarrollo</option>
              <option value="validation">
                Validation · 10 · retrospectiva
              </option>
              <option value="labelled">
                Total etiquetado · 40 · descriptivo
              </option>
            </select>
          </label>
        </div>
        {loading && <p role="status">Actualizando la muestra…</p>}
        {data.status === "unavailable" ? (
          <p role="status">{data.message}</p>
        ) : (
          <>
            <p>
              {q.total} entradas · {q.completed} análisis válidos · {q.errors}{" "}
              errores · {q.pending} pendientes. Las predicciones revisadas están
              incluidas. El total suma TP/FP/FN y recalcula las métricas.
            </p>
            <div className="final-quality-grid">
              {[
                ["risk", "Riesgo"],
                ["urgent", "Urgencia"],
                ["suppliers", "Proveedores"],
              ].map(([k, title]) => {
                const m = q.quality?.[k];
                return (
                  <article key={k}>
                    <h3>{title}</h3>
                    {m ? (
                      <>
                        <p>
                          TP {m.tp} · FP {m.fp} · FN {m.fn}
                          {k !== "suppliers" ? ` · TN ${m.tn}` : ""}
                        </p>
                        {[
                          ["precision", "Precisión"],
                          ["recall", "Recall"],
                          ["f1", "F1"],
                        ].map(([f, label]) => (
                          <div className="final-metric" key={f}>
                            <span>{label}</span>
                            <strong>{pct(m[f])}</strong>
                            {m[f] != null && (
                              <meter
                                min={0}
                                max={1}
                                value={m[f]}
                                aria-label={title + " · " + label}
                              />
                            )}
                          </div>
                        ))}
                        <p>
                          {k === "suppliers"
                            ? `Asociaciones micro · conjuntos exactos ${m.exact}/${m.n}`
                            : `${m.n} noticias · ${m.positives} positivas de referencia`}
                        </p>
                      </>
                    ) : (
                      <p>
                        No calculable: sin referencias y predicciones válidas.
                      </p>
                    )}
                  </article>
                );
              })}
            </div>
            <p>
              Escala 0–100%. No se calcula un score global ni una matriz binaria
              de proveedores sin universo definido.
            </p>
            <div className="final-stat-grid">
              <div>
                <small>Cobertura automática</small>
                <strong>{pct(q.automatic_rate)}</strong>
                <span>
                  {q.automatic}/{q.total} entradas
                </span>
              </div>
              <div>
                <small>Revisión de análisis</small>
                <strong>{q.review}</strong>
                <span>
                  {q.review}/{q.total} entradas
                </span>
              </div>
              <div>
                <small>Errores entre automáticas</small>
                <strong>
                  {q.automatic_errors == null
                    ? "No calculable"
                    : `${q.automatic_errors}/${q.automatic_labelled}`}
                </strong>
                <span>Riesgo, urgencia y conjunto de proveedores</span>
              </div>
            </div>
            <p>
              Cobertura no es precisión; confianza JEV y prioridad empresarial
              tampoco son F1. Test, LiveDay y RSS no tienen precisión evaluada
              sin etiquetas.
            </p>
          </>
        )}
      </section>
      <div className="final-matrices">
        <Matrix title="Riesgo" m={q?.quality?.risk} />
        <Matrix title="Urgencia" m={q?.quality?.urgent} />
      </div>
      <section className="card">
        <h2>Rendimiento observado por noticia</h2>
        {p ? (
          <>
            <h3>Campaña local importada · inferencia nueva</h3>
            <div className="final-stat-grid">
              <div>
                <small>Media aritmética individual</small>
                <strong>{secs(p.fresh.mean)}</strong>
                <span>{p.fresh.n} noticias del perfil final</span>
              </div>
              <div>
                <small>Mediana / p95 individual</small>
                <strong>
                  {secs(p.fresh.median)} / {secs(p.fresh.p95)}
                </strong>
                <span>p95 por rango más próximo</span>
              </div>
              <div>
                <small>Espera en cola, separada</small>
                <strong>{secs(p.queue.mean)}</strong>
                <span>{p.queue.n} marcas de cola</span>
              </div>
            </div>
            <p>{p.definition}</p>
            <p>
              Periodo {date(p.start)} – {date(p.end)}. Entorno:{" "}
              {p.environment.service}, Python {p.environment.python}. Campaña
              concurrente de cuatro ejecutores; esto no certifica throughput en
              Railway.
            </p>
            <p>
              {p.new_requests} llamadas nuevas · {p.cached_or_mixed.n} análisis
              con caché o mixtos, separados de la media nueva.
            </p>
            <h3>Mediciones nuevas del worker de Railway</h3>
            <p>
              Inferencia nueva: {data.railway.fresh.n} noticias · media{" "}
              {secs(data.railway.fresh.mean)}. Caché/mixtas:{" "}
              {data.railway.cached_or_mixed.n} · media{" "}
              {secs(data.railway.cached_or_mixed.mean)}. Cola media{" "}
              {secs(data.railway.queue?.mean)}.
            </p>
            <p>
              {data.railway.definition} Las muestras pequeñas no garantizan
              tiempos futuros.
            </p>
          </>
        ) : (
          <p>
            No disponible: faltan marcas individuales válidas del perfil final.
          </p>
        )}
      </section>
      <section className="card simulator">
        <h2>Mini simulador de tiempo y coste</h2>
        <p>
          Si llegan X noticias con Y tokens facturables por noticia, estimamos
          este tiempo y coste.
        </p>
        <div className="simulator-inputs">
          <label>
            X · Número de noticias
            <input
              aria-label="Número de noticias"
              type="number"
              min="0"
              step="1"
              value={x}
              onChange={(e) => setX(e.target.value)}
            />
          </label>
          <label>
            Y · Tokens totales por noticia
            <input
              aria-label="Tokens por noticia"
              type="number"
              min="0"
              step="1"
              value={y}
              onChange={(e) => {
                setY(e.target.value);
                setDirtyY(true);
              }}
            />
          </label>
        </div>
        <p>
          Y incluye instrucciones, catálogo, respuestas y todas las llamadas del
          análisis; no solo el texto de la noticia. Una noticia no equivale a
          una petición JEV.
        </p>
        <p>
          Valor inicial: media de entrada+salida reportadas en{" "}
          {p?.tokens_reported.n || 0} noticias del perfil final, redondeada a
          tokens enteros. Aproximación a tokens facturables; no hay confirmación
          contractual de caché o facturación. Puedes corregir Y.
        </p>
        <details>
          <summary>Ajustes y supuestos de la estimación</summary>
          <label>
            Tasa efectiva histórica · $ por millón de tokens
            <input
              aria-label="Tasa por millón de tokens"
              type="number"
              min="0"
              step="any"
              value={rate}
              onChange={(e) => {
                rateEdited.current = true;
                setRate(e.target.value);
              }}
            />
          </label>
          <p>
            Referencia aportada el 19/10/2026: Spend 2,6045 $, Tokens
            66.083.115, Requests 5.157. Asumiendo mismo ámbito y periodo: 2,6045
            / 66.083.115 × 1.000.000 = 0,03941248835 $ por millón. No es tarifa
            oficial ni precio separado de entrada/salida. Se conserva el símbolo
            $, sin asumir divisa.
          </p>
          <p>
            Tokens = X × Y. Coste = X × Y / 1.000.000 × tasa. Tiempo secuencial
            = X × media individual observada, sin cola. Y modifica el coste; no
            se ha calibrado una relación lineal entre tokens y latencia. No se
            divide por workers teóricos.
          </p>
        </details>
        {simulation.error ? (
          <p role="alert">{simulation.error}</p>
        ) : (
          <div className="final-stat-grid" aria-live="polite">
            <div>
              <small>Tiempo estimado</small>
              <strong>{secs(simulation.seconds)}</strong>
              <span>
                Secuencial, sin espera en cola; noticia media local observada
              </span>
            </div>
            <div>
              <small>Coste estimado</small>
              <strong>{amount(simulation.cost!)}</strong>
              <span>{number(simulation.tokens)} tokens proyectados</span>
            </div>
          </div>
        )}
        <p>
          Proyección, no medición nueva ni factura. Cambiar estos datos no llama
          a JEV, no crea trabajos y no modifica métricas.
        </p>
      </section>
    </div>
  );
}
