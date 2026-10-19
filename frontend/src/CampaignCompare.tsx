import { ReviewGuidance } from "./ReviewGuidance";
import React, { useEffect, useState } from "react";
import { api, date, number } from "./api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
const BASE = "1.0.0",
  CAND = "radar-1.0.0-candidate";
const label = (p: string) =>
  p === BASE ? "1.0.0 · referencia" : "3.4.2 · revisión 1.3.1";
const samples: Record<string, string> = {
  training: "Training · desarrollo",
  validation: "Validation · retrospectiva",
  test: "Test · sin etiquetas",
  liveday: "LiveDay · sin etiquetas",
  labelled: "Total etiquetado · descriptivo",
  all: "Todas · no mezclar precisión etiquetada con test",
};
const pct = (n: any) => (n == null ? "No disponible" : number(n * 100) + "%");
const decision = (v: any) =>
  v === "Y" ? "Sí" : v === "N" ? "No" : "Sin decisión";
const diff = (a: any, b: any) =>
  a == null || b == null
    ? "—"
    : `${b - a >= 0 ? "+" : ""}${number((b - a) * 100)} pp`;
const state = (s: string) =>
  ({
    prepared: "Preparada",
    queued: "En cola",
    running: "En ejecución",
    done: "Automático",
    review: "Analizado · revisión",
    error: "Error",
    complete: "Completa",
    paused: "Pausada",
  })[s] || s;
