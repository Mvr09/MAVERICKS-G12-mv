import React, { useEffect, useState, useRef } from "react";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  NavLink,
  Link,
  Routes,
  Route,
  useParams,
  useNavigate,
  useLocation,
} from "react-router-dom";
import {
  Activity,
  LayoutDashboard,
  Building2,
  Package,
  Newspaper,
  Bell,
  Radio,
  Volume2,
  VolumeX,
  ShieldCheck,
  ArrowUpRight,
  Search,
  SlidersHorizontal,
  Upload,
  RefreshCw,
  ChevronRight,
  X,
  Download,
  Copy,
  LogIn,
  CheckCircle2,
  AlertTriangle,
  Clock3,
  Menu,
  LogOut,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { api, setCsrf, date, number } from "./api";
import type {
  Material,
  Supplier,
  Article,
  Source,
  Batch,
  Alert,
} from "./types";
import { audio } from "./audio";
import { setBands, getBands, bandFor } from "./policy";
import "./style.css";

const names: Record<string, string> = {
  training: "Entrenamiento",
  validation: "Validación retenida",
  test: "Test final",
  liveday: "LiveDay",
  pending: "Pendiente",
  superseded: "Versión anterior",
  done: "Analizado",
  review: "Requiere revisión",
  error: "Error",
  ok: "Consultada",
  unchanged: "Sin novedades",
  active: "Activo",
  monitoring: "En seguimiento",
  resolved: "Recuperado",
  positive: "Noticia positiva",
  High: "Alta",
  Medium: "Media",
  Low: "Baja",
};
Object.assign(names, {
  fire_incident: "Incendio o explosión",
  natural_disaster: "Desastre natural",
  labour_strike: "Huelga",
  regulatory_action: "Acción regulatoria",
  export_restriction: "Restricción de exportación",
  financial_distress: "Dificultades financieras",
  quality_recall: "Retirada o calidad",
  logistics_disruption: "Interrupción logística",
  utility_outage: "Interrupción de suministros",
  leadership_change: "Cambio de dirección",
  acquisition: "Adquisición",
  recovery: "Recuperación",
  positive_news: "Noticia positiva",
  other: "Otro evento",
  not_relevant: "Sin vínculo operativo",
  inventory_missing: "Inventario físico no informado",
  criticality_missing: "Criticidad no informada",
  risk_without_operational_evidence:
    "Riesgo propuesto sin evidencia operativa consistente",
  source_text_limited: "Lectura limitada al resumen o a un texto parcial",
  source_text_incomplete:
    "Resumen truncado: falta texto para descartar el impacto con seguridad",
  single_source_missing: "Fuente única no informada",
  category_share_missing: "Gasto en categoría no informado",
  severity_missing: "Severidad no disponible",
  buffer_horizon_missing: "Falta plazo para comparar cobertura",
  evidence_missing: "Falta evidencia suficiente",
  critical_without_urgency: "Prioridad crítica sin urgencia: revisar",
  decision_ambiguous_or_contradictory: "Decisión ambigua o contradictoria",
  recovery_requires_compatible_incident:
    "Recuperación sin un único incidente compatible",
  event_group_ambiguous: "Agrupación de evento ambigua",
  resolved_event_requires_review: "Incidente resuelto: revisar nueva evidencia",
  link_ambiguous: "Vínculo ambiguo",
  severity_confidence_low: "Confianza de severidad insuficiente",
  impact_state_confidence_low: "Estado del impacto incierto",
  evidence_confidence_low: "Selección de evidencia incierta",
  duration_confidence_low: "Duración incierta",
  event_type_confidence_low: "Tipo de evento incierto",
  event_state_confidence_low: "Estado del evento incierto",
});
const label = (s: string) => names[s] || s;
const riskLabel = (value?: string | null) =>
  value === "Y"
    ? "Riesgo detectado"
    : value === "N"
      ? "Sin riesgo detectado"
      : "Riesgo sin determinar";
const urgencyLabel = (value?: string | null) =>
  value === "Y"
    ? "Urgente"
    : value === "N"
      ? "No urgente"
      : "Urgencia sin determinar";
const reviewLabel = (s: string) => {
  const [key, id] = s.split(":");
  return (names[key] || "Revisar decisión del motor") + (id ? " · " + id : "");
};
function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return <span className={"badge " + tone}>{children}</span>;
}
function Score({ value }: { value: number | null }) {
  return (
    <div className={"score " + bandFor(value)}>
      <strong>{number(value)}</strong>
      <small>/ 100</small>
    </div>
  );
}
function Empty({
  title,
  children,
}: {
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="empty">
      <Activity size={30} />
      <h3>{title}</h3>
      <p>
        {children ||
          "Los resultados aparecerán aquí cuando se complete el análisis."}
      </p>
    </div>
  );
}
function Modal({
  title,
  close,
  children,
}: {
  title: string;
  close: () => void;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const prev = document.activeElement as HTMLElement;
    ref.current?.showModal();
    ref.current
      ?.querySelector<HTMLElement>("[autofocus],input,textarea")
      ?.focus();
    return () => prev?.focus();
  }, []);
  return (
    <dialog
      ref={ref}
      onCancel={(e) => {
        e.preventDefault();
        close();
      }}
      onClick={(e) => {
        if (e.target === ref.current) close();
      }}
    >
      <header>
        <h2>{title}</h2>
        <button className="icon-button" onClick={close} aria-label="Cerrar">
          <X />
        </button>
      </header>
      {children}
    </dialog>
  );
}
function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [origin, setOrigin] = useState("");
  const effectiveOrigin = location.pathname === "/" ? origin : "";
  const [context, setContext] = useState("exercise"),
    [overview, setOverview] = useState<any>(null),
    [suppliers, setSuppliers] = useState<Supplier[]>([]),
    [articles, setArticles] = useState<Article[]>([]),
    [sources, setSources] = useState<Source[]>([]),
    [batches, setBatches] = useState<Batch[]>([]),
    [alerts, setAlerts] = useState<Alert[]>([]),
    [config, setConfig] = useState<any>({}),
    [presenter, setPresenter] = useState(false),
    [loginOpen, setLoginOpen] = useState(false),
    [password, setPassword] = useState(""),
    [message, setMessage] = useState(""),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [sound, setSound] = useState("Desactivado"),
    [more, setMore] = useState(false),
    [alertFilter, setAlertFilter] = useState("all");
  const scope = context + "|" + effectiveOrigin;
  const activeScope = useRef(scope);
  const cursor = useRef<number | null>(null),
    file = useRef<HTMLInputElement>(null),
    activeContext = useRef(context),
    configRef = useRef<any>({});
  useEffect(() => {
    api("/session")
      .then((s) => {
        setPresenter(s.presenter);
        setCsrf(s.csrf || "");
      })
      .catch((e) => setError(e.message));
    api("/config")
      .then((c) => {
        setBands(c.bands);
        configRef.current = c;
        setConfig(c);
      })
      .catch((e) => setError(e.message));
  }, []);
  const refreshInFlight = useRef(new Set<string>()),
    nextRefreshAt = useRef(0);
  async function refresh(force = false) {
    if (
      refreshInFlight.current.has(scope) ||
      (!force && Date.now() < nextRefreshAt.current)
    )
      return;
    refreshInFlight.current.add(scope);
    try {
      const [o, s, a, f, b, n] = await Promise.all([
        api(
          "/overview?context=" +
            context +
            (effectiveOrigin
              ? "&origin=" + encodeURIComponent(effectiveOrigin)
              : ""),
        ),
        api(
          "/suppliers?context=" +
            context +
            (effectiveOrigin
              ? "&origin=" + encodeURIComponent(effectiveOrigin)
              : ""),
        ),
        api(
          "/articles?context=" +
            context +
            (effectiveOrigin
              ? "&origin=" + encodeURIComponent(effectiveOrigin)
              : ""),
        ),
        api("/sources"),
        api("/batches"),
        api("/alerts?context=" + context),
      ]);
      if (activeScope.current !== scope) return;
      nextRefreshAt.current = 0;
      setOverview(o);
      setSuppliers(s.items);
      setArticles(a);
      setSources(f);
      setBatches(b);
      setAlerts(n.items);
      document.title =
        (n.unread ? `(${n.unread}) ` : "") + "Supplier Risk Radar · Helixa";
      if (
        cursor.current !== null &&
        configRef.current.cooldown_seconds !== undefined
      )
        await audio
          .notify(
            n.items.filter((x: Alert) => x.id > cursor.current!),
            configRef.current.cooldown_seconds,
          )
          .catch(() => setSound("Bloqueado"));
      cursor.current = n.cursor;
    } catch (e) {
      if (activeScope.current === scope) {
        nextRefreshAt.current = Date.now() + 30000;
        setError((e as Error).message);
      }
    } finally {
      refreshInFlight.current.delete(scope);
      if (activeScope.current === scope) setLoading(false);
    }
  }
  useEffect(() => {
    activeContext.current = context;
    activeScope.current = scope;
    nextRefreshAt.current = 0;
    cursor.current = null;
    setOverview(null);
    setSuppliers([]);
    setArticles([]);
    setAlerts([]);
    setLoading(true);
    refresh();
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") refresh();
    }, 3000);
    const focus = () => refresh(true);
    window.addEventListener("focus", focus);
    return () => {
      clearInterval(timer);
      window.removeEventListener("focus", focus);
    };
  }, [scope]);
  async function action(
    fn: () => Promise<any>,
    success = "Operación completada",
  ) {
    try {
      const result = await fn();
      setMessage(success);
      await refresh(true);
      return result;
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function upload(f: File) {
    const data = new FormData();
    data.append("file", f);
    const imported = await action(
      () => api("/imports", { method: "POST", body: data }),
      "Archivo importado. Revisa el lote antes de analizar.",
    );
    if (imported?.batch_id) {
      setContext("exercise");
      setOrigin("batch:" + imported.batch_id);
      navigate("/");
    }
  }
  const shared = { context, presenter, action, refresh };
  const navigation = [
    { to: "/", icon: LayoutDashboard, text: "Resumen" },
    { to: "/proveedores", icon: Building2, text: "Proveedores" },
    { to: "/materiales", icon: Package, text: "Materiales" },
    { to: "/noticias", icon: Newspaper, text: "Noticias" },
    { to: "/alertas", icon: Bell, text: "Alertas" },
    { to: "/fuentes", icon: Radio, text: "Fuentes" },
    { to: "/analitica", icon: Activity, text: "Analítica" },
  ];
  return (
    <div className="app">
      <a className="skip" href="#contenido">
        Saltar al contenido
      </a>
      <aside className="sidebar">
        <Link to="/" className="brand">
          <span className="brand-icon">
            <Activity />
          </span>
          <span>
            Supplier Risk<span className="brand-light">Radar</span>
          </span>
        </Link>
        <div className="workspace-label">HELIXA PHARMACEUTICALS</div>
        <nav aria-label="Principal">
          {navigation.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === "/"}>
              <n.icon size={19} />
              {n.text}
              {n.to === "/alertas" &&
                alerts.filter((a) => !a.acknowledged).length > 0 && (
                  <span className="nav-count">
                    {alerts.filter((a) => !a.acknowledged).length}
                  </span>
                )}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <ShieldCheck size={18} />
          <div>
            Cartera simulada<small>Decisiones con evidencia</small>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="context-picker">
            <span className="status-dot" />
            <label className="sr-only" htmlFor="context">
              Contexto
            </label>
            <select
              id="context"
              value={context}
              onChange={(e) => {
                setOrigin("");
                setContext(e.target.value);
              }}
            >
              <option value="exercise">Ejercicio</option>
              <option value="rss">Noticias reales</option>
            </select>
          </div>
          <div className="topbar-actions">
            <span className="public-tag">
              {presenter ? "Presentador" : "Vista pública"}
            </span>
            <button
              className="icon-button mobile-sound"
              aria-label="Activar sonido"
              onClick={() =>
                audio
                  .activate()
                  .then(() => setSound("Activado"))
                  .catch(() => setSound("Bloqueado"))
              }
            >
              <Volume2 size={19} />
            </button>
            <button
              className="button small"
              onClick={() =>
                presenter
                  ? action(
                      () =>
                        api("/session", { method: "DELETE" }).then(() => {
                          setPresenter(false);
                          setCsrf("");
                        }),
                      "Sesión cerrada",
                    )
                  : setLoginOpen(true)
              }
            >
              {presenter ? <LogOut size={16} /> : <LogIn size={16} />}
              <span>{presenter ? "Salir" : "Acceso presentador"}</span>
            </button>
          </div>
        </header>
        <main id="contenido">
          <div className="page-heading">
            <div>
              <div className="eyebrow">INTELIGENCIA DE SUMINISTRO</div>
              <h1>
                Radar de proveedores<span className="heading-dot">.</span>
              </h1>
              <p>
                {context === "rss"
                  ? "Exposición potencial de una cartera simulada a noticias reales."
                  : "Detecta señales, entiende el impacto y prioriza la respuesta."}
              </p>
            </div>
            <div className="heading-actions">
              {presenter && (
                <DemoControl
                  onClean={async (result) => {
                    cursor.current = null;
                    navigate("/");
                    await refresh(true);
                    setMessage(
                      result?.mode === "rerun"
                        ? `${result.job_ids.length} análisis encolados; los resultados aparecerán conforme terminen.`
                        : "Selección borrada. Consumo e historial de llamadas conservados.",
                    );
                  }}
                />
              )}
              <input
                ref={file}
                type="file"
                accept=".xlsx"
                className="sr-only"
                aria-label="Archivo Excel"
                onChange={(e) => {
                  if (e.target.files?.[0]) upload(e.target.files[0]);
                  e.target.value = "";
                }}
              />
              <button
                className="button primary"
                onClick={() =>
                  presenter ? file.current?.click() : setLoginOpen(true)
                }
              >
                <Upload size={17} />
                Importar Excel
              </button>
            </div>
          </div>
          {config.fixtures && (
            <div className="notice warning">
              Demostración de interfaz · MOCKS IDENTIFICADOS. Estos resultados
              no proceden de JEV real.
            </div>
          )}
          {error && (
            <div className="notice error" role="alert">
              <AlertTriangle size={20} />
              <span>{error}</span>
              <button
                className="icon-button"
                onClick={() => setError("")}
                aria-label="Cerrar error"
              >
                <X size={17} />
              </button>
            </div>
          )}
          {message && (
            <div className="notice success" role="status">
              <CheckCircle2 size={20} />
              <span>{message}</span>
              <button
                className="icon-button"
                onClick={() => setMessage("")}
                aria-label="Cerrar aviso"
              >
                <X size={17} />
              </button>
            </div>
          )}
          {config.engine_configured === false && (
            <div className="notice warning">
              Motor sin configurar. El catálogo sigue disponible; las noticias
              permanecen pendientes.
            </div>
          )}
          <div className="sound-bar">
            <div>
              <Volume2 size={16} />
              <span>
                Sonido: <strong>{sound}</strong>
              </span>
            </div>
            <div className="sound-actions">
              <button
                onClick={() =>
                  audio
                    .activate()
                    .then(() => setSound("Activado"))
                    .catch(() => setSound("Bloqueado"))
                }
              >
                Activar sonido
              </button>
              <button
                onClick={() =>
                  audio
                    .play()
                    .catch(() =>
                      setSound("Bloqueado: activa primero el sonido"),
                    )
                }
              >
                Probar alarma
              </button>
              <button
                onClick={() => {
                  audio.mute();
                  setSound("Silenciado");
                }}
              >
                <VolumeX size={14} />
                Silenciar
              </button>
            </div>
          </div>
          {loading && !overview ? (
            <div className="loading" role="status">
              Cargando datos del radar…
            </div>
          ) : (
            <Routes>
              <Route
                path="/"
                element={
                  <>
                    <section className="card origin-filter">
                      <label htmlFor="summary-origin">
                        Origen de los datos
                      </label>
                      <select
                        id="summary-origin"
                        value={origin}
                        onChange={(e) => {
                          const value = e.target.value;
                          setOrigin(value);
                          if (value)
                            setContext(
                              value.startsWith("rss:") ? "rss" : "exercise",
                            );
                        }}
                      >
                        <option value="">
                          Todos ·{" "}
                          {context === "rss" ? "Noticias reales" : "Ejercicio"}
                        </option>
                        <optgroup label="Archivos del ejercicio">
                          {batches.map((b) => (
                            <option key={b.id} value={"batch:" + b.id}>
                              {b.origin_label || b.filename || label(b.split)}
                            </option>
                          ))}
                        </optgroup>
                        <optgroup label="Fuentes RSS">
                          {sources.map((s) => (
                            <option key={s.id} value={"rss:" + s.id}>
                              {s.name}
                            </option>
                          ))}
                        </optgroup>
                      </select>
                      <small>
                        Indicadores, ranking y señales del origen seleccionado.
                        Los incidentes recuperados permanecen cerrados.
                      </small>
                    </section>
                    <div className="kpis">
                      <Kpi
                        label="Proveedores urgentes"
                        value={overview?.urgent_suppliers}
                        note={`de ${suppliers.length} proveedores en cartera`}
                        icon={<Bell />}
                        tone="purple"
                      />
                      <Kpi
                        label="Incidentes activos"
                        value={overview?.active_incidents}
                        note="Eventos distintos · sin sumar titulares"
                        icon={<Activity />}
                        tone="cyan"
                      />
                      <Kpi
                        label="Noticias analizadas"
                        value={overview?.processed}
                        note={`de ${overview?.received || 0} recibidas · ${overview?.pending || 0} pendientes`}
                        icon={<Newspaper />}
                        tone="blue"
                      />
                      <Kpi
                        label="Fuentes consultadas"
                        value={`${overview?.healthy_sources || 0} / 6`}
                        note="RSS · estado global de la última consulta"
                        icon={<Radio />}
                        tone="green"
                      />
                    </div>
                    <div className="dashboard-grid">
                      <section className="card ranking-panel">
                        <div className="section-heading">
                          <div>
                            <h2>Prioridad de proveedores</h2>
                            <p>Máximo de incidentes activos por proveedor</p>
                          </div>
                          <Badge>{suppliers.length} proveedores</Badge>
                        </div>
                        <Ranking suppliers={suppliers} context={context} />
                        <Link className="card-footer-link" to="/proveedores">
                          Explorar la cartera completa{" "}
                          <ChevronRight size={16} />
                        </Link>
                      </section>
                      <div className="side-column">
                        <section className="card">
                          <div className="section-heading">
                            <h2>Últimas señales</h2>
                            <Link
                              to="/noticias"
                              aria-label="Ver todas las noticias"
                            >
                              <ArrowUpRight size={19} />
                            </Link>
                          </div>
                          <NewsList articles={articles.slice(0, 4)} />
                        </section>
                        <section className="card sources-mini">
                          <div className="section-heading">
                            <h2>Estado de fuentes</h2>
                            <Link to="/fuentes">Ver todas</Link>
                          </div>
                          {sources.map((s) => (
                            <div className="source-mini" key={s.id}>
                              <span
                                className={
                                  "status-dot " +
                                  (s.status === "error"
                                    ? "danger"
                                    : s.last_success_at
                                      ? ""
                                      : "unknown")
                                }
                              />
                              <span>{s.name}</span>
                              <small>{label(s.status)}</small>
                            </div>
                          ))}
                        </section>
                      </div>
                    </div>
                    {context === "exercise" && (
                      <Batches
                        batches={
                          origin.startsWith("batch:")
                            ? batches.filter((b) => "batch:" + b.id === origin)
                            : batches
                        }
                        {...shared}
                      />
                    )}
                  </>
                }
              />
              <Route
                path="/proveedores"
                element={
                  <section className="card">
                    <div className="section-heading">
                      <div>
                        <h2>Cartera de proveedores</h2>
                        <p>Identidad, exposición y alternativas conocidas</p>
                      </div>
                    </div>
                    <Ranking suppliers={suppliers} context={context} full />
                  </section>
                }
              />
              <Route
                path="/proveedores/:id"
                element={<SupplierDetail {...shared} />}
              />
              <Route
                path="/materiales"
                element={<MaterialsPage suppliers={suppliers} />}
              />
              <Route path="/materiales/:id" element={<MaterialDetail />} />
              <Route
                path="/noticias"
                element={<NewsPage articles={articles} />}
              />
              <Route
                path="/noticias/:id"
                element={<ArticleDetail {...shared} />}
              />
              <Route
                path="/alertas"
                element={
                  <section className="card">
                    <div className="section-heading">
                      <div>
                        <h2>Centro de alertas</h2>
                        <p>Reconocer una alerta conserva el incidente activo</p>
                      </div>
                      <Badge>
                        {alerts.filter((a) => !a.acknowledged).length} sin leer
                      </Badge>
                    </div>
                    <div className="ranking-toolbar">
                      <select
                        aria-label="Estado de alerta"
                        value={alertFilter}
                        onChange={(e) => setAlertFilter(e.target.value)}
                      >
                        <option value="all">Todas las alertas</option>
                        <option value="new">Sin leer</option>
                        <option value="ack">Reconocidas</option>
                        <option value="resolved">Recuperadas</option>
                      </select>
                    </div>
                    {alerts.length ? (
                      alerts
                        .filter(
                          (a) =>
                            alertFilter === "all" ||
                            (alertFilter === "new" && !a.acknowledged) ||
                            (alertFilter === "ack" && a.acknowledged) ||
                            (alertFilter === "resolved" &&
                              a.state === "resolved"),
                        )
                        .slice()
                        .reverse()
                        .map((a) => (
                          <article className="alert-item" key={a.id}>
                            <div className="alert-icon">
                              <Bell size={20} />
                            </div>
                            <div>
                              <div className="inline">
                                <Badge
                                  tone={
                                    a.state === "resolved"
                                      ? "success"
                                      : a.needs_review
                                        ? "warning"
                                        : "danger"
                                  }
                                >
                                  {a.state === "resolved"
                                    ? "Recuperada"
                                    : a.needs_review
                                      ? "Requiere revisión"
                                      : "Urgente"}
                                </Badge>
                                <small>{date(a.created_at)}</small>
                              </div>
                              <h3>
                                <Link to={"/proveedores/" + a.supplier_id}>
                                  {a.supplier_name}
                                </Link>
                              </h3>
                              <p>{a.headline}</p>
                              <small>
                                Prioridad {number(a.priority)} ·{" "}
                                {a.sound_eligible
                                  ? "Elegible para sonido"
                                  : "Solo aviso visual"}
                              </small>
                              <div className="inline">
                                <button
                                  className="button small"
                                  disabled={!presenter || a.acknowledged}
                                  onClick={() =>
                                    action(() =>
                                      api(`/alerts/${a.id}/ack`, {
                                        method: "POST",
                                      }),
                                    )
                                  }
                                >
                                  {a.acknowledged ? "Reconocida" : "Reconocer"}
                                </button>
                                <Link
                                  className="text-link"
                                  to={"/proveedores/" + a.supplier_id}
                                >
                                  Ver evidencia →
                                </Link>
                              </div>
                            </div>
                          </article>
                        ))
                    ) : (
                      <Empty title="Sin alertas registradas">
                        Las noticias pendientes no se consideran libres de
                        riesgo.
                      </Empty>
                    )}
                  </section>
                }
              />
              <Route
                path="/fuentes"
                element={
                  <SourcesPage
                    sources={sources}
                    onRss={() => setContext("rss")}
                    config={config}
                    {...shared}
                  />
                }
              />
              <Route
                path="/analitica"
                element={
                  <Analytics
                    overview={overview}
                    suppliers={suppliers}
                    sources={sources}
                    batches={batches}
                    {...shared}
                  />
                }
              />
              <Route
                path="*"
                element={
                  <Empty title="Página no encontrada">
                    <Link to="/">Volver al resumen</Link>
                  </Empty>
                }
              />
            </Routes>
          )}
          <footer className="page-footer">
            <span>Helixa Pharmaceuticals · Cartera ficticia</span>
            <span>
              Política {config.policy_version || "1.0.0"} ·{" "}
              {config.model || "jev-1.13.0"}
            </span>
          </footer>
        </main>
      </div>
      <nav className="mobile-nav" aria-label="Navegación móvil">
        {navigation
          .filter((n) => ["/", "/noticias", "/alertas"].includes(n.to))
          .map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === "/"}>
              <n.icon size={21} />
              <span>{n.text}</span>
            </NavLink>
          ))}
        <button onClick={() => setMore(!more)} aria-expanded={more}>
          <Menu size={21} />
          Más
        </button>
      </nav>
      {more && (
        <div className="more-menu">
          {navigation
            .filter((n) =>
              ["/proveedores", "/fuentes", "/analitica"].includes(n.to),
            )
            .map((n) => (
              <Link key={n.to} to={n.to} onClick={() => setMore(false)}>
                <n.icon size={18} />
                {n.text}
              </Link>
            ))}
        </div>
      )}
      {loginOpen && (
        <Modal title="Acceso de presentador" close={() => setLoginOpen(false)}>
          <form
            className="modal-body"
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                const s = await api("/session", {
                  method: "POST",
                  body: JSON.stringify({ password }),
                });
                setCsrf(s.csrf);
                setPresenter(true);
                setLoginOpen(false);
                setPassword("");
                setError("");
              } catch (e) {
                setError((e as Error).message);
                setLoginOpen(false);
              }
            }}
          >
            <p>Acceso a cargas, análisis, sincronización y borradores.</p>
            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoFocus
            />
            <button className="button primary" type="submit">
              Entrar
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}
function Kpi({
  label: caption,
  value,
  note,
  icon,
  tone,
}: {
  label: string;
  value: any;
  note: string;
  icon: React.ReactNode;
  tone: string;
}) {
  return (
    <div className="kpi card">
      <div className="kpi-top">
        <span>{caption}</span>
        <div className={"kpi-icon " + tone}>{icon}</div>
      </div>
      <div className="kpi-value">{value ?? "—"}</div>
      <small>{note}</small>
    </div>
  );
}
function Ranking({
  suppliers,
  context,
  full = false,
}: {
  suppliers: Supplier[];
  context: string;
  full?: boolean;
}) {
  const [q, setQ] = useState(""),
    [filters, setFilters] = useState(false),
    [category, setCategory] = useState(""),
    [criticality, setCriticality] = useState(""),
    [single, setSingle] = useState(""),
    [urgent, setUrgent] = useState(false),
    [alternate, setAlternate] = useState(""),
    [product, setProduct] = useState("");
  const rows = suppliers.filter(
    (s) =>
      (!q ||
        [s.name, s.supplier_id, s.material, s.country]
          .join(" ")
          .toLowerCase()
          .includes(q.toLowerCase())) &&
      (!category || s.category === category) &&
      (!criticality || s.criticality === criticality) &&
      (!single || s.single_source === single) &&
      (!urgent || s.urgent) &&
      (!alternate || Boolean(s.alternate_id) === (alternate === "Y")) &&
      (!product || s.products.includes(product)),
  );
  return (
    <>
      <div className="ranking-toolbar">
        <div className="search">
          <Search size={17} />
          <input
            aria-label="Buscar proveedor"
            placeholder="Buscar proveedor, material o país…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <button
          className={"button " + (filters ? "selected" : "")}
          onClick={() => setFilters(!filters)}
          aria-expanded={filters}
        >
          <SlidersHorizontal size={16} />
          <span>Filtros</span>
        </button>
      </div>
      {filters && (
        <div className="filters">
          <label>
            Categoría
            <select
              aria-label="Categoría"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="">Todas</option>
              {[...new Set(suppliers.map((s) => s.category))].map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>
          <label>
            Criticidad
            <select
              aria-label="Criticidad"
              value={criticality}
              onChange={(e) => setCriticality(e.target.value)}
            >
              <option value="">Todas</option>
              {["High", "Medium", "Low"].map((c) => (
                <option value={c} key={c}>
                  {label(c)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Fuente única
            <select
              aria-label="Fuente única"
              value={single}
              onChange={(e) => setSingle(e.target.value)}
            >
              <option value="">Todas</option>
              <option value="Y">Sí</option>
              <option value="N">No</option>
            </select>
          </label>
          <label>
            Alternativo aprobado
            <select
              aria-label="Alternativo aprobado"
              value={alternate}
              onChange={(e) => setAlternate(e.target.value)}
            >
              <option value="">Todos</option>
              <option value="Y">Sí</option>
              <option value="N">No</option>
            </select>
          </label>
          <label>
            Producto
            <select
              aria-label="Producto"
              value={product}
              onChange={(e) => setProduct(e.target.value)}
            >
              <option value="">Todos</option>
              {[...new Set(suppliers.flatMap((s) => s.products))].map((p) => (
                <option key={p}>{p}</option>
              ))}
            </select>
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={urgent}
              onChange={(e) => setUrgent(e.target.checked)}
            />
            Solo urgentes
          </label>
          <button
            className="button"
            onClick={() => {
              setQ("");
              setCategory("");
              setCriticality("");
              setSingle("");
              setAlternate("");
              setProduct("");
              setUrgent(false);
            }}
          >
            Limpiar
          </button>
          <button className="button primary" onClick={() => setFilters(false)}>
            Aplicar
          </button>
        </div>
      )}
      <div className="ranking-header">
        <span>Proveedor / material</span>
        <span>Dependencia</span>
        <span>Prioridad</span>
        <span />
      </div>
      <div className="ranking-list">
        {rows.length ? (
          rows.slice(0, full ? 100 : 8).map((s) => (
            <Link
              key={s.supplier_id}
              to={"/proveedores/" + s.supplier_id}
              className="supplier-row"
            >
              <div className="supplier-identity">
                <span className="supplier-avatar">
                  {s.name
                    .split(" ")
                    .map((x) => x[0])
                    .slice(0, 2)
                    .join("")}
                </span>
                <div>
                  <h3>{s.name}</h3>
                  <p>
                    {s.country} <span>·</span> {s.material}
                  </p>
                  <small>
                    {s.latest_evidence
                      ? `Evidencia: ${date(s.latest_evidence)}`
                      : "Pendiente de análisis"}
                  </small>
                </div>
              </div>
              <div className="dependency">
                <Badge tone={s.criticality === "High" ? "purple" : "neutral"}>
                  Criticidad {label(s.criticality).toLowerCase()}
                </Badge>
                {s.single_source === "Y" && <small>Fuente única</small>}
                {s.status === "resolved" && (
                  <Badge tone="success">Recuperado</Badge>
                )}
                {s.status === "positive" && (
                  <Badge tone="success">Sin riesgo activo</Badge>
                )}
                {s.urgent && <Badge tone="danger">Urgente</Badge>}
                {s.needs_review && <Badge tone="warning">Revisión</Badge>}
              </div>
              <Score value={s.priority} />
              <ChevronRight size={17} className="row-arrow" />
              <div className="mobile-row-action">
                <span className="reason-text">{s.reason}</span>
                <span>Ver detalle →</span>
              </div>
            </Link>
          ))
        ) : (
          <Empty
            title={
              suppliers.length
                ? "Sin coincidencias"
                : "Catálogo pendiente de importación"
            }
          >
            Ajusta los filtros o importa el Excel de entrenamiento con acceso de
            presentador.
          </Empty>
        )}
      </div>
      <div className="list-count">
        {Math.min(rows.length, full ? 100 : 8)} de {rows.length} proveedores ·{" "}
        {context === "rss" ? "Exposición potencial" : "Datos del ejercicio"}
      </div>
    </>
  );
}
function NewsList({
  articles,
  onOpen,
}: {
  articles: Article[];
  onOpen?: () => void;
}) {
  return articles.length ? (
    <div className="news-list">
      {articles.map((a) => (
        <article className="news-item" key={a.id}>
          <div className="inline">
            <small className="source-label">{a.origin_label || a.source}</small>
            <Badge
              tone={
                a.state === "review"
                  ? "warning"
                  : a.state === "error"
                    ? "danger"
                    : "neutral"
              }
            >
              {label(a.state)}
            </Badge>
          </div>
          <h3>
            <Link to={"/noticias/" + a.id} onClick={onOpen}>
              {a.headline}
            </Link>
          </h3>
          <small>
            {date(a.published_date)}
            {a.cached ? " · Resultado cacheado" : ""}
          </small>
        </article>
      ))}
    </div>
  ) : (
    <Empty title="Aún no hay noticias">
      Importa un lote o consulta los RSS desde la vista de presentador.
    </Empty>
  );
}
function NewsPage({ articles }: { articles: Article[] }) {
  const [q, setQ] = useState(""),
    [state, setState] = useState(""),
    [source, setSource] = useState(""),
    [split, setSplit] = useState(""),
    [from, setFrom] = useState(""),
    [to, setTo] = useState(""),
    [event, setEvent] = useState(""),
    [relevant, setRelevant] = useState(false);
  return (
    <section className="card">
      <div className="section-heading">
        <div>
          <h2>Noticias y evidencias</h2>
          <p>Fuente, fecha y estado de cada entrada</p>
        </div>
        <Badge>{articles.length} recibidas</Badge>
      </div>
      <div className="ranking-toolbar">
        <div className="search">
          <Search size={18} />
          <input
            placeholder="Buscar noticias…"
            aria-label="Buscar noticias"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <select
          aria-label="Estado de análisis"
          value={state}
          onChange={(e) => setState(e.target.value)}
        >
          <option value="">Todos los estados</option>
          {["pending", "done", "review", "error"].map((s) => (
            <option key={s} value={s}>
              {label(s)}
            </option>
          ))}
        </select>
        <select
          aria-label="Fuente"
          value={source}
          onChange={(e) => setSource(e.target.value)}
        >
          <option value="">Todas las fuentes</option>
          {[...new Set(articles.map((a) => a.source))].map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </div>
      <div className="ranking-toolbar news-filters">
        <label>
          Lote de origen
          <select
            aria-label="Lote de origen"
            value={split}
            onChange={(e) => setSplit(e.target.value)}
          >
            <option value="">Todos los lotes</option>
            {[...new Set(articles.map((a) => a.split).filter(Boolean))].map(
              (s) => (
                <option key={s} value={s}>
                  {s === "rss" ? "Noticias reales" : label(s!)}
                </option>
              ),
            )}
          </select>
        </label>
        <label>
          Desde
          <input
            aria-label="Fecha desde"
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
          />
        </label>
        <label>
          Hasta
          <input
            aria-label="Fecha hasta"
            type="date"
            value={to}
            onChange={(e) => setTo(e.target.value)}
          />
        </label>
        <label>
          Evento
          <select
            aria-label="Tipo de evento"
            value={event}
            onChange={(e) => setEvent(e.target.value)}
          >
            <option value="">Todos los eventos</option>
            {[
              ...new Set(
                articles.flatMap((a) =>
                  a.analysis?.event_type ? [a.analysis.event_type] : [],
                ),
              ),
            ].map((v) => (
              <option key={v} value={v}>
                {label(v)}
              </option>
            ))}
          </select>
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={relevant}
            onChange={(e) => setRelevant(e.target.checked)}
          />
          Solo con proveedores identificados
        </label>
        <button
          className="button"
          onClick={() => {
            setQ("");
            setState("");
            setSource("");
            setSplit("");
            setFrom("");
            setTo("");
            setEvent("");
            setRelevant(false);
          }}
        >
          Limpiar
        </button>
      </div>
      <NewsList
        articles={articles.filter(
          (a) =>
            (!q ||
              (a.headline + " " + a.summary)
                .toLowerCase()
                .includes(q.toLowerCase())) &&
            (!state || a.state === state) &&
            (!source || a.source === source) &&
            (!split || a.split === split) &&
            (!from || a.published_date >= from) &&
            (!to || a.published_date.slice(0, 10) <= to) &&
            (!event || a.analysis?.event_type === event) &&
            (!relevant || Boolean(a.analysis?.affected_supplier_ids.length)),
        )}
      />
    </section>
  );
}
function ArticleDetail({ context, presenter, action }: any) {
  const { id } = useParams();
  const [a, setA] = useState<Article | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setA(null);
    setError("");
    async function refreshArticle() {
      try {
        const value = await api("/articles/" + id);
        if (active) {
          setA(value);
          setError("");
        }
      } catch (e) {
        if (active) setError((e as Error).message);
      }
    }
    refreshArticle();
    const timer = window.setInterval(refreshArticle, 3000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [id, context]);
  if (!a)
    return (
      <div role={error ? "alert" : "status"}>
        {error || "Cargando noticia…"}
      </div>
    );
  return (
    <section className="card detail-card">
      <Link className="text-link" to="/noticias">
        ← Noticias
      </Link>
      <div className="inline">
        <Badge>{label(a.state)}</Badge>
        <span>
          {a.source} · {date(a.published_date)}
        </span>
      </div>
      <h2>{a.headline}</h2>
      <small>Origen: {a.origin_label || a.source}</small>
      <p className="article-summary">{a.summary}</p>
      {a.split === "rss" && (
        <div className="notice">
          <span>
            {a.analysis?.source_reading?.status === "public_text"
              ? "Texto público ampliado"
              : a.analysis?.source_reading?.status === "partial"
                ? "Texto público parcial"
                : a.analysis?.source_reading
                  ? "Solo resumen RSS · no se pudo ampliar la lectura"
                  : a.analysis
                    ? "Análisis anterior: solo resumen RSS"
                    : "Lectura ampliada pendiente de análisis"}
            {a.analysis?.source_reading?.checked_at && (
              <>
                {" "}
                · Consulta del texto:{" "}
                {date(a.analysis.source_reading.checked_at)}
              </>
            )}
            {a.analysis && <> · Preguntas: {a.analysis.question_version}</>}
          </span>
        </div>
      )}
      {a.analysis?.context_notes?.length ? (
        <details>
          <summary>
            Observaciones del contexto ({a.analysis.context_notes.length})
          </summary>
          <p>
            Estas dudas descriptivas no cambian por sí solas la decisión ni
            autorizan una alarma.
          </p>
          {a.analysis.context_notes.map((r) => (
            <p key={r}>{reviewLabel(r)}</p>
          ))}
        </details>
      ) : null}
      {a.analysis?.analysis_status === "error" && (
        <div className="notice error">
          <span>
            Análisis sin decisión: {a.analysis.error}. El presentador debe
            diagnosticar el fallo antes de reintentar.
          </span>
        </div>
      )}
      {presenter && (
        <div className="inline">
          <DemoControl
            buttonLabel="Reanalizar noticia"
            initialSelection={["article:" + a.id]}
            initialMode="rerun"
            onClean={async () => {
              setA(await api("/articles/" + id));
            }}
          />
        </div>
      )}
      {a.state === "error" && presenter && (
        <RetryAnalysis article={a} action={action} />
      )}

      {presenter && <AnalysisHistory article={a} />}
      {presenter && a.split === "rss" && <ComparisonControl article={a} />}
      {a.url && /^https?:\/\//.test(a.url) && (
        <a className="button" href={a.url} target="_blank" rel="noreferrer">
          Abrir fuente original <ArrowUpRight size={16} />
        </a>
      )}
      {a.analysis ? (
        <>
          {a.analysis.review_reasons.map((r) => (
            <p className="notice warning" key={r}>
              {reviewLabel(r)}
            </p>
          ))}
          <h3>Evidencia literal</h3>
          {a.analysis.evidence
            .filter((e) =>
              a.analysis!.assessments.some((s) =>
                s.evidence_ids.includes(e.id),
              ),
            )
            .map((e) => (
              <blockquote key={e.id}>{e.text}</blockquote>
            ))}
          <h3>Evaluación por proveedor</h3>
          {a.analysis.assessments.map((s) => (
            <div className="assessment" key={s.supplier_id}>
              <Link to={"/proveedores/" + s.supplier_id}>{s.supplier_id}</Link>
              <Score value={s.priority} />
              <span>
                Vínculo {number(s.p_link * 100)}% · {riskLabel(s.is_risk)} ·{" "}
                {urgencyLabel(s.urgent)}
              </span>
              {s.p_identity != null && (
                <small>
                  Identidad explícita: {number(s.p_identity * 100)}% ·
                  Exposición potencial: {number((s.p_exposure || 0) * 100)}%.
                  Cartera simulada; no confirma embarques de Helixa.
                </small>
              )}
              {s.needs_review && (
                <Badge tone="warning">Requiere revisión</Badge>
              )}
              {s.review_reasons.map((r) => (
                <small key={r}>{reviewLabel(r)}</small>
              ))}
            </div>
          ))}
          <small>
            Modelo: {a.analysis.model_id} · Versión de noticia {a.version} ·{" "}
            {a.cached
              ? "Resultado cacheado"
              : a.cache_stages?.length
                ? "Caché parcial y peticiones nuevas"
                : "Petición procesada"}
          </small>
        </>
      ) : (
        <div className="notice warning">
          Análisis pendiente. No se ha emitido una decisión de riesgo.
        </div>
      )}
    </section>
  );
}
function RetryAnalysis({ article, action }: any) {
  const [open, setOpen] = useState(false),
    [reason, setReason] = useState("");
  return (
    <>
      <button className="button" onClick={() => setOpen(true)}>
        Reintentar tras diagnóstico
      </button>
      {open && (
        <Modal
          title="Diagnóstico antes de reintentar"
          close={() => setOpen(false)}
        >
          <form
            className="modal-body"
            onSubmit={async (e) => {
              e.preventDefault();
              await action(
                () =>
                  api("/articles/" + article.id + "/retry", {
                    method: "POST",
                    body: JSON.stringify({ reason }),
                  }),
                "Reintento encolado.",
              );
              setOpen(false);
            }}
          >
            <p>
              Indica la corrección realizada sin incluir credenciales. Los
              intentos agotados no se reinician.
            </p>
            <label htmlFor="diagnostic">Diagnóstico y corrección</label>
            <textarea
              id="diagnostic"
              required
              minLength={12}
              maxLength={2000}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <button className="button primary" type="submit">
              Registrar y reintentar
            </button>
          </form>
        </Modal>
      )}
    </>
  );
}
function SupplierDetail({ context, presenter, action, refresh }: any) {
  const { id } = useParams();
  const [s, setS] = useState<Supplier | null>(null),
    [draft, setDraft] = useState<{ id: string; text: string } | null>(null),
    [error, setError] = useState(""),
    [resolution, setResolution] = useState<string | null>(null),
    [reason, setReason] = useState("");
  useEffect(() => {
    api("/suppliers/" + id + "?context=" + context)
      .then(setS)
      .catch((e) => setError(e.message));
  }, [id, context]);
  async function create(kind: string, iid: string) {
    try {
      setDraft(
        await api("/drafts", {
          method: "POST",
          body: JSON.stringify({ supplier_id: id, incident_id: iid, kind }),
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    }
  }
  if (!s) return <div role="status">{error || "Cargando proveedor…"}</div>;
  return (
    <>
      <Link className="text-link" to="/proveedores">
        ← Volver a proveedores
      </Link>
      <section className="card detail-card">
        <div className="supplier-detail-heading">
          <div>
            <div className="eyebrow">
              {s.supplier_id} · {s.category}
            </div>
            <h2>{s.name}</h2>
            <p>
              {s.city}, {s.country} · {s.material}
            </p>
            <div className="inline">
              <Badge tone="purple">Criticidad {label(s.criticality)}</Badge>
              <Badge>
                {s.single_source === "Y" ? "Fuente única" : "Varias fuentes"}
              </Badge>
              {s.urgent && <Badge tone="danger">Urgente</Badge>}
            </div>
          </div>
          <div>
            <Score value={s.priority} />
            <small>Prioridad actual</small>
          </div>
        </div>
        {error && <div className="notice error">{error}</div>}
        <div className="detail-grid">
          <div>
            <h3>Qué ocurrió y qué sabemos</h3>
            {s.incidents.length ? (
              s.incidents.map((i) => (
                <article className="incident-card" key={i.id}>
                  <div className="inline">
                    <Badge
                      tone={
                        i.state === "resolved"
                          ? "success"
                          : i.state === "monitoring"
                            ? "warning"
                            : "danger"
                      }
                    >
                      {label(i.state)}
                    </Badge>
                    <small>{date(i.event_date)}</small>
                  </div>
                  <h4>
                    {i.current_headline ||
                      i.history.findLast((h) => h.headline)?.headline ||
                      label(i.event_type)}
                  </h4>
                  {i.history
                    .filter((h) => h.assessment)
                    .map((h, n) => (
                      <div key={n}>
                        {h.explanation && (
                          <blockquote>{h.explanation}</blockquote>
                        )}
                        <p>
                          {h.assessment?.needs_review
                            ? "Requiere revisión: " +
                              h.assessment.review_reasons
                                .map(reviewLabel)
                                .join(", ")
                            : "Evaluación completada con evidencia."}
                        </p>
                        <p>
                          Vínculo {number((h.assessment?.p_link || 0) * 100)}% ·
                          Severidad {number(h.assessment?.severity)} / 10
                        </p>
                        <div className="factor-grid">
                          {Object.entries(
                            h.assessment?.factor_values || {},
                          ).map(([k, v]) => (
                            <div key={k}>
                              <small>
                                {
                                  {
                                    C: "Criticidad",
                                    U: "Fuente única",
                                    B: "Presión de cobertura",
                                    G: "Gasto en categoría",
                                  }[k]
                                }
                              </small>
                              <strong>{number(v)}</strong>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  {i.stale && (
                    <Badge tone="warning">Requiere actualización</Badge>
                  )}
                  {i.history
                    .filter((h) => h.reason)
                    .map((h, n) => (
                      <p key={n}>Resolución registrada: {h.reason}</p>
                    ))}
                  <small>
                    Máximo histórico: {number(i.historical_priority)} / 100
                  </small>
                  <div className="inline">
                    <button
                      className="button primary"
                      disabled={!presenter}
                      onClick={() => create("supplier", i.id)}
                    >
                      Consultar proveedor
                    </button>
                    <button
                      className="button"
                      disabled={!presenter || !s.alternate_id}
                      onClick={() => create("alternate", i.id)}
                    >
                      Consultar alternativo
                    </button>
                    {i.state !== "resolved" && (
                      <button
                        className="button"
                        disabled={!presenter}
                        onClick={() => {
                          setReason("");
                          setResolution(i.id);
                        }}
                      >
                        Resolver con motivo
                      </button>
                    )}
                  </div>
                </article>
              ))
            ) : (
              <Empty title="Sin incidentes analizados">
                La ausencia de análisis no implica ausencia de riesgo.
              </Empty>
            )}
            <h3>Noticias relacionadas</h3>
            <NewsList articles={s.articles || []} />
          </div>
          <aside>
            <div className="fact-box">
              <h3>Contexto de suministro</h3>
              <dl>
                <dt>Cobertura de inventario</dt>
                <dd>
                  {["Logistics", "Services"].includes(s.category)
                    ? "Inventario no aplicable"
                    : s.inventory_days == null
                      ? "Inventario no informado"
                      : `${s.inventory_days} días`}
                </dd>
                <dt>Lead time</dt>
                <dd>
                  {s.lead_days == null ? "No informado" : `${s.lead_days} días`}
                </dd>
                <dt>Gasto en categoría</dt>
                <dd>{number(s.share_category_pct)}%</dd>
              </dl>
              <p className="small-note">
                La prioridad ordena atención; no es una probabilidad de quiebra
                ni una fecha de rotura de stock.
              </p>
            </div>
            <div className="fact-box">
              <h3>Materiales mapeados</h3>
              {s.materials.length ? (
                s.materials.map((m) => (
                  <p key={m.material_id}>
                    <Link
                      className="text-link"
                      to={"/materiales/" + m.material_id}
                    >
                      {m.name} →
                    </Link>
                  </p>
                ))
              ) : (
                <p>Sin correspondencia en Materials</p>
              )}
              <h3>Productos relacionados</h3>
              {s.products.length ? (
                s.products.map((p) => <Badge key={p}>{p}</Badge>)
              ) : (
                <p>Productos no mapeados</p>
              )}
            </div>
            <div className="fact-box">
              <h3>Alternativo aprobado</h3>
              {s.alternate ? (
                <>
                  <Link to={"/proveedores/" + s.alternate.supplier_id}>
                    {s.alternate.name}
                  </Link>
                  <p>
                    {s.alternate.city}, {s.alternate.country}
                  </p>
                  <Badge tone="warning">Stock sin confirmar</Badge>
                </>
              ) : (
                <p>Sin alternativo aprobado</p>
              )}
            </div>
          </aside>
        </div>
      </section>
      {resolution && (
        <Modal title="Resolver incidente" close={() => setResolution(null)}>
          <form
            className="modal-body"
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                await api("/incidents/" + resolution + "/resolve", {
                  method: "POST",
                  body: JSON.stringify({ reason }),
                });
                setResolution(null);
                setS(await api("/suppliers/" + id + "?context=" + context));
                refresh();
              } catch (e) {
                setError((e as Error).message);
              }
            }}
          >
            <label htmlFor="reason">Motivo y evidencia de resolución</label>
            <textarea
              id="reason"
              minLength={8}
              maxLength={2000}
              required
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <button className="button primary" type="submit">
              Registrar resolución
            </button>
          </form>
        </Modal>
      )}
      {draft && (
        <Modal title="Borrador de consulta" close={() => setDraft(null)}>
          <div className="modal-body">
            <div className="notice info">
              Borrador editable. No se envía a ningún destinatario.
            </div>
            <label htmlFor="draft">Texto de la consulta</label>
            <textarea
              id="draft"
              rows={15}
              value={draft.text}
              onChange={(e) => setDraft({ ...draft, text: e.target.value })}
            />
            <div className="inline">
              <button
                className="button primary"
                onClick={() =>
                  action(() =>
                    api("/drafts/" + draft.id, {
                      method: "PATCH",
                      body: JSON.stringify({ text: draft.text }),
                    }),
                  )
                }
              >
                Guardar
              </button>
              <button
                className="button"
                onClick={() =>
                  navigator.clipboard
                    .writeText(draft.text)
                    .catch(() =>
                      setError(
                        "No se pudo copiar. Selecciona y copia el texto.",
                      ),
                    )
                }
              >
                <Copy size={16} />
                Copiar
              </button>
              <button
                className="button"
                onClick={() => {
                  const url = URL.createObjectURL(
                    new Blob([draft.text], {
                      type: "text/plain;charset=utf-8",
                    }),
                  );
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = "consulta-proveedor.txt";
                  a.click();
                  URL.revokeObjectURL(url);
                }}
              >
                <Download size={16} />
                Descargar TXT
              </button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
function MaterialDetail() {
  const { id } = useParams();
  const [m, setM] = useState<Material | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    api<Material>("/materials/" + id)
      .then(setM)
      .catch((e) => setError(e.message));
  }, [id]);
  if (!m) return <div role="status">{error || "Cargando material…"}</div>;
  return (
    <section className="card detail-card">
      <Link className="text-link" to="/materiales">
        ← Catálogo de materiales
      </Link>
      <div className="eyebrow">
        {m.material_id} · {m.category}
      </div>
      <h2>{m.name}</h2>
      <p>
        Especificaciones disponibles en el catálogo importado. No se han
        informado fichas técnicas adicionales.
      </p>
      <div className="fact-box">
        <h3>Datos del material</h3>
        <dl className="material-specs">
          <div>
            <dt>Identificador</dt>
            <dd>{m.material_id}</dd>
          </div>
          <div>
            <dt>Categoría</dt>
            <dd>{m.category}</dd>
          </div>
          <div>
            <dt>Necesidad mensual</dt>
            <dd>
              {number(m.monthly_requirement)} {m.unit}
            </dd>
          </div>
          <div>
            <dt>Unidad declarada</dt>
            <dd>{m.unit || "No informada"}</dd>
          </div>
        </dl>
      </div>
      <div className="detail-grid">
        <div>
          <h3>Productos relacionados</h3>
          {m.products.length ? (
            m.products.map((p) => <Badge key={p}>{p}</Badge>)
          ) : (
            <p>Productos no mapeados</p>
          )}
        </div>
        <aside>
          <div className="fact-box">
            <h3>Proveedor principal</h3>
            {m.primary ? (
              <Link className="text-link" to={"/proveedores/" + m.primary_id}>
                {m.primary.name}
              </Link>
            ) : (
              <p>No informado</p>
            )}
          </div>
          <div className="fact-box">
            <h3>Alternativo aprobado</h3>
            {m.alternate ? (
              <>
                <Link
                  className="text-link"
                  to={"/proveedores/" + m.alternate_id}
                >
                  {m.alternate.name}
                </Link>
                <Badge tone="warning">Stock sin confirmar</Badge>
              </>
            ) : (
              <p>Sin alternativo aprobado</p>
            )}
          </div>
        </aside>
      </div>
    </section>
  );
}
function Batches({ batches, presenter, action }: any) {
  const [busy, setBusy] = useState<string | null>(null);
  return (
    <section className="card batches">
      <div className="section-heading">
        <div>
          <h2>Lotes del ejercicio</h2>
          <p>Resultados y exportaciones independientes de RSS</p>
        </div>
        <Badge>{batches.length} importados</Badge>
      </div>
      {batches.length ? (
        batches.map((b: Batch) => (
          <div className="batch-row" key={b.id}>
            <div>
              <h3>{label(b.split)}</h3>
              <small>
                {b.origin_label || b.filename || "Archivo importado"}
              </small>
              <small>
                {b.count} entradas · {b.done} completadas · {b.pending}{" "}
                pendientes · {b.errors} errores
              </small>
              <progress
                max={b.count}
                value={b.done}
                aria-label={"Progreso " + label(b.split)}
              />
              {b.elapsed_seconds != null && (
                <small>
                  Tiempo medido del lote: {number(b.elapsed_seconds)} s
                </small>
              )}
            </div>
            <div className="inline">
              <button
                className="button"
                disabled={
                  !presenter ||
                  b.done === b.count ||
                  busy === b.id ||
                  !!b.queued ||
                  !!b.running
                }
                onClick={async () => {
                  setBusy(b.id);
                  try {
                    await action(
                      () =>
                        api("/batches/" + b.id + "/analyze", {
                          method: "POST",
                        }),
                      "Análisis encolado. El progreso se actualiza automáticamente.",
                    );
                  } finally {
                    setBusy(null);
                  }
                }}
              >
                {busy === b.id
                  ? "Encolando…"
                  : b.queued || b.running
                    ? "Analizando…"
                    : "Analizar"}
              </button>
              {presenter && b.done === b.count && (
                <DemoControl
                  buttonLabel="Reanalizar lote"
                  initialSelection={["batch:" + b.id]}
                  initialMode="rerun"
                  onClean={async () => {}}
                />
              )}
              <button
                className="button"
                disabled={!presenter || b.done !== b.count || b.errors > 0}
                onClick={() =>
                  window.location.assign(
                    "/api/batches/" + b.id + "/export.xlsx",
                  )
                }
              >
                <Download size={16} />
                Exportar
              </button>
            </div>
          </div>
        ))
      ) : (
        <Empty title="Importa el primer archivo">
          El catálogo se carga desde el Excel de entrenamiento.
        </Empty>
      )}
    </section>
  );
}
function Analytics({ overview, suppliers, sources, batches, ...shared }: any) {
  const data = sources.map((s: Source) => ({
    name: s.name,
    recibidas: s.received_count,
    duplicadas: s.duplicates,
  }));
  const distribution = [
    {
      name: "Sin analizar",
      count: suppliers.filter((s: Supplier) => s.priority === null).length,
    },
    ...getBands().map((b) => ({
      name: b.label_es,
      count: suppliers.filter((s: Supplier) => bandFor(s.priority) === b.id)
        .length,
    })),
  ];
  return (
    <>
      <section className="card detail-card">
        <h2>Analítica de ingestión</h2>
        <p>
          Denominador: {overview?.received || 0} artículos del contexto
          seleccionado.
        </p>
        <div className="analytics-stats">
          {[
            ["Recibidas", "received"],
            ["Procesadas", "processed"],
            ["Pendientes", "pending"],
            ["Con error", "errors"],
            ["Vinculadas", "linked"],
            ["Riesgo", "risk"],
            ["Urgentes", "urgent"],
            ["En revisión", "review"],
          ].map(([l, k]) => (
            <div key={k}>
              <small>{l}</small>
              <strong>{overview?.[k] || 0}</strong>
            </div>
          ))}
        </div>
        <div className="charts">
          <div>
            <h3>Volumen RSS por fuente</h3>
            <div className="chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data}
                  margin={{ left: 0, right: 10, bottom: 40 }}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="name"
                    angle={-25}
                    textAnchor="end"
                    height={70}
                    tick={{ fontSize: 10 }}
                  />
                  <YAxis allowDecimals={false} width={30} />
                  <Tooltip />
                  <Bar
                    isAnimationActive={false}
                    name="Recibidas"
                    dataKey="recibidas"
                    fill="#635bff"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="small-note">
              {sources
                .map(
                  (s: Source) =>
                    `${s.name}: ${s.received_count} recibidas, ${s.duplicates} duplicadas`,
                )
                .join(" · ")}
            </p>
          </div>
          <div>
            <h3>Distribución de prioridad</h3>
            {distribution.map((r) => (
              <div className="distribution" key={r.name}>
                <span>{r.name}</span>
                <meter
                  min={0}
                  max={Math.max(suppliers.length, 1)}
                  value={r.count}
                />
                <strong>{r.count}</strong>
              </div>
            ))}
            <p className="small-note">
              Proveedores únicos. Sin analizar no equivale a prioridad baja.
            </p>
          </div>
        </div>
        <p>
          Latencia p50: {number(overview?.latencies?.p50)} s · p95:{" "}
          {number(overview?.latencies?.p95)} s · muestra n=
          {overview?.latencies?.n || 0}. Una muestra pequeña no establece
          rendimiento general.
        </p>
      </section>
      <Batches batches={batches} {...shared} />
    </>
  );
}
createRoot(document.getElementById("root")!).render(
  <BrowserRouter>
    <App />
  </BrowserRouter>,
);

function MaterialsPage({ suppliers }: { suppliers: Supplier[] }) {
  const [materials, setMaterials] = useState<Material[]>([]),
    [query, setQuery] = useState(""),
    [category, setCategory] = useState(""),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    api<Material[]>("/materials")
      .then((rows) => {
        if (active) setMaterials(rows);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);
  const supplier = (id: string | null) =>
    suppliers.find((s) => s.supplier_id === id);
  const rows = materials.filter(
    (m) =>
      (!category || m.category === category) &&
      [
        m.material_id,
        m.name,
        m.category,
        supplier(m.primary_id)?.name,
        ...m.products,
      ]
        .join(" ")
        .toLocaleLowerCase("es")
        .includes(query.toLocaleLowerCase("es")),
  );
  return (
    <section className="card detail-card">
      <div className="section-heading">
        <div>
          <h2>Catálogo de materiales</h2>
          <p>
            Especificaciones, productos y proveedores del catálogo importado
          </p>
        </div>
        <Badge>{materials.length} materiales</Badge>
      </div>
      <div className="ranking-toolbar material-filters">
        <label>
          Buscar material
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Nombre, ID, producto o proveedor"
          />
        </label>
        <label>
          Categoría del material
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="">Todas las categorías</option>
            {[...new Set(materials.map((m) => m.category))].sort().map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        <button
          className="button"
          onClick={() => {
            setQuery("");
            setCategory("");
          }}
        >
          Limpiar filtros
        </button>
      </div>
      {error && (
        <p role="alert" className="error-text">
          {error}
        </p>
      )}
      {loading ? (
        <p role="status">Cargando materiales…</p>
      ) : rows.length ? (
        <div className="materials-grid">
          {rows.map((m) => (
            <article className="source-card" key={m.material_id}>
              <div className="eyebrow">
                {m.material_id} · {m.category}
              </div>
              <h3>
                <Link className="text-link" to={"/materiales/" + m.material_id}>
                  {m.name}
                </Link>
              </h3>
              <p>
                Necesidad mensual:{" "}
                <strong>
                  {number(m.monthly_requirement)} {m.unit}
                </strong>
              </p>
              <p>
                Proveedor principal:{" "}
                <Link className="text-link" to={"/proveedores/" + m.primary_id}>
                  {supplier(m.primary_id)?.name || m.primary_id}
                </Link>
              </p>
              <p>
                {m.products.length
                  ? m.products.join(" · ")
                  : "Productos no mapeados"}
              </p>
              <Link
                className="button small"
                to={"/materiales/" + m.material_id}
              >
                Ver especificaciones <ChevronRight size={16} />
              </Link>
            </article>
          ))}
        </div>
      ) : (
        <Empty
          title={
            materials.length
              ? "Sin coincidencias"
              : "Catálogo pendiente de importación"
          }
        >
          Prueba otros filtros o importa el Excel de entrenamiento.
        </Empty>
      )}
    </section>
  );
}

function SourcesPage({ sources, config, presenter, refresh, onRss }: any) {
  const [worker, setWorker] = useState<any>(null),
    [stream, setStream] = useState<Article[]>([]),
    [submitting, setSubmitting] = useState(false),
    [budget, setBudget] = useState<any>(null),
    [analysisBusy, setAnalysisBusy] = useState(false),
    [notice, setNotice] = useState(""),
    [error, setError] = useState("");
  const baseline = useRef<Set<string> | null>(null);
  const noBudgetLimits = budget?.limits_enforced === false;
  const pendingCount = stream.filter((a) => a.state === "pending").length;
  useEffect(() => {
    let active = true,
      inFlight = false;
    async function load() {
      if (inFlight) return;
      inFlight = true;
      try {
        const [w, rows, b] = await Promise.all([
          api("/worker"),
          api<Article[]>("/articles?context=rss"),
          presenter ? api("/analysis/budget") : Promise.resolve(null),
        ]);
        if (active) {
          setWorker(w);
          setStream(rows);
          setBudget(b);
          baseline.current ??= new Set(rows.map((a) => a.id));
        }
      } catch (e) {
        if (active) setError((e as Error).message);
      } finally {
        inFlight = false;
      }
    }
    load();
    const timer = setInterval(load, 3000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [presenter]);
  const active = sources.filter((s: Source) =>
      ["queued", "running"].includes(s.job_state || ""),
    ),
    completed = sources.filter((s: Source) => s.job_state === "done").length,
    failures = sources.filter((s: Source) => s.job_state === "error").length,
    newCount = baseline.current
      ? stream.filter((a) => !baseline.current!.has(a.id)).length
      : 0;
  async function synchronize() {
    setSubmitting(true);
    setError("");
    setNotice("Solicitando actualización de las seis fuentes…");
    baseline.current = new Set(stream.map((a) => a.id));
    try {
      const r = await api("/sources/sync", { method: "POST" });
      setWorker(r.worker);
      setNotice(
        `${r.job_ids.length} consultas registradas. El progreso y las noticias se actualizarán en esta pantalla.`,
      );
      await refresh(true);
    } catch (e) {
      setError((e as Error).message);
      setNotice("");
    } finally {
      setSubmitting(false);
    }
  }
  return (
    <>
      <div className="notice info">
        <Radio size={20} />
        <span>
          Seis fuentes reales. Análisis periódico de pago{" "}
          {config.rss_paid_analysis ? "habilitado" : "desactivado"}. Las
          noticias sin analizar permanecen pendientes.
        </span>
      </div>
      <section
        className="card detail-card"
        aria-busy={submitting || (active.length > 0 && !!worker?.online)}
      >
        <div className="section-heading">
          <div>
            <h2>Monitor de fuentes RSS</h2>
            <p>
              La actualización manual se encola inmediatamente. El servicio de
              procesamiento atiende la cola.
            </p>
          </div>
          <button
            className="button primary"
            disabled={
              !presenter ||
              submitting ||
              (active.length > 0 && !!worker?.online)
            }
            onClick={synchronize}
          >
            <RefreshCw
              size={16}
              className={
                submitting || (active.length > 0 && worker?.online)
                  ? "spin"
                  : ""
              }
            />
            {submitting
              ? "Solicitando…"
              : active.length && worker?.online
                ? "Actualizando…"
                : "Actualizar ahora"}
          </button>
        </div>
        {error && (
          <div className="notice error" role="alert">
            {error}
          </div>
        )}
        {notice && <p role="status">{notice}</p>}
        {worker && !worker.online && (
          <div className="notice warning">
            <Clock3 size={20} />
            <span>
              Procesamiento sin conexión. Las consultas permanecerán en cola
              hasta que el worker esté activo. Última señal:{" "}
              {date(worker.last_seen_at)}.
            </span>
          </div>
        )}
        {worker?.online && worker?.compatible === false && (
          <div className="notice warning">
            El worker usa otra versión. Actualiza su despliegue y espera 30
            segundos antes de iniciar un análisis.
          </div>
        )}
        {sources.length === 0 && (
          <p>
            No hay fuentes inicializadas. «Actualizar ahora» registrará las seis
            fuentes configuradas.
          </p>
        )}
        <div className="sync-summary" aria-live="polite">
          <strong>{stream.length} noticias recibidas</strong>
          <span>{newCount} nuevas desde esta visita o actualización</span>
          <span>
            {active.length} en cola o consultándose · {completed} fuentes
            completadas · {failures} con error
          </span>
        </div>
        {!!active.length && (
          <progress
            max={sources.length}
            value={completed + failures}
            aria-label="Progreso de consulta RSS"
          />
        )}
        <div className="sources-grid">
          {sources.map((s: Source) => (
            <article className="source-card" key={s.id}>
              <div className="inline">
                <Radio size={20} />
                <Badge
                  tone={
                    s.status === "error"
                      ? "danger"
                      : s.last_success_at
                        ? "success"
                        : "warning"
                  }
                >
                  {s.job_state === "queued"
                    ? "En cola"
                    : s.job_state === "running"
                      ? "Consultando…"
                      : label(s.status)}
                </Badge>
              </div>
              <h3>{s.name}</h3>
              <p>Última consulta: {date(s.last_attempt_at || undefined)}</p>
              <p>Último éxito: {date(s.last_success_at || undefined)}</p>
              <div className="source-count">
                <strong>{s.item_count}</strong> nuevas versiones · HTTP{" "}
                {s.http_status || "—"}
              </div>
              {s.error && <p className="error-text">{s.error}</p>}
            </article>
          ))}
        </div>
      </section>
      {presenter && (
        <section className="card detail-card">
          <div className="section-heading">
            <div>
              <h2>Análisis de noticias con JEV</h2>
              <p>
                Inicio manual · consultas y reintentos registrados · sin
                análisis periódico
              </p>
            </div>
          </div>
          <p>
            {budget
              ? noBudgetLimits
                ? `Sin límites locales de presupuesto · ${pendingCount} noticias pendientes · ${budget.network_requests} peticiones registradas`
                : `${budget.remaining} artículos disponibles · ${budget.network_requests} peticiones registradas`
              : "Consultando estado del análisis…"}
          </p>
          {budget?.limits_enforced === true &&
            budget.request_budgets?.map((b: any) => (
              <div className="notice info" key={b.id}>
                <span>
                  Presupuesto compartido:{" "}
                  <strong>
                    {b.unlimited
                      ? "Sin límite de peticiones ni vencimiento"
                      : `${b.remaining_requests} de ${b.request_limit} peticiones disponibles`}
                  </strong>{" "}
                  entre ejercicio y RSS, incluidos reintentos. {b.requests_used}{" "}
                  registradas.
                  {b.closes_at && ` Ventana hasta ${date(b.closes_at)}.`}
                </span>
              </div>
            ))}
          <p>
            {stream.filter((a) => ["done", "review"].includes(a.state)).length}{" "}
            noticias procesadas ·{" "}
            {stream.filter((a) => a.state === "error").length} con error · los
            fallos permanecen visibles.
          </p>
          <button
            className="button primary"
            disabled={
              analysisBusy ||
              !worker?.online ||
              worker?.compatible === false ||
              !budget ||
              (!noBudgetLimits && !budget.remaining) ||
              !stream.some((a) => a.state === "pending")
            }
            onClick={async () => {
              setAnalysisBusy(true);
              setError("");
              try {
                const r = await api("/analysis/rss", {
                  method: "POST",
                  body: JSON.stringify(
                    noBudgetLimits ? {} : { limit: budget.remaining },
                  ),
                });
                setNotice(
                  `${r.articles} noticias encoladas para JEV; máximo ${r.maximum_requests} peticiones, reintentos incluidos.`,
                );
                setBudget(await api("/analysis/budget"));
                await refresh(true);
              } catch (e) {
                setError((e as Error).message);
              } finally {
                setAnalysisBusy(false);
              }
            }}
          >
            {analysisBusy
              ? "Encolando análisis…"
              : noBudgetLimits
                ? `Analizar ${pendingCount} noticias pendientes con JEV`
                : `Analizar hasta ${budget?.remaining || 0} noticias con JEV`}
          </button>
          {budget?.limits_enforced === true && !budget.remaining && (
            <p>El cupo agotado no se restablece al reiniciar ni desplegar.</p>
          )}
        </section>
      )}
      <section className="card detail-card">
        <div className="section-heading">
          <div>
            <h2>Noticias que van llegando</h2>
            <p>
              Últimas incorporaciones reales · fuente y fecha de publicación
              conservadas
            </p>
          </div>
          <Link className="text-link" to="/noticias" onClick={onRss}>
            Ver noticias
          </Link>
        </div>
        <NewsList articles={stream.slice(0, 12)} onOpen={onRss} />
      </section>
    </>
  );
}

function DemoControl({
  onClean,
  initialSelection = [],
  initialMode = "delete",
  buttonLabel = "Preparar demo",
}: {
  onClean: (result?: any) => Promise<void>;
  initialSelection?: string[];
  initialMode?: "delete" | "rerun";
  buttonLabel?: string;
}) {
  const [open, setOpen] = useState(false),
    [options, setOptions] = useState<any[]>([]),
    [selection, setSelection] = useState<string[]>([]),
    [mode, setMode] = useState<"delete" | "rerun">(initialMode),
    [preview, setPreview] = useState<any>(null),
    [confirmation, setConfirmation] = useState(""),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(false),
    [error, setError] = useState("");
  const phrase = mode === "rerun" ? "REANALIZAR" : "LIMPIAR DEMO";
  function invalidate() {
    setPreview(null);
    setConfirmation("");
    setError("");
  }
  async function show() {
    setOpen(true);
    invalidate();
    setLoading(true);
    setMode(initialMode);
    setSelection(initialSelection);
    try {
      const rows = await api("/demo/options");
      setOptions([
        ...initialSelection
          .filter((x) => x.startsWith("article:"))
          .map((id) => ({
            id,
            label: "Esta noticia",
            kind: "individual",
            count: 1,
          })),
        ...rows,
      ]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  return (
    <>
      <button className="button" onClick={show}>
        {buttonLabel}
      </button>
      {open && (
        <Modal
          title="Preparar demo: elegir datos y acción"
          close={() => {
            if (!busy) setOpen(false);
          }}
        >
          <div className="modal-body">
            <p>
              Marca los datos sobre los que quieres actuar. Las opciones sin
              marcar se conservan.
            </p>
            <fieldset className="demo-options" disabled={busy || loading}>
              <legend>Datos seleccionados</legend>
              <div className="inline">
                <button
                  className="button"
                  type="button"
                  onClick={() => {
                    invalidate();
                    setSelection(
                      options
                        .filter(
                          (o) => mode === "delete" || o.kind !== "catalog",
                        )
                        .map((o) => o.id),
                    );
                  }}
                >
                  Seleccionar todo
                </button>
                <button
                  className="button"
                  type="button"
                  onClick={() => {
                    invalidate();
                    setSelection([]);
                  }}
                >
                  Desmarcar todo
                </button>
              </div>
              {options.map((o) => (
                <label className="demo-option" key={o.id}>
                  <input
                    type="checkbox"
                    checked={selection.includes(o.id)}
                    disabled={mode === "rerun" && o.kind === "catalog"}
                    onChange={(e) => {
                      invalidate();
                      setSelection(
                        e.target.checked
                          ? [...selection, o.id]
                          : selection.filter((id) => id !== o.id),
                      );
                    }}
                  />
                  <span>
                    {o.label}
                    <small>
                      {o.kind === "rss" ? "Noticias reales · " : ""}
                      {o.count}{" "}
                      {o.kind === "catalog" ? "proveedores" : "noticias"}
                    </small>
                  </span>
                </label>
              ))}
            </fieldset>
            {loading && <p role="status">Cargando opciones…</p>}
            <fieldset className="demo-options" disabled={busy}>
              <legend>Acción</legend>
              <label className="demo-option">
                <input
                  type="radio"
                  name="demo-mode"
                  checked={mode === "delete"}
                  onChange={() => {
                    invalidate();
                    setMode("delete");
                  }}
                />
                <span>
                  Borrar datos seleccionados
                  <small>
                    Permite volver a importar Excel o consultar las fuentes RSS.
                  </small>
                </span>
              </label>
              <label className="demo-option">
                <input
                  type="radio"
                  name="demo-mode"
                  checked={mode === "rerun"}
                  onChange={() => {
                    invalidate();
                    setMode("rerun");
                    setSelection(selection.filter((x) => x !== "catalog"));
                  }}
                />
                <span>
                  Volver a ejecutar el análisis
                  <small>
                    Nuevas consultas JEV; conserva las noticias y archiva
                    resultados anteriores.
                  </small>
                </span>
              </label>
            </fieldset>
            <p>
              El consumo y los registros de llamadas JEV se conservan. Los
              incidentes compartidos se recalculan con las evidencias restantes.
              Sus alertas y borradores asociados se retiran por depender de la
              revisión anterior.
            </p>
            <button
              className="button"
              disabled={busy || loading || !selection.length}
              onClick={async () => {
                setBusy(true);
                setError("");
                setConfirmation("");
                try {
                  setPreview(
                    await api("/demo/preview", {
                      method: "POST",
                      body: JSON.stringify({ selection, mode }),
                    }),
                  );
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              Revisar alcance
            </button>
            {preview && (
              <div className="fact-box" aria-live="polite">
                <p>
                  <strong>
                    {preview.counts.batches} lotes · {preview.counts.articles}{" "}
                    noticias · {preview.counts.analyses} análisis
                  </strong>
                </p>
                <p>
                  {preview.counts.incidents} incidentes ·{" "}
                  {preview.counts.alerts} alertas · {preview.counts.drafts}{" "}
                  borradores asociados
                </p>
                {preview.counts.suppliers > 0 && (
                  <p>
                    Catálogo: {preview.counts.suppliers} proveedores y{" "}
                    {preview.counts.materials} materiales.
                  </p>
                )}
                {mode === "rerun" && (
                  <p>
                    Hasta {preview.maximum_requests} peticiones nuevas,
                    incluidos reintentos. La exportación queda pendiente hasta
                    terminar el nuevo análisis.
                  </p>
                )}
              </div>
            )}
            {(error || preview?.blocked) && (
              <p className="error-text" role="alert">
                {error || preview.blocked}
              </p>
            )}
            {preview && (
              <label className="cleanup-confirmation">
                Escribe {phrase} para confirmar
                <input
                  value={confirmation}
                  onChange={(e) => setConfirmation(e.target.value)}
                  autoComplete="off"
                  disabled={busy}
                />
              </label>
            )}
            <div className="inline">
              <button
                className="button"
                disabled={busy}
                onClick={() => setOpen(false)}
              >
                Cancelar
              </button>
              <button
                className="button primary"
                disabled={
                  busy ||
                  !preview ||
                  !!preview.blocked ||
                  confirmation !== phrase
                }
                onClick={async () => {
                  setBusy(true);
                  setError("");
                  try {
                    const response = await api("/demo/cleanup", {
                      method: "POST",
                      body: JSON.stringify({
                        confirmation,
                        token: preview.token,
                      }),
                    });
                    setOpen(false);
                    await onClean(response.deleted);
                  } catch (e) {
                    setError((e as Error).message);
                    setPreview(null);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                {busy
                  ? "Procesando…"
                  : mode === "rerun"
                    ? "Encolar nuevo análisis"
                    : "Borrar selección"}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}

function ComparisonControl({ article }: { article: Article }) {
  const [rows, setRows] = useState<any[]>([]),
    [error, setError] = useState(""),
    [open, setOpen] = useState(false),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    async function refresh() {
      try {
        const values = await api("/articles/" + article.id + "/comparisons");
        if (active) setRows(values);
      } catch (e) {
        if (active) setError((e as Error).message);
      }
    }
    refresh();
    const timer = window.setInterval(refresh, 3000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [article.id]);
  const current = rows[0],
    running = current && ["queued", "running"].includes(current.state);
  return (
    <section className="comparison-panel">
      <h3>Contraste con tres evaluaciones JEV</h3>
      <p>
        Tres consultas nuevas del mismo modelo, con la política actual. Sirven
        para comparar incertidumbre; no son expertos independientes ni eliminan
        automáticamente una revisión.
      </p>
      <button
        className="button"
        disabled={
          busy || running || !["review", "done"].includes(article.state)
        }
        onClick={() => setOpen(true)}
      >
        Contrastar con 3 JEV
      </button>
      {error && (
        <p className="error-text" role="alert">
          {error}
        </p>
      )}
      {current && (
        <div aria-live="polite">
          <p>
            <Badge
              tone={
                current.state === "error"
                  ? "danger"
                  : running
                    ? "warning"
                    : "info"
              }
            >
              {label(current.state)}
            </Badge>{" "}
            · {current.ballots.length}/3 evaluaciones terminadas
          </p>
          {current.summary.message && <p>{current.summary.message}</p>}
          <ol>
            {current.ballots.map((b: any, index: number) => (
              <li key={index}>
                <strong>
                  Evaluación {index + 1}: {label(b.analysis_status)}
                </strong>{" "}
                · {riskLabel(b.is_risk)} · {urgencyLabel(b.urgent)} ·
                Proveedores{" "}
                {b.affected_supplier_ids.join(", ") || "sin vínculo"} ·{" "}
                {label(b.event_type || "other")}
                {b.error && <p className="error-text">{b.error}</p>}
                {b.review_reasons.map((r: string) => (
                  <p key={r}>{reviewLabel(r)}</p>
                ))}
              </li>
            ))}
          </ol>
          {current.ballots.length > 0 && (
            <p>
              {current.summary.done_votes}/3 sin revisión ·{" "}
              {current.summary.review_votes}/3 con revisión ·{" "}
              {current.summary.errors} errores. Acuerdo en decisión:{" "}
              {current.summary.decision_agreement}/3.
            </p>
          )}
          <small>
            El análisis vigente, su prioridad, sus alarmas y las exportaciones
            se conservan.
          </small>
        </div>
      )}
      {open && (
        <Modal
          title="Iniciar contraste de tres evaluaciones"
          close={() => {
            if (!busy) setOpen(false);
          }}
        >
          <div className="modal-body">
            <p>
              Se harán hasta 18 peticiones JEV, incluidos reintentos: dos etapas
              por evaluación, con un máximo de tres intentos por etapa. No se
              consulta la segunda etapa cuando no hay proveedores candidatos.
            </p>
            <p>
              El resultado será auxiliar. Una mayoría no sustituye la evidencia
              ni los datos que faltan y puede repetir el mismo error del modelo.
            </p>
            <div className="inline">
              <button
                className="button"
                disabled={busy}
                onClick={() => setOpen(false)}
              >
                Cancelar
              </button>
              <button
                className="button primary"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  setError("");
                  try {
                    await api("/articles/" + article.id + "/compare", {
                      method: "POST",
                    });
                    setRows(
                      await api("/articles/" + article.id + "/comparisons"),
                    );
                    setOpen(false);
                  } catch (e) {
                    setError((e as Error).message);
                    setOpen(false);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                {busy ? "Encolando…" : "Iniciar contraste"}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </section>
  );
}

function AnalysisHistory({ article }: { article: Article }) {
  const [rows, setRows] = useState<any[]>([]),
    [error, setError] = useState(""),
    [open, setOpen] = useState(false),
    [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!open) return;
    let active = true;
    setLoading(true);
    setError("");
    api("/articles/" + article.id + "/runs")
      .then((values) => {
        if (active) setRows(values);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [open, article.id, article.generation, article.state]);
  return (
    <details
      className="comparison-panel"
      aria-busy={open && loading}
      onToggle={(e) => {
        if (e.target === e.currentTarget) setOpen(e.currentTarget.open);
      }}
    >
      <summary>Historial de análisis</summary>
      {loading && <p role="status">Actualizando historial…</p>}
      {error && <p role="alert">{error}</p>}
      {rows.map((r: any) => (
        <details key={r.generation}>
          <summary>
            Análisis {r.generation + 1} · {date(r.created_at)} ·{" "}
            {label(r.result.analysis_status)}
          </summary>
          <p>
            {riskLabel(r.result.is_risk)} · {urgencyLabel(r.result.urgent)} ·
            Proveedores{" "}
            {r.result.affected_supplier_ids.join(", ") || "sin vínculo"}
          </p>
          {r.result.evidence.map((e: any) => (
            <blockquote key={e.id}>{e.text}</blockquote>
          ))}
        </details>
      ))}
    </details>
  );
}
