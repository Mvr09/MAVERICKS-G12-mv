import { CampaignCompare } from "./CampaignCompare";
import { WindowEvaluation } from "./WindowEvaluation";
import { CandidateComparison } from "./CandidateComparison";
import { ReviewPolicyComparison } from "./ReviewPolicyComparison";
import React, { useEffect, useState } from "react";
import { api, date, number } from "./api";
import type { Batch, Source } from "./types";
import { DiagnosticPanel } from "./DiagnosticPanel";

const percent = (value: number | null | undefined) =>
  value == null ? "No calculable" : number(value * 100) + "%";
const score = (value: number | null | undefined) =>
  value == null
    ? "No calculable"
    : value.toLocaleString("es-ES", { maximumFractionDigits: 3 });
const splits: Record<string, string> = {
  training: "Entrenamiento · desarrollo",
  validation: "Validación · comparación retrospectiva",
  test: "Test sin etiquetas",
  liveday: "LiveDay sin etiquetas",
};

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <small>{label}</small>
      <strong>{value}</strong>
    </div>
  );
}
function MetricCards({
  rows,
}: {
  rows: { name: string; items: [string, React.ReactNode][] }[];
}) {
  return (
    <div className="metric-cards">
      {rows.map((row) => (
        <section key={row.name}>
          <h4>{row.name}</h4>
          <dl>
            {row.items.map(([name, value]) => (
              <div key={name}>
                <dt>{name}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </section>
      ))}
    </div>
  );
}
function Confusion({ title, metric }: { title: string; metric: any }) {
  return (
    <section className="confusion">
      <h3>{title}</h3>
      <table>
        <caption>
          {metric.n} noticias · {metric.positives} positivos de referencia
        </caption>
        <thead>
          <tr>
            <th>Referencia / predicción</th>
            <th>Positiva</th>
            <th>Negativa</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th>Positiva</th>
            <td>
              {metric.tp}
              <small>Aciertos positivos</small>
            </td>
            <td className="metric-warning">
              {metric.fn}
              <small>Omisiones</small>
            </td>
          </tr>
          <tr>
            <th>Negativa</th>
            <td>
              {metric.fp}
              <small>Falsas alarmas</small>
            </td>
            <td>
              {metric.tn}
              <small>Aciertos negativos</small>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  );
}

function HistoricalModelPage({
  presenter,
  context,
  config,
  batches,
  sources,
}: {
  presenter: boolean;
  context: string;
  config: any;
  batches: Batch[];
  sources: Source[];
}) {
  const [data, setData] = useState<any>(null),
    [error, setError] = useState(""),
    [selection, setSelection] = useState(""),
    [origin, setOrigin] = useState("");
  useEffect(() => {
    setOrigin("");
  }, [context]);
  useEffect(() => {
    setData(null);
    setError("");
    if (!presenter) return;
    let active = true,
      inFlight = false;
    async function refresh() {
      if (inFlight) return;
      inFlight = true;
      try {
        const report = await api(
          "/model/metrics?context=" +
            context +
            (origin ? "&origin=" + encodeURIComponent(origin) : ""),
        );
        if (active) {
          setData(report);
          setError("");
        }
      } catch (e) {
        if (active) setError((e as Error).message);
      } finally {
        inFlight = false;
      }
    }
    refresh();
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") refresh();
    }, 3000);
    const focus = () => refresh();
    window.addEventListener("focus", focus);
    return () => {
      active = false;
      clearInterval(interval);
      window.removeEventListener("focus", focus);
    };
  }, [presenter, context, origin]);
  const evaluations = data?.evaluations || [];
  const selected =
    evaluations.find((row: any) => row.id === selection) ||
    evaluations.find((row: any) => row.split === "validation") ||
    evaluations[0];
  const m = selected?.metrics,
    execution = data?.execution;
  return (
    <div className="model-page">
      <section className="card detail-card">
        <h2>Modelo</h2>
        <p>
          Calidad medida y ejecución de JEV. Actualización cada 3 segundos
          mientras esta pestaña está visible; consultar métricas no ejecuta
          análisis.
        </p>
        <p className="small-note">
          Modelo configurado: {config.model} · Ejercicio:{" "}
          {config.question_version} · RSS: {config.rss_question_version}
        </p>
      </section>
      {!presenter ? (
        <section className="card detail-card">
          <h3>Acceso de presentador</h3>
          <p>
            Inicia sesión desde el encabezado para consultar evaluación y
            telemetría. Las etiquetas y respuestas de referencia permanecen
            privadas.
          </p>
        </section>
      ) : (
        <>
          <WindowEvaluation />
          <CandidateComparison />
          <ReviewPolicyComparison />
          {error && (
            <div className="notice error" role="alert">
              {error}{" "}
              {data &&
                "Los datos mostrados corresponden a la última consulta correcta."}
            </div>
          )}
          {!data && !error && (
            <p role="status">Calculando métricas registradas…</p>
          )}
          {data && (
            <>
              <section className="card detail-card">
                <h2>Calidad con etiquetas de referencia</h2>
                <label className="model-selector">
                  Lote de evaluación
                  <select
                    aria-label="Lote de evaluación"
                    value={selected?.id || ""}
                    onChange={(e) => setSelection(e.target.value)}
                  >
                    {evaluations.map((row: any) => (
                      <option key={row.id} value={row.id}>
                        {splits[row.split] || row.split} · {row.label}
                      </option>
                    ))}
                  </select>
                </label>
                {!evaluations.some((row: any) => row.split === "training") && (
                  <p className="small-note">
                    Entrenamiento no cargado. Sus resultados de desarrollo se
                    mostrarán separados de validación.
                  </p>
                )}
                {!selected ? (
                  <p>No hay lotes importados para evaluar.</p>
                ) : !m ? (
                  <div className="notice warning">
                    <span>
                      {selected.reason ||
                        "Completa el lote antes de evaluarlo."}{" "}
                      {selected.count} entradas; no se muestra F1 como cero ni
                      se consideran correctas respuestas vacías.
                    </span>
                  </div>
                ) : (
                  <>
                    <p>
                      <strong>{m.n} noticias</strong> · Modelo {m.model_id} ·
                      Preguntas {m.question_version} · Política{" "}
                      {m.policy_version}.{" "}
                      {selected.split === "training"
                        ? "Datos de desarrollo: no son una estimación independiente."
                        : "Muestra pequeña; no demuestra rendimiento general."}
                    </p>
                    <div className="analytics-stats">
                      <Stat label="F1 de riesgo" value={score(m.risk.f1)} />
                      <Stat
                        label="Recall de riesgo"
                        value={percent(m.risk.recall)}
                      />
                      <Stat label="F1 de urgencia" value={score(m.urgent.f1)} />
                      <Stat
                        label="Proveedores exactos"
                        value={`${m.suppliers.exact} / ${m.n}`}
                      />
                    </div>
                    <MetricCards
                      rows={[
                        ["Riesgo", m.risk],
                        ["Urgencia", m.urgent],
                        ["Proveedores · micro", m.suppliers],
                      ].map(([name, metric]: any) => ({
                        name,
                        items: [
                          ["Precisión", percent(metric.precision)],
                          ["Recall", percent(metric.recall)],
                          ["F1", score(metric.f1)],
                          [
                            "Positivos",
                            metric.positives ?? metric.tp + metric.fn,
                          ],
                        ],
                      }))}
                    />
                    <div className="metric-table-wrap">
                      <table className="quality-table">
                        <caption>
                          Métricas principales: incluyen noticias que requieren
                          revisión
                        </caption>
                        <thead>
                          <tr>
                            <th>Tarea</th>
                            <th>Precisión</th>
                            <th>Recall</th>
                            <th>F1</th>
                            <th>Referencia positiva</th>
                          </tr>
                        </thead>
                        <tbody>
                          {[
                            ["Riesgo", m.risk],
                            ["Urgencia", m.urgent],
                            ["Proveedores · micro", m.suppliers],
                          ].map(([name, metric]: any) => (
                            <tr key={name}>
                              <th>{name}</th>
                              <td>{percent(metric.precision)}</td>
                              <td>{percent(metric.recall)}</td>
                              <td>{score(metric.f1)}</td>
                              <td>
                                {metric.positives ?? metric.tp + metric.fn}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <p className="small-note">
                      Precisión: cuántas detecciones fueron correctas. Recall:
                      cuántos positivos de referencia detectamos. F1 equilibra
                      ambas. Sin positivos o detecciones suficientes, la métrica
                      correspondiente no es calculable. Coincidencia exacta de
                      proveedores: {percent(m.suppliers.exact_set_accuracy)}.
                    </p>
                    <div className="confusion-grid">
                      <Confusion title="Matriz de riesgo" metric={m.risk} />
                      <Confusion title="Matriz de urgencia" metric={m.urgent} />
                    </div>
                    <h3>Calidad y necesidad de revisión</h3>
                    <p>
                      {m.review_count}/{m.n} noticias en revisión (
                      {percent(m.review_rate)}); cobertura automática{" "}
                      {percent(m.automatic_coverage)}. Revisar no equivale a
                      acertar o fallar.
                    </p>
                    <MetricCards
                      rows={[
                        ["Todas · principal", m],
                        ["Sin revisión", m.automatic],
                        ["Requieren revisión", m.under_review],
                      ].map(([name, subset]: any) => ({
                        name,
                        items: [
                          ["Noticias", subset?.n || 0],
                          ["F1 riesgo", score(subset?.risk.f1)],
                          ["Recall", percent(subset?.risk.recall)],
                        ],
                      }))}
                    />
                    <div className="metric-table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>Conjunto</th>
                            <th>Noticias</th>
                            <th>F1 riesgo</th>
                            <th>Recall riesgo</th>
                          </tr>
                        </thead>
                        <tbody>
                          {[
                            ["Todas · principal", m],
                            ["Sin revisión", m.automatic],
                            ["Requieren revisión", m.under_review],
                          ].map(([name, subset]: any) => (
                            <tr key={name}>
                              <th>{name}</th>
                              <td>{subset?.n || 0}</td>
                              <td>{score(subset?.risk.f1)}</td>
                              <td>{percent(subset?.risk.recall)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
                {selected && m && (
                  <DiagnosticPanel key={selected.id} bid={selected.id} />
                )}
                <p className="small-note">
                  Test, LiveDay y RSS no tienen referencia válida para medir
                  precisión/F1. La confianza de JEV, el acuerdo entre votos y la
                  prioridad 0–100 no sustituyen esa evaluación. No se evalúa
                  exactitud de severidad sin una referencia.
                </p>
              </section>
              <section className="card detail-card">
                <h2>Ejecución de JEV</h2>
                <label className="model-selector">
                  Origen de la ejecución
                  <select
                    aria-label="Origen de la ejecución"
                    value={origin}
                    onChange={(e) => setOrigin(e.target.value)}
                  >
                    <option value="">
                      Todo el contexto ·{" "}
                      {context === "rss" ? "Noticias reales" : "Datos base"}
                    </option>
                    {context === "rss"
                      ? sources.map((s) => (
                          <option key={s.id} value={"rss:" + s.id}>
                            {s.name}
                          </option>
                        ))
                      : batches.map((b) => (
                          <option key={b.id} value={"batch:" + b.id}>
                            {b.origin_label || b.filename || splits[b.split]}
                          </option>
                        ))}
                  </select>
                </label>
                <div className="analytics-stats">
                  <Stat
                    label="Peticiones registradas"
                    value={number(execution.requests)}
                  />
                  <Stat
                    label="Reintentos HTTP"
                    value={number(execution.retries)}
                  />
                  <Stat
                    label="Intentos con error"
                    value={number(execution.failed_requests)}
                  />
                  <Stat
                    label="Resultados vigentes cacheados"
                    value={number(execution.cache_hits)}
                  />
                  <Stat
                    label="Trabajos en cola"
                    value={execution.jobs.queued || 0}
                  />
                  <Stat
                    label="Trabajos en ejecución"
                    value={execution.jobs.running || 0}
                  />
                </div>
                <h3>Latencia registrada</h3>
                <p>
                  Por intento HTTP: p50 {number(execution.http_latency.p50)} s ·
                  p95 {number(execution.http_latency.p95)} s · n=
                  {execution.http_latency.n}.
                </p>
                <p>
                  Duración de análisis vigente: p50{" "}
                  {number(execution.analysis_latency.p50)} s · p95{" "}
                  {number(execution.analysis_latency.p95)} s · n=
                  {execution.analysis_latency.n}. No incluye espera en cola; los
                  registros RSS anteriores a 2.1 pueden excluir la descarga
                  editorial.
                </p>
                <h3>Uso reportado por la API</h3>
                <p>
                  Tokens de entrada: {number(execution.usage.input_tokens)} ·
                  salida: {number(execution.usage.output_tokens)}.{" "}
                  {execution.calls_with_token_usage}/{execution.requests}{" "}
                  peticiones informan tokens; los datos ausentes no se estiman.
                </p>
                <p>
                  {execution.http_statuses
                    .map((r: any) => `HTTP ${r.status}: ${r.count}`)
                    .join(" · ") ||
                    "Sin peticiones registradas para este origen."}
                </p>
                <h3>Consistencia de tres evaluaciones</h3>
                <p>
                  {execution.consistency.unanimous}/
                  {execution.consistency.articles} noticias con acuerdo unánime
                  ({percent(execution.consistency.unanimous_rate)}). Solo el
                  último contraste completo de la generación vigente por
                  noticia. Son consultas del mismo modelo: el acuerdo no mide
                  precisión.
                </p>
                <h3>Versiones de análisis vigentes</h3>
                <ul>
                  {execution.versions.map((v: any) => (
                    <li
                      key={[v.model, v.questions, v.policy, v.review].join("|")}
                    >
                      {v.model} · preguntas {v.questions} · revisión{" "}
                      {v.review || "no registrada"} · política {v.policy}:{" "}
                      {v.count} noticias
                    </li>
                  ))}
                </ul>
                <p className="small-note">{execution.scope_note}</p>
              </section>
              <p className="small-note" role="status">
                Última consulta de métricas: {date(data.updated_at)}. Resultados
                vigentes; no es una nueva ejecución JEV.
              </p>
            </>
          )}
        </>
      )}
    </div>
  );
}

export function AdministrativeModels(props: Parameters<typeof HistoricalModelPage>[0]) {
  return (
    <CampaignCompare
      presenter={props.presenter}
      history={<HistoricalModelPage {...props} />}
    />
  );
}