function read() {
  try {
    return JSON.parse(sessionStorage.getItem("radar:comparison") || "{}");
  } catch {
    return {};
  }
}
export function CampaignCompare({
  presenter,
  history,
}: {
  presenter: boolean;
  history: React.ReactNode;
}) {
  const initial = read();
  const [tab, setTab] = useState(initial.tab || "compare"),
    [campaigns, setCampaigns] = useState<any[]>([]),
    [cid, setCid] = useState(initial.cid || ""),
    [sample, setSample] = useState(initial.sample || "training"),
    [a, setA] = useState(initial.a || BASE),
    [b, setB] = useState(initial.b || CAND),
    [data, setData] = useState<any>(null),
    [error, setError] = useState(""),
    [cell, setCell] = useState<any>(initial.cell || null),
    [onlyDiff, setOnlyDiff] = useState(initial.onlyDiff || false),
    [q, setQ] = useState(initial.q || ""),
    [busy, setBusy] = useState(false),
    [confirmed, setConfirmed] = useState(false),
    [inspect, setInspect] = useState<string | null>(null),
    [diagnosis, setDiagnosis] = useState("");
  useEffect(() => {
    try {
      sessionStorage.setItem(
        "radar:comparison",
        JSON.stringify({ tab, cid, sample, a, b, cell, onlyDiff, q }),
      );
    } catch {
      /* Filters still work when browser storage is unavailable. */
    }
  }, [tab, cid, sample, a, b, cell, onlyDiff, q]);
  useEffect(() => {
    if (!presenter) return;
    let alive = true;
    async function load() {
      try {
        const x = await api("/campaigns");
        if (alive) {
          setCampaigns(x);
          if (!cid && x.length) setCid(x[0].id);
        }
      } catch (e) {
        if (alive) setError((e as Error).message);
      }
    }
    load();
    const t = setInterval(load, 5000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [presenter, cid]);
  useEffect(() => {
    if (!cid || !presenter) return;
    let alive = true,
      inFlight = false,
      terminal = false;
    setData(null);
    setInspect(null);
    async function load() {
      if (inFlight) return;
      inFlight = true;
      try {
        const x = await api("/campaigns/" + cid + "?split=" + sample);
        if (alive) {
          setData(x);
          terminal = x.state === "complete";
          setError("");
        }
      } catch (e) {
        if (alive) setError((e as Error).message);
      } finally {
        inFlight = false;
      }
    }
    load();
    const t = setInterval(() => {
      if (!terminal && document.visibilityState === "visible") void load();
    }, 4000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [cid, sample, presenter]);
  if (!presenter)
    return (
      <section className="card">
        <h2>Comparar calidad y ejecución</h2>
        <p>
          Accede como presentador para consultar campañas y referencias
          privadas. La consulta no ejecuta JEV.
        </p>
      </section>
    );
  const A = data?.aggregate[a],
    B = data?.aggregate[b];
  const rows: any[] = data?.rows || [];
  const keys = [...new Set(rows.map((r) => r.key))];
  const pairs = keys.map((key) => ({
    key,
    A: rows.find((r) => r.key === key && r.profile === a),
    B: rows.find((r) => r.key === key && r.profile === b),
  }));
  const different = (x: any) =>
    !x.A?.result ||
    !x.B?.result ||
    ["is_risk", "urgent", "analysis_status", "affected_supplier_ids"].some(
      (k) => JSON.stringify(x.A.result[k]) !== JSON.stringify(x.B.result[k]),
    );
  const visible = pairs.filter((x) => {
    if (onlyDiff && !different(x)) return false;
    if (
      q &&
      !((x.A?.headline || "") + " " + (x.A?.news_id || ""))
        .toLowerCase()
        .includes(q.toLowerCase())
    )
      return false;
    if (cell) {
      const r = cell.profile === a ? x.A : x.B;
      if (!r?.reference || !["done", "review"].includes(r.state)) return false;
      const pos =
          r.reference[cell.field === "is_risk" ? "Is_Risk" : "Urgent"] === "Y",
        pred = r.result[cell.field] === "Y";
      return (pos ? (pred ? "tp" : "fn") : pred ? "fp" : "tn") === cell.kind;
    }
    return true;
  });
  const chart = ["risk", "urgent", "suppliers"].flatMap((k) =>
    ["precision", "recall", "f1"].map((m) => ({
      name: `${k === "risk" ? "Riesgo" : k === "urgent" ? "Urgencia" : "Proveedores"} · ${m === "precision" ? "Precisión" : m === "recall" ? "Recall" : "F1"}`,
      A: A?.quality?.[k]?.[m] == null ? null : A.quality[k][m] * 100,
      B: B?.quality?.[k]?.[m] == null ? null : B.quality[k][m] * 100,
    })),
  );
  const selected = inspect ? pairs.find((x) => x.key === inspect) : null;
  async function start() {
    setBusy(true);
    try {
      await api("/campaigns/" + cid + "/start", { method: "POST" });
      setData(await api("/campaigns/" + cid + "?split=" + sample));
      setConfirmed(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="campaign-page">
      <section className="card comparator-heading">
        <div>
          <h2>Dos perfiles. Las mismas noticias.</h2>
          <p>
            Calidad medida, cobertura y decisiones explorables. Consultar
            gráficos no consume JEV.
          </p>
        </div>
        <nav className="compare-tabs" aria-label="Vistas del modelo">
          {[
            ["compare", "Comparar"],
            ["runs", "Ejecuciones"],
            ["history", "Histórico"],
          ].map(([v, t]) => (
            <button
              key={v}
              className={tab === v ? "selected" : ""}
              aria-pressed={tab === v}
              onClick={() => setTab(v)}
            >
              {t}
            </button>
          ))}
        </nav>
      </section>
      {error && (
        <div role="alert" className="notice error">
          {error}
          <button
            onClick={() => {
              setError("");
              setCid("");
            }}
          >
            Volver a cargar campañas
          </button>
        </div>
      )}
      {tab === "history" ? (
        <details className="card">
          <summary>
            Consultar experimentos anteriores · histórico conservado
          </summary>
          {history}
        </details>
      ) : (
        <>
          <section className="card compare-controls">
            <label>
              Campaña de evaluación
              <select
                aria-label="Campaña de evaluación"
                value={cid}
                onChange={(e) => {
                  setCid(e.target.value);
                  setCell(null);
                  setConfirmed(false);
                }}
              >
                <option value="">Selecciona campaña</option>
                {campaigns.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} · {state(c.state)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Muestra
              <select
                aria-label="Muestra"
                value={sample}
                onChange={(e) => {
                  setSample(e.target.value);
                  setCell(null);
                }}
              >
                {Object.entries(samples).map(([v, t]) => (
                  <option key={v} value={v}>
                    {t}
                  </option>
                ))}
              </select>
            </label>
            {[
              ["A", a, setA],
              ["B", b, setB],
            ].map(([name, v, set]: any) => (
              <label key={name}>
                Perfil {name}
                <select
                  aria-label={"Perfil " + name}
                  value={v}
                  onChange={(e) => {
                    set(e.target.value);
                    setCell(null);
                  }}
                >
                  {[BASE, CAND].map((p) => (
                    <option key={p} value={p}>
                      {label(p)}
                    </option>
                  ))}
                </select>
              </label>
            ))}
          </section>
          {tab === "runs" && (
            <section className="card">
              <h3>Preparar o recuperar una campaña</h3>
              <p>
                Importa el manifiesto privado generado por el ejecutor para
                prepararla sin inferencias, o recupera una campaña ya medida.
                Importar resultados no ejecuta JEV ni los incorpora a datos
                operativos.
              </p>
              {[
                ["Preparar entradas congeladas", false],
                ["Importar resultados medidos", true],
              ].map(([text, measured]) => (
                <label key={String(text)} className="campaign-file">
                  {text}
                  <input
                    disabled={busy}
                    type="file"
                    accept=".json,application/json"
                    onChange={async (e) => {
                      const file = e.target.files?.[0];
                      e.target.value = "";
                      if (!file) return;
                      setBusy(true);
                      try {
                        let r;
                        if (measured) {
                          const form = new FormData();
                          form.append("file", file);
                          r = await api("/campaigns/import", {
                            method: "POST",
                            body: form,
                          });
                        } else {
                          r = await api("/campaigns", {
                            method: "POST",
                            body: await file.text(),
                          });
                        }
                        setCampaigns(await api("/campaigns"));
                        setCid(r.id);
                        setConfirmed(false);
                        setError("");
                      } catch (err) {
                        setError((err as Error).message);
                      } finally {
                        setBusy(false);
                      }
                    }}
                  />
                </label>
              ))}
            </section>
          )}
          {!campaigns.length && (
            <section className="card">
              <h3>Aún no hay campañas congeladas</h3>
              <p>
                Prepara el manifiesto privado con los originales autorizados. El
                histórico conserva las comparaciones anteriores.
              </p>
            </section>
          )}
          {cid && !data && (
            <p role="status">Cargando resultados persistidos…</p>
          )}
          {data && (
            <>
              <section className="card compare-provenance">
                <p>
                  Infraestructura de ejecución:{" "}
                  {data.freeze.infrastructure?.service || "No registrada"}.
                  Importar resultados conserva su entorno y sus tiempos
                  originales.
                </p>
                <strong>
                  {state(data.state)} · {A?.completed || 0}/{A?.total || 0} A y{" "}
                  {B?.completed || 0}/{B?.total || 0} B completados
                </strong>
                <p>
                  {samples[sample]} · {date(data.started_at || data.created_at)}{" "}
                  · Commit de congelación{" "}
                  <code>{data.freeze.created_commit?.slice(0, 7)}</code>
                </p>
                <p>
                  {["test", "liveday"].includes(sample)
                    ? "No disponible: sin etiquetas. Los acuerdos entre perfiles no miden exactitud."
                    : "Training y validation ya inspeccionados: comparación descriptiva, no validación independiente."}{" "}
                  Las revisadas están incluidas en las métricas. Los fallos
                  permanecen fuera de decisiones, con su denominador visible.
                </p>
                <details>
                  <summary>
                    Versiones completas, entrada congelada e infraestructura
                  </summary>
                  <pre>
                    {JSON.stringify(
                      {
                        versions: data.freeze.versions,
                        manifest: data.freeze.manifest,
                        hash: data.freeze.hash,
                        infrastructure: data.freeze.infrastructure,
                        concurrency: data.freeze.concurrency,
                        order: data.freeze.order,
                        request_estimate: data.freeze.request_estimate,
                      },
                      null,
                      2,
                    )}
                  </pre>
                </details>
                <a
                  className="text-link"
                  href={"/api/campaigns/" + cid + "/export"}
                  download
                >
                  Descargar campaña completa JSON · privado
                </a>
              </section>
              {a === b && (
                <div className="notice warning">
                  Ambos selectores contienen el mismo perfil; no es una
                  comparación entre versiones.
                </div>
              )}
              {tab === "runs" ? (
                <section className="card">
                  <h3>Ejecución explícita</h3>
                  <p>
                    {data.freeze.expected_complete_analyses ?? "—"} análisis
                    completos previstos para esta campaña; las peticiones
                    dependen de las etapas, no equivalen a noticias. Caché
                    histórica desactivada exclusivamente aquí; una reanudación
                    conserva resultados válidos de esta campaña.
                  </p>
                  <p>
                    Estado global: {JSON.stringify(data.progress)}. RSS
                    periódico de pago desactivado. Campaña aislada de alertas,
                    acciones, incidentes y decisiones humanas.
                  </p>
                  <p>
                    Tiempo end-to-end de campaña:{" "}
                    {data.elapsed_seconds == null
                      ? "En curso / no medido"
                      : number(data.elapsed_seconds) + " s"}
                    . Desde encolado hasta resultados persistidos y exportación
                    JSON disponible; no renueva A20 ni mide exportación Excel
                    operativa.
                  </p>
                  {["prepared", "running"].includes(data.state) && (
                    <>
                      <label className="check-label">
                        <input
                          type="checkbox"
                          checked={confirmed}
                          onChange={(e) => setConfirmed(e.target.checked)}
                        />
                        Confirmo iniciar o reanudar esta campaña congelada.
                        Máximo técnico:{" "}
                        {
                          data.freeze.request_estimate
                            .max_http_attempts_including_retries
                        }{" "}
                        peticiones incluidos reintentos.
                      </label>
                      <button
                        className="button primary"
                        disabled={!confirmed || busy}
                        onClick={start}
                      >
                        {busy
                          ? "Registrando…"
                          : data.state === "running"
                            ? "Reanudar pendientes"
                            : "Iniciar evaluación con llamadas nuevas"}
                      </button>
                    </>
                  )}
                  {data.state === "paused" && (
                    <>
                      <p className="notice warning">
                        Pausada por autenticación o contrato. Examina el error
                        antes de continuar. Las entradas fallidas se conservan;
                        no se repetirán para obtener otra respuesta.
                      </p>
                      <label>
                        Diagnóstico y motivo de reanudación
                        <textarea
                          value={diagnosis}
                          onChange={(e) => setDiagnosis(e.target.value)}
                        />
                      </label>
                      <button
                        className="button"
                        disabled={diagnosis.trim().length < 15 || busy}
                        onClick={async () => {
                          setBusy(true);
                          try {
                            await api("/campaigns/" + cid + "/diagnose", {
                              method: "POST",
                              body: JSON.stringify({ note: diagnosis }),
                            });
                            setData(
                              await api(
                                "/campaigns/" + cid + "?split=" + sample,
                              ),
                            );
                            setDiagnosis("");
                          } catch (e) {
                            setError((e as Error).message);
                          } finally {
                            setBusy(false);
                          }
                        }}
                      >
                        Registrar diagnóstico · no reintenta casos fallidos
                      </button>
                    </>
                  )}
                </section>
              ) : (
                <>
                  <div className="comparison-summary">
                    {[
                      [a, A],
                      [b, B],
                    ].map(([p, s]: any) => (
                      <section className="card" key={p}>
                        <h3>{label(p)}</h3>
                        <div className="comparison-numbers">
                          <div>
                            <small>Cobertura automática</small>
                            <strong>{pct(s?.automatic_rate)}</strong>
                            <span>
                              {s?.automatic}/{s?.total} entradas
                            </span>
                          </div>
                          <div>
                            <small>Revisión</small>
                            <strong>{s?.review}</strong>
                            <span>
                              {s?.review}/{s?.total} entradas
                            </span>
                          </div>
                          <div>
                            <small>Errores entre automáticas</small>
                            <strong>
                              {s?.automatic_errors == null
                                ? "Sin referencia"
                                : `${s.automatic_errors}/${s.automatic_labelled}`}
                            </strong>
                            <span>
                              Automáticas con referencia:{" "}
                              {s?.automatic_labelled}/{s?.automatic}. Riesgo,
                              urgencia y conjunto de proveedores
                            </span>
                          </div>
                        </div>
                        <p>
                          Completitud {s?.completed}/{s?.total} · {s?.errors}{" "}
                          errores · {s?.pending} pendientes.
                        </p>
                        <p>
                          Automáticos etiquetados: positivos{" "}
                          {s?.automatic_positive.n} (
                          {s?.automatic_positive.errors} errores); negativos{" "}
                          {s?.automatic_negative.n} (
                          {s?.automatic_negative.errors} errores). Riesgos
                          correctos {s?.automatic_risks}; urgencias correctas{" "}
                          {s?.automatic_urgencies}.
                        </p>
                      </section>
                    ))}
                  </div>
                  <section className="card">
                    <h3 id="comparison-quality" tabIndex={-1}>
                      Calidad por decisión
                    </h3>
                    <p className="small-note">
                      Una métrica no calculable no equivale a cero: precisión
                      requiere predicciones positivas; recall requiere positivos
                      de referencia; F1 requiere algún positivo real o predicho.
                    </p>
                    <p>
                      Escala común 0–100%. A y B: {A.labelled_completed} y{" "}
                      {B.labelled_completed} predicciones con referencia
                      completadas. Cobertura no es precisión.
                    </p>
                    {A.quality || B.quality ? (
                      <>
                        <div
                          className="compare-chart"
                          role="img"
                          aria-label="Barras agrupadas de precisión, recall y F1; valores exactos en la tabla siguiente"
                        >
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart
                              data={chart}
                              layout="vertical"
                              margin={{ left: 5, right: 22 }}
                              accessibilityLayer
                            >
                              <CartesianGrid
                                horizontal={false}
                                strokeDasharray="3 3"
                              />
                              <XAxis type="number" domain={[0, 100]} unit="%" />
                              <YAxis
                                type="category"
                                dataKey="name"
                                width={138}
                                tick={{ fontSize: 11 }}
                              />
                              <Tooltip
                                formatter={(v: any) => number(v) + "%"}
                              />
                              <Legend />
                              <Bar
                                name={"A · " + label(a)}
                                dataKey="A"
                                fill="#635bff"
                                isAnimationActive={false}
                              />
                              <Bar
                                name={"B · " + label(b)}
                                dataKey="B"
                                fill="#0891b2"
                                isAnimationActive={false}
                              />
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                        <div className="table-wrap">
                          <table>
                            <caption>
                              Valores exactos y diferencias B−A en puntos
                              porcentuales
                            </caption>
                            <thead>
                              <tr>
                                <th>Decisión</th>
                                <th>Métrica</th>
                                <th>A</th>
                                <th>B</th>
                                <th>Diferencia</th>
                              </tr>
                            </thead>
                            <tbody>
                              {["risk", "urgent", "suppliers"].flatMap((k) =>
                                ["precision", "recall", "f1"].map((m) => (
                                  <tr key={k + m}>
                                    <th>
                                      {k === "risk"
                                        ? "Riesgo"
                                        : k === "urgent"
                                          ? "Urgencia"
                                          : "Proveedores"}
                                    </th>
                                    <td>{m}</td>
                                    <td>{pct(A.quality?.[k]?.[m])}</td>
                                    <td>{pct(B.quality?.[k]?.[m])}</td>
                                    <td>
                                      {diff(
                                        A.quality?.[k]?.[m],
                                        B.quality?.[k]?.[m],
                                      )}
                                    </td>
                                  </tr>
                                )),
                              )}
                            </tbody>
                          </table>
                        </div>
                        <p>
                          Asociaciones micro TP/FP/FN: A{" "}
                          {A.quality?.suppliers.tp}/{A.quality?.suppliers.fp}/
                          {A.quality?.suppliers.fn}; B {B.quality?.suppliers.tp}
                          /{B.quality?.suppliers.fp}/{B.quality?.suppliers.fn}.
                          Conjuntos exactos: A {A.quality?.suppliers.exact}/
                          {A.quality?.n}; B {B.quality?.suppliers.exact}/
                          {B.quality?.n}.
                        </p>
                      </>
                    ) : (
                      <p className="notice">{A.quality_limit}</p>
                    )}
                  </section>
                  <div className="confusion-grid">
                    {[
                      [a, A],
                      [b, B],
                    ].flatMap(([p, s]: any) =>
                      ["risk", "urgent"].map((k) => (
                        <section className="card" key={p + k}>
                          <h3>
                            {p === a ? "A" : "B"} ·{" "}
                            {k === "risk" ? "Riesgo" : "Urgencia"}
                          </h3>
                          {s.quality ? (
                            <>
                              <p>
                                {s.quality[k].n} noticias · referencia en filas,
                                predicción en columnas
                              </p>
                              <table className="interactive-confusion">
                                <thead>
                                  <tr>
                                    <th>Referencia</th>
                                    <th>Pred. sí</th>
                                    <th>Pred. no</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {[
                                    ["Sí", "tp", "fn"],
                                    ["No", "fp", "tn"],
                                  ].map(([t, ...cells]) => (
                                    <tr key={t}>
                                      <th>{t}</th>
                                      {cells.map((kind) => (
                                        <td key={kind}>
                                          <button
                                            onClick={() => {
                                              setCell({
                                                profile: p,
                                                field:
                                                  k === "risk"
                                                    ? "is_risk"
                                                    : "urgent",
                                                kind,
                                              });
                                              setInspect(null);
                                              requestAnimationFrame(() =>
                                                document
                                                  .getElementById(
                                                    "comparison-news",
                                                  )
                                                  ?.focus({
                                                    preventScroll: true,
                                                  }),
                                              );
                                              document
                                                .getElementById(
                                                  "comparison-news",
                                                )
                                                ?.scrollIntoView({
                                                  behavior: matchMedia(
                                                    "(prefers-reduced-motion: reduce)",
                                                  ).matches
                                                    ? "instant"
                                                    : "smooth",
                                                });
                                            }}
                                            aria-label={`${p === a ? "A" : "B"} ${k === "risk" ? "riesgo" : "urgencia"} ${kind}: ${s.quality[k][kind]} noticias`}
                                          >
                                            {s.quality[k][kind]}
                                            <small>
                                              {
                                                (
                                                  {
                                                    tp: "Acierto positivo",
                                                    fn: "Omisión",
                                                    fp: "Falsa alarma",
                                                    tn: "Acierto negativo",
                                                  } as any
                                                )[kind]
                                              }
                                            </small>
                                          </button>
                                        </td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </>
                          ) : (
                            <p>No disponible: sin etiquetas</p>
                          )}
                        </section>
                      )),
                    )}
                  </div>
                </>
              )}
              <section className="card" id="comparison-news" tabIndex={-1}>
                <h3>Acuerdos y diferencias por noticia</h3>
                <div className="compare-controls">
                  <label>
                    Buscar título o News_ID
                    <input value={q} onChange={(e) => setQ(e.target.value)} />
                  </label>
                  <label className="check-label">
                    <input
                      type="checkbox"
                      checked={onlyDiff}
                      onChange={(e) => setOnlyDiff(e.target.checked)}
                    />
                    Solo diferencias
                  </label>
                  {cell && (
                    <button
                      className="button"
                      onClick={() => {
                        setCell(null);
                        const target =
                          document.getElementById("comparison-quality");
                        target?.scrollIntoView();
                        target?.focus({ preventScroll: true });
                      }}
                    >
                      Quitar filtro {cell.kind.toUpperCase()} · volver a
                      comparación
                    </button>
                  )}
                </div>
                <p role="status">
                  {visible.length} noticias de {pairs.length}.{" "}
                  {cell &&
                    `Celda ${cell.kind.toUpperCase()} del perfil ${label(cell.profile)}.`}
                </p>
                <div className="comparison-news">
                  {visible.map((x) => (
                    <article key={x.key}>
                      <div className="section-heading">
                        <div>
                          <small>
                            {x.A?.news_id} · {x.A?.source} · {x.A?.split}
                          </small>
                          <h4>{x.A?.headline}</h4>
                        </div>
                        <button
                          className="text-link"
                          aria-expanded={inspect === x.key}
                          onClick={() =>
                            setInspect(inspect === x.key ? null : x.key)
                          }
                        >
                          Evidencia y prioridad
                        </button>
                      </div>
                      <div className="comparison-predictions">
                        {[
                          ["A", x.A],
                          ["B", x.B],
                        ].map(([name, r]: any) => (
                          <div key={name}>
                            <strong>
                              {name} · {state(r?.state)}
                            </strong>
                            <p>
                              Riesgo {decision(r?.result?.is_risk)} · Urgencia{" "}
                              {decision(r?.result?.urgent)}
                            </p>
                            <p>
                              Proveedores:{" "}
                              {r?.result?.affected_supplier_ids?.join(", ") ||
                                "Sin vínculo"}
                            </p>
                            {r?.reference && (
                              <p>
                                Referencia: riesgo{" "}
                                {decision(r.reference.Is_Risk)} · urgencia{" "}
                                {decision(r.reference.Urgent)} · proveedores{" "}
                                {r.reference.Affected_Supplier_IDs || "ninguno"}
                              </p>
                            )}
                            {r?.supplier_added?.length > 0 && (
                              <p className="metric-warning">
                                Adicionales frente a referencia:{" "}
                                {r.supplier_added.join(", ")}
                              </p>
                            )}
                            {r?.supplier_omitted?.length > 0 && (
                              <p className="metric-warning">
                                Omitidos: {r.supplier_omitted.join(", ")}
                              </p>
                            )}
                            {r?.result?.error && (
                              <p role="status">
                                Error: {r.result.error} · decisiones nulas
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                      {inspect === x.key && (
                        <div className="comparison-evidence">
                          {[
                            ["A", x.A],
                            ["B", x.B],
                          ].map(([name, r]: any) => (
                            <section key={name}>
                              <h4>{name} · evidencia y revisión</h4>
                              {r?.result && (
                                <ReviewGuidance analysis={r.result} />
                              )}
                              {r?.result?.evidence?.map((e: any) => (
                                <blockquote key={e.id}>
                                  <small>
                                    {e.id} · {e.field}
                                  </small>
                                  {e.text}
                                </blockquote>
                              ))}
                              <p>
                                Dudas:{" "}
                                {[
                                  ...(r?.result?.review_reasons || []),
                                  ...(r?.result?.assessments || []).flatMap(
                                    (s: any) =>
                                      (s.review_reasons || []).map(
                                        (v: string) => s.supplier_id + ": " + v,
                                      ),
                                  ),
                                ].join(" · ") || "Sin motivos registrados"}
                              </p>
                              {r?.critical_errors?.length > 0 && (
                                <p>
                                  Errores en cartera:{" "}
                                  {r.critical_errors
                                    .map(
                                      (s: any) =>
                                        `${s.supplier_id} · criticidad ${({ High: "Alta", Medium: "Media", Low: "Baja" } as Record<string, string>)[s.criticality] || s.criticality} · fuente única ${s.single_source === "Y" ? "sí" : "no"}`,
                                    )
                                    .join(" · ")}
                                </p>
                              )}
                            </section>
                          ))}
                          <h4>
                            Prioridad empresarial por unidad noticia–proveedor
                          </h4>
                          <p>
                            Separada de calidad y confianza. Ausente no equivale
                            a cero.
                          </p>
                          {[
                            ...new Set(
                              [
                                ...(x.A?.result?.assessments || []),
                                ...(x.B?.result?.assessments || []),
                              ].map((s: any) => s.supplier_id),
                            ),
                          ].map((sid: any) => {
                            const pa = x.A?.result?.assessments?.find(
                                (s: any) => s.supplier_id === sid,
                              )?.priority,
                              pb = x.B?.result?.assessments?.find(
                                (s: any) => s.supplier_id === sid,
                              )?.priority;
                            return (
                              <p key={sid}>
                                {sid}: A{" "}
                                {pa == null ? "Sin estimación" : number(pa)} · B{" "}
                                {pb == null ? "Sin estimación" : number(pb)} · Δ{" "}
                                {pa == null || pb == null
                                  ? "No comparable"
                                  : number(pb - pa)}
                              </p>
                            );
                          })}
                        </div>
                      )}
                    </article>
                  ))}
                </div>
                {!visible.length && (
                  <p>
                    No hay noticias para estos filtros. Cambia la muestra o
                    quita el filtro de la matriz.
                  </p>
                )}
              </section>
              <section className="card">
                <h3>Tiempo y consumo de esta muestra</h3>
                <p>
                  La suma de tiempos de análisis no equivale al tiempo del lote.
                  Las latencias incluyen ejecución de sus etapas; la espera se
                  calcula desde encolado y los timestamps quedan en la
                  exportación.
                </p>
                <div className="comparison-summary">
                  {[
                    [a, A],
                    [b, B],
                  ].map(([p, s]: any) => (
                    <div key={p}>
                      <h4>{label(p)}</h4>
                      <p>
                        {s.new_requests} peticiones nuevas · {s.cache_stages}{" "}
                        etapas reutilizadas de esta campaña · {s.retries}{" "}
                        reintentos · {s.http_errors} errores HTTP
                      </p>
                      <p>
                        Tokens reportados: entrada{" "}
                        {number(s.tokens.input_tokens)} · salida{" "}
                        {number(s.tokens.output_tokens)}. Caché del proveedor
                        solo si aparece en el registro de uso.
                      </p>
                      <p>
                        Espera en cola observada: p50{" "}
                        {s.queue_wait_seconds?.p50 == null
                          ? "No registrada"
                          : number(s.queue_wait_seconds.p50) + " s"}{" "}
                        · p95{" "}
                        {s.queue_wait_seconds?.p95 == null
                          ? "No registrada"
                          : number(s.queue_wait_seconds.p95) + " s"}
                        . Resultados exportables desde{" "}
                        {date(data.exportable_since)}.
                      </p>
                      <p>
                        Ventana real desde primer inicio hasta último resultado:{" "}
                        {s.elapsed_seconds == null
                          ? "Pendiente"
                          : number(s.elapsed_seconds) + " s"}{" "}
                        · suma de análisis {number(s.analysis_wall_seconds_sum)}{" "}
                        s.
                      </p>
                    </div>
                  ))}
                </div>
              </section>
            </>
          )}
        </>
      )}
    </div>
  );
}
