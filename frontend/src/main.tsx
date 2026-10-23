import { LoadingBlock, AsyncButton, downloadFile } from "./OperationFeedback";
import { PendingAnalysis } from "./PendingAnalysis";
import { RssTriage } from "./RssTriage";
import { HumanReview } from "./HumanReview";
import { IncidentWorkspace } from "./IncidentWorkspace";
import { ActionPlan, PlanCard, usePlans } from "./ActionPlan";
import { UrgentBanner } from "./UrgentBanner";
import {
  scopedPath,
  useNewsFilters,
  useNewsReturn,
  rememberNews,
} from "./NewsContinuity";
import { ReviewGuidance } from "./ReviewGuidance";
import {
  AnalysisProfile,
  CANDIDATE,
  DEFAULT_ANALYSIS_PROFILE,
} from "./AnalysisProfile";
import {
  VerificationDraft,
  RssArticleAnalysis,
  SupplierVerificationList,
} from "./VerificationDraft";
import { ProcessingPulse } from "./ProcessingPulse";
import { BusinessKpis } from "./BusinessKpis";
import { BuyerDecision } from "./BuyerDecision";
import { AttentionDesk, ProcurementBrief } from "./Procurement.tsx";
import { SupplierMap, toMapData } from "./SupplierMap";
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
  BrainCircuit,
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
  Sparkles,
} from "lucide-react";

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
const ModelPage = React.lazy(() =>
  import("./ModelPage").then((module) => ({ default: module.ModelPage })),
);
import { ChartBoundary } from "./ChartBoundary";
const AdministrativeModels = React.lazy(() =>
  import("./ModelArchive").then((m) => ({ default: m.AdministrativeModels })),
);
const SourceVolumeChart = React.lazy(() => import("./SourceVolumeChart"));
import { EventTag, eventNames } from "./EventTag";

const names: Record<string, string> = {
  impact_state_local_uncertainty:
    "Estado concreto por precisar: activo o seguimiento; se conserva una acción no urgente respaldada.",
  risk_fact_prediction_conflict:
    "El hecho adverso respaldado y la decisión de riesgo discrepan; confirmar su interpretación.",
  model_check_same_source_not_independent_corroboration:
    "Las comprobaciones del modelo contrastan la misma fuente; no son una corroboración externa independiente.",
  potential_exposure_is_not_confirmed_damage:
    "La compatibilidad del catálogo no confirma daño individual ni entregas afectadas.",
  training: "Entrenamiento",
  validation: "Validación · retrospectiva",
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
  ...eventNames,
  link_evidence_confidence_low: "Selección de cita de asociación incierta",
  association_support_insufficient: "Soporte insuficiente de la asociación",
  scope_coverage_unconfirmed: "Cobertura del alcance sin confirmar",
  geography_requires_review: "Ubicación ambigua: exposición por confirmar",
  geography_not_resolved: "Ubicación con alternativas o sin resolver",
  risk_ambiguous: "Decisión de riesgo ambigua",
  risk_evidence_insufficient:
    "Evidencia insuficiente para la decisión de riesgo",
  urgency_ambiguous: "Decisión de urgencia ambigua",
  urgency_support_insufficient:
    "Falta soporte suficiente del criterio de urgencia",
  risk_impact_contradiction: "Riesgo y estado del impacto contradictorios",
  inventory_missing: "Inventario físico no informado",
  criticality_missing: "Criticidad no informada",
  risk_without_operational_evidence:
    "Riesgo propuesto sin evidencia operativa consistente",
  source_text_limited: "Lectura limitada al resumen o a un texto parcial",
  potential_exposure_is_not_confirmed_damage:
    "La exposición potencial no confirma daños ni entregas afectadas.",
  model_check_same_source_not_independent_corroboration:
    "La comprobación automatizada interpreta la misma fuente; no la corrobora externamente.",
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
  const [origin, setOrigin] = useState(
    new URLSearchParams(window.location.search).get("origen") || "",
  );
  const effectiveOrigin =
    location.pathname === "/" && !origin.startsWith("context:") ? origin : "";
  const [context, setContext] = useState(
      new URLSearchParams(window.location.search).get("context") === "rss"
        ? "rss"
        : "exercise",
    ),
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
    [uploading, setUploading] = useState(false),
    [refreshError, setRefreshError] = useState(""),
    [sound, setSound] = useState("Desactivado"),
    [more, setMore] = useState(false),
    [qaStatus, setQaStatus] = useState(""),
    [qaBusy, setQaBusy] = useState(false),
    [alertFilter, setAlertFilter] = useState("current");
  const qaPending = useRef<{
    signal: {
      id: number;
      revision: number;
      sound_eligible: boolean;
      acknowledged: boolean;
    };
    dueAt: number;
  } | null>(null);
  const scope = context + "|" + effectiveOrigin;
  const activeScope = useRef(scope);
  // Plans follow incident revisions; refetch only when an incident or alert changes.
  const plans = usePlans(
    context,
    presenter +
      "|" +
      alerts.map((a) => a.id + ":" + a.revision).join(",") +
      "|" +
      suppliers
        .flatMap((s) =>
          (s.incidents ?? []).map((i) => i.id + i.state + i.priority),
        )
        .join(","),
  );
  const cursor = useRef<number | null>(null),
    file = useRef<HTMLInputElement>(null),
    activeContext = useRef(context),
    configRef = useRef<any>({});
  useEffect(() => {
    const requested = new URLSearchParams(location.search).get("context");
    if (
      (requested === "rss" || requested === "exercise") &&
      requested !== context
    ) {
      setOrigin("");
      setContext(requested);
    }
    if (location.pathname === "/")
      setOrigin(new URLSearchParams(location.search).get("origen") || "");
  }, [location.pathname, location.search]);
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
      setRefreshError("");
      setOverview(o);
      setSuppliers(s.items);
      setArticles(a);
      setSources(f);
      setBatches(b);
      setAlerts(n.items);
      document.title =
        (n.unread ? `(${n.unread}) ` : "") + "Supplier Risk Radar · Helixa";
      const qaDue =
        cursor.current !== null &&
        qaPending.current &&
        Date.now() >= qaPending.current.dueAt
          ? qaPending.current.signal
          : null;
      if (
        cursor.current !== null &&
        configRef.current.cooldown_seconds !== undefined
      )
        await audio
          .notify(
            [
              ...n.items.filter((x: Alert) => x.id > cursor.current!),
              ...(qaDue ? [qaDue] : []),
            ],
            configRef.current.cooldown_seconds,
          )
          .catch(() => setSound("Bloqueado"));
      if (qaDue) {
        qaPending.current = null;
        setQaBusy(false);
        setQaStatus(
          "QA entregada al aviso automático. Confirma la audibilidad en el dispositivo; este estado no demuestra que haya sonado.",
        );
      }
      cursor.current = n.cursor;
    } catch (e) {
      if (activeScope.current === scope) {
        nextRefreshAt.current = Date.now() + 30000;
        setRefreshError((e as Error).message);
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
    if (uploading) return;
    setUploading(true);
    try {
      const data = new FormData();
      data.append("file", f);
      const imported = await action(
        () => api("/imports", { method: "POST", body: data }),
        "Archivo importado. Revisa el lote antes de analizar.",
      );
      if (imported?.batch_id) {
        setContext("exercise");
        setOrigin("batch:" + imported.batch_id);
        navigate(
          scopedPath(
            "/?origen=" + encodeURIComponent("batch:" + imported.batch_id),
            "exercise",
          ),
        );
      }
    } finally {
      setUploading(false);
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
    { to: "/modelo", icon: BrainCircuit, text: "Modelo" },
  ];
  return (
    <div className="app">
      <a className="skip" href="#contenido">
        Saltar al contenido
      </a>
      <aside className="sidebar">
        <Link
          to={scopedPath(
            origin ? "/?origen=" + encodeURIComponent(origin) : "/",
            context,
          )}
          className="brand"
        >
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
            <NavLink
              key={n.to}
              to={scopedPath(
                n.to === "/" && origin
                  ? "/?origen=" + encodeURIComponent(origin)
                  : n.to,
                context,
              )}
              end={n.to === "/"}
            >
              <n.icon size={19} />
              {n.text}
              {n.to === "/alertas" &&
                alerts.filter(
                  (a) =>
                    !a.acknowledged &&
                    a.is_current !== false &&
                    !["superseded", "resolved"].includes(a.state),
                ).length > 0 && (
                  <span className="nav-count">
                    {
                      alerts.filter(
                        (a) =>
                          !a.acknowledged &&
                          a.is_current !== false &&
                          !["superseded", "resolved"].includes(a.state),
                      ).length
                    }
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
                const next = e.target.value;
                setContext(next);
                navigate(
                  scopedPath(
                    location.pathname.startsWith("/noticias/")
                      ? "/noticias"
                      : location.pathname,
                    next,
                  ),
                  { replace: true },
                );
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
                {(
                  {
                    "/": "Resumen",
                    "/proveedores": "Proveedores",
                    "/materiales": "Materiales",
                    "/noticias": "Noticias",
                    "/alertas": "Alertas",
                    "/fuentes": "Fuentes",
                    "/analitica": "Analítica",
                    "/modelo": "Modelo",
                    "/administracion": "Herramientas de modelo",
                  } as Record<string, string>
                )["/" + (location.pathname.split("/")[1] || "")] || "Resumen"}
                <span className="heading-dot">.</span>
              </h1>
              <p>
                {context === "rss"
                  ? "Exposición potencial de una cartera simulada a noticias reales."
                  : "Cartera ficticia de Helixa · evidencia, decisiones y acciones de compras."}
              </p>
            </div>
            <div className="heading-actions">
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
              {(location.pathname === "/" ||
                location.pathname.startsWith("/noticias")) && (
                <>
                  <button
                    className="button primary"
                    disabled={uploading}
                    aria-busy={uploading}
                    onClick={() =>
                      presenter ? file.current?.click() : setLoginOpen(true)
                    }
                  >
                    <Upload size={17} />
                    {uploading ? "Validando e importando…" : "Importar Excel"}
                  </button>
                </>
              )}
            </div>
          </div>
          <UrgentBanner
            plans={plans}
            onGo={() => {
              navigate(scopedPath("/", context));
              // The Resumen route renders and refreshes its data after navigating; keep
              // bringing the desk to the top until the layout settles (about 3 s at most).
              let tries = 0,
                settled = 0;
              const reveal = () => {
                const desk = document.getElementById("attention-title");
                const off = desk ? Math.abs(desk.getBoundingClientRect().top - 16) : 999;
                if (desk && off > 8) {
                  settled = 0;
                  window.scrollBy({ top: desk.getBoundingClientRect().top - 16 });
                } else if (desk) settled++;
                if (settled < 2 && ++tries < 12) window.setTimeout(reveal, 250);
              };
              window.setTimeout(reveal, 150);
            }}
          />
          {config.fixtures && (
            <div className="notice warning">
              Demostración de interfaz · MOCKS IDENTIFICADOS. Estos resultados
              no proceden de JEV real.
            </div>
          )}
          {refreshError && (
            <div className="notice warning" role="alert">
              <span>{refreshError} Los datos ya visibles se conservan.</span>
              <AsyncButton
                onAction={() => refresh(true)}
                busyLabel="Consultando…"
              >
                Reintentar consulta
              </AsyncButton>
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
          {presenter && (
            <details className="qa-control">
              <summary>Herramientas del presentador</summary>
              <Link className="button" to="/administracion/modelo">
                Auditar campañas y perfiles anteriores
              </Link>
              {presenter && (
                <DemoControl
                  onClean={async (result) => {
                    cursor.current = null;
                    navigate(
                      scopedPath(
                        result?.mode === "rerun" && origin
                          ? "/?origen=" + encodeURIComponent(origin)
                          : "/",
                        context,
                      ),
                    );
                    await refresh(true);
                    setMessage(
                      result?.mode === "rerun"
                        ? `${result.job_ids.length} análisis encolados; los resultados aparecerán conforme terminen.`
                        : "Selección borrada. Consumo e historial de llamadas conservados.",
                    );
                  }}
                />
              )}
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

              <section
                className="notice"
                aria-label="Prueba controlada de alerta automática"
              >
                <div>
                  <strong>QA · Alerta automática controlada</strong>
                  <p>
                    Activa el sonido y espera 30 segundos desde la última alerta
                    automática. Esta prueba programa una señal elegible para el
                    próximo sondeo después de 5 segundos. No usa JEV ni crea
                    noticias, incidentes o alertas de cartera. Solo existe en
                    esta pestaña.
                  </p>
                  <button
                    className="button"
                    disabled={qaBusy || loading}
                    onClick={async () => {
                      setQaBusy(true);
                      try {
                        const signal = await api("/qa/audio", {
                          method: "POST",
                        });
                        qaPending.current = {
                          signal,
                          dueAt: Date.now() + signal.delay_seconds * 1000,
                        };
                        setQaStatus(
                          "QA programada. Mantén esta pestaña abierta; el sondeo automático la recogerá.",
                        );
                      } catch (e) {
                        setQaBusy(false);
                        setError((e as Error).message);
                      }
                    }}
                  >
                    Programar alerta QA (5 s)
                  </button>
                  {qaStatus && <p role="status">{qaStatus}</p>}
                </div>
              </section>
            </details>
          )}
          {!overview ? (
            loading ? (
              <LoadingBlock label="Cargando datos del radar…" />
            ) : (
              <section className="card detail-card" role="alert">
                <h2>No se pudieron cargar los datos</h2>
                <p>
                  Reintenta la consulta. No se ha mostrado una lista vacía como
                  si no hubiera registros.
                </p>
                <AsyncButton
                  className="button primary"
                  onAction={() => refresh(true)}
                  busyLabel="Recuperando…"
                >
                  Recuperar datos
                </AsyncButton>
              </section>
            )
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
                          const next = value
                            ? value === "context:rss" ||
                              value.startsWith("rss:")
                              ? "rss"
                              : "exercise"
                            : context;
                          setOrigin(value);
                          setContext(next);
                          navigate(
                            scopedPath(
                              value
                                ? "/?origen=" + encodeURIComponent(value)
                                : "/",
                              next,
                            ),
                          );
                        }}
                      >
                        <option value="">
                          Todos ·{" "}
                          {context === "rss" ? "Noticias reales" : "Ejercicio"}
                        </option>
                        <optgroup label="Grupos de datos">
                          <option value="context:rss">
                            Solo noticias reales · todos los RSS
                          </option>
                          <option value="context:exercise">
                            Solo datos base · todos los Excel
                          </option>
                        </optgroup>
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
                    <AttentionDesk
                      suppliers={suppliers}
                      context={context}
                      origin={effectiveOrigin}
                      plans={plans}
                    />
                    <FollowupDesk
                      suppliers={suppliers}
                      context={context}
                      reviewCount={overview?.review || 0}
                    />
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
                    <BusinessKpis suppliers={suppliers} context={context} />
                    <ProcessingPulse
                      key={scope}
                      articles={articles}
                      presenter={presenter}
                    />
                    <div className="dashboard-grid">
                      <section className="card ranking-panel">
                        <div className="section-heading">
                          <div>
                            <h2>Prioridad de proveedores</h2>
                            <p>Máximo de incidentes activos por proveedor</p>
                          </div>
                          <Badge>{suppliers.length} proveedores</Badge>
                        </div>
                        <Ranking
                          suppliers={suppliers}
                          context={context}
                          origin={effectiveOrigin}
                        />
                        <Link
                          className="card-footer-link"
                          to={scopedPath("/proveedores", context)}
                        >
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
                          <p className="small-note">
                            Orden: urgencia, riesgo y revisión; fecha dentro de
                            cada grupo. Las noticias neutras siguen en Noticias.
                          </p>
                          <NewsList
                            presenter={presenter}
                            articles={[...articles]
                              .sort((a, b) => {
                                const rank = (x: Article) =>
                                  x.analysis?.urgent === "Y"
                                    ? 3
                                    : x.analysis?.is_risk === "Y"
                                      ? 2
                                      : x.state === "review"
                                        ? 1
                                        : 0;
                                return (
                                  rank(b) - rank(a) ||
                                  b.published_date.localeCompare(
                                    a.published_date,
                                  )
                                );
                              })
                              .slice(0, 4)}
                          />
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
                    <section
                      className="card exposure-map"
                      aria-labelledby="exposure-title"
                    >
                      <div className="section-heading">
                        <div>
                          <h2 id="exposure-title">Mapa de exposición</h2>
                          <p>
                            Proveedores por prioridad actual y eventos abiertos
                            del origen seleccionado
                          </p>
                        </div>
                      </div>
                      <div className="px-[22px] pb-[22px]">
                        {loading && !suppliers.length ? (
                          <p className="small-note">Cargando mapa…</p>
                        ) : (
                          <SupplierMap
                            {...toMapData(suppliers)}
                            onSupplierClick={(id) =>
                              navigate(
                                scopedPath(
                                  "/proveedores/" + encodeURIComponent(id),
                                  context,
                                ),
                              )
                            }
                          />
                        )}
                      </div>
                    </section>
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
                element={
                  <NewsPage
                    key={scope}
                    articles={articles}
                    context={context}
                    presenter={presenter}
                  />
                }
              />
              <Route
                path="/noticias/:id"
                element={<ArticleDetail {...shared} suppliers={suppliers} />}
              />
              <Route
                path="/alertas"
                element={
                  <section className="card">
                    <div className="section-heading">
                      <div>
                        <h2>Centro de alertas</h2>
                        <p>
                          Vigentes: sin leer primero. Reconocer un aviso no
                          completa la acción ni recupera al proveedor.
                        </p>
                      </div>
                      <Badge>
                        {
                          alerts.filter(
                            (a) =>
                              !a.acknowledged &&
                              a.is_current !== false &&
                              !["superseded", "resolved"].includes(a.state),
                          ).length
                        }{" "}
                        sin leer
                      </Badge>
                    </div>
                    <div className="ranking-toolbar">
                      <select
                        aria-label="Estado de alerta"
                        value={alertFilter}
                        onChange={(e) => setAlertFilter(e.target.value)}
                      >
                        <option value="current">Vigentes por atender</option>
                        <option value="history">Histórico de avisos</option>
                        <option value="all">Todas · incluye histórico</option>
                        <option value="new">Sin leer</option>
                        <option value="ack">Reconocidas</option>
                        <option value="resolved">Recuperadas</option>
                        <option value="superseded">Análisis sustituidos</option>
                      </select>
                    </div>
                    {visibleAlerts(alerts, alertFilter).length ? (
                      visibleAlerts(alerts, alertFilter).map((a) => (
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
                                {a.is_current === false &&
                                !["superseded", "resolved"].includes(a.state)
                                  ? "Aviso histórico"
                                  : a.state === "superseded"
                                    ? "Análisis sustituido"
                                    : a.state === "resolved"
                                      ? "Recuperada"
                                      : a.needs_review
                                        ? "Requiere revisión"
                                        : a.urgent === "Y" || a.sound_eligible
                                          ? "Acción inmediata"
                                          : "Atención de compras"}
                              </Badge>
                              <small>{date(a.created_at)}</small>
                            </div>
                            <h3>
                              <Link to={"/proveedores/" + a.supplier_id}>
                                {a.supplier_name}
                              </Link>
                            </h3>
                            <p>{a.headline}</p>
                            {a.historical_reason && (
                              <p className="small-note">
                                {a.historical_reason}
                              </p>
                            )}
                            <div className="inline">
                              <Link
                                className="text-link"
                                to={scopedPath(
                                  "/proveedores/" + a.supplier_id,
                                  context,
                                )}
                              >
                                Gestionar acción
                              </Link>
                              {a.needs_review && a.article_id && (
                                <Link
                                  className="text-link"
                                  to={scopedPath(
                                    "/noticias/" + a.article_id,
                                    context,
                                  )}
                                >
                                  Resolver revisión
                                </Link>
                              )}
                            </div>
                            <EventTag
                              analysis={a.event_tag}
                              state="unavailable"
                            />
                            <small>
                              Prioridad {number(a.priority)} ·{" "}
                              {a.sound_eligible
                                ? "Elegible para sonido"
                                : "Solo aviso visual"}
                            </small>
                            {plans[a.incident_id] &&
                              a.is_current !== false &&
                              !["superseded", "resolved"].includes(a.state) && (
                                <details
                                  className="alert-plan"
                                  open={!a.acknowledged && a.urgent === "Y"}
                                >
                                  <summary>
                                    Plan de acción (
                                    {plans[a.incident_id]!.actions.length}{" "}
                                    acciones)
                                  </summary>
                                  <PlanCard
                                    plan={plans[a.incident_id]!}
                                    presenter={presenter}
                                  />
                                </details>
                              )}
                            {suppliers.find(
                              (s) => s.supplier_id === a.supplier_id,
                            ) && (
                              <ProcurementBrief
                                supplier={
                                  suppliers.find(
                                    (s) => s.supplier_id === a.supplier_id,
                                  )!
                                }
                                context={context}
                                incidentId={a.incident_id}
                                compact
                                hideNext={
                                  !!plans[a.incident_id] &&
                                  a.is_current !== false &&
                                  !["superseded", "resolved"].includes(a.state)
                                }
                              />
                            )}
                            <div className="inline">
                              <AsyncButton
                                className="button small"
                                disabled={!presenter || a.acknowledged}
                                busyLabel="Reconociendo…"
                                onAction={async () => {
                                  await api(`/alerts/${a.id}/ack`, {
                                    method: "POST",
                                  });
                                  setMessage(
                                    "Aviso reconocido. La acción y el incidente conservan su estado.",
                                  );
                                  await refresh(true);
                                }}
                              >
                                {a.acknowledged ? "Reconocida" : "Reconocer"}
                              </AsyncButton>
                              <Link
                                className="text-link"
                                to={
                                  a.article_id
                                    ? "/noticias/" + a.article_id
                                    : "/proveedores/" + a.supplier_id
                                }
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
                path="/modelo"
                element={
                  <ChartBoundary message="No se pudo cargar la información del perfil. Las vistas operativas siguen disponibles.">
                    <React.Suspense
                      fallback={
                        <p role="status">Cargando perfil y métricas…</p>
                      }
                    >
                      <ModelPage
                        presenter={presenter}
                        context={context}
                        config={config}
                        batches={batches}
                        sources={sources}
                      />
                    </React.Suspense>
                  </ChartBoundary>
                }
              />
              <Route
                path="/administracion/modelo"
                element={
                  presenter ? (
                    <React.Suspense
                      fallback={<LoadingBlock label="Cargando auditoría…" />}
                    >
                      <AdministrativeModels
                        presenter={presenter}
                        context={context}
                        config={config}
                        batches={batches}
                        sources={sources}
                      />
                    </React.Suspense>
                  ) : (
                    <p role="status">
                      Accede como presentador para consultar la auditoría
                      privada.
                    </p>
                  )
                }
              />
              <Route
                path="/analitica"
                element={
                  <Analytics
                    overview={overview}
                    articles={articles}
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
            <NavLink
              key={n.to}
              to={scopedPath(
                n.to === "/" && origin
                  ? "/?origen=" + encodeURIComponent(origin)
                  : n.to,
                context,
              )}
              end={n.to === "/"}
            >
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
              [
                "/proveedores",
                "/materiales",
                "/fuentes",
                "/analitica",
                "/modelo",
              ].includes(n.to),
            )
            .map((n) => (
              <Link
                key={n.to}
                to={scopedPath(
                  n.to === "/" && origin
                    ? "/?origen=" + encodeURIComponent(origin)
                    : n.to,
                  context,
                )}
                onClick={() => setMore(false)}
              >
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
  origin = "",
}: {
  suppliers: Supplier[];
  context: string;
  full?: boolean;
  origin?: string;
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
            Alternativo registrado
            <select
              aria-label="Alternativo registrado"
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
              to={
                "/proveedores/" +
                s.supplier_id +
                (origin ? "?origen=" + encodeURIComponent(origin) : "")
              }
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
                  <p className={"ranking-reason" + (full ? " concise" : "")}>
                    {s.reason}
                  </p>
                  <small>
                    {s.latest_evidence
                      ? `Evidencia: ${date(s.latest_evidence)}`
                      : s.status === "unlinked"
                        ? "Sin evidencia vinculada"
                        : "Pendiente de análisis"}
                  </small>
                </div>
              </div>
              <div className="dependency">
                <Badge tone={s.criticality === "High" ? "purple" : "neutral"}>
                  Criticidad {label(s.criticality).toLowerCase()}
                </Badge>
                {s.single_source === "Y" && <small>Fuente única</small>}
                <small>
                  {s.inventory_days == null
                    ? ["Logistics", "Services"].includes(s.category)
                      ? "Inventario no aplicable"
                      : "Inventario desconocido"
                    : s.inventory_days + " días de cobertura"}{" "}
                  ·{" "}
                  {s.alternate_id
                    ? "Alternativo registrado"
                    : "Sin alternativo registrado"}
                </small>
                {s.status === "resolved" && (
                  <Badge tone="success">Recuperado</Badge>
                )}
                {s.status === "unlinked" && <Badge>Sin vínculo</Badge>}
                {s.status === "superseded" && (
                  <Badge>Análisis sustituido</Badge>
                )}
                {s.status === "positive" && (
                  <Badge tone="success">Sin riesgo activo</Badge>
                )}
                {s.urgent && <Badge tone="danger">Urgente</Badge>}
                {s.needs_review && <Badge tone="warning">Revisión</Badge>}
              </div>
              {s.priority === 0 && s.needs_review ? (
                <div className="priority-unconfirmed">
                  <strong>Por confirmar</strong>
                  <small>Estimación 0 · decisión en revisión</small>
                </div>
              ) : (
                <Score value={s.priority} />
              )}
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
  presenter = false,
  onOpen,
}: {
  articles: Article[];
  presenter?: boolean;
  onOpen?: () => void;
}) {
  const listLocation = useLocation();
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
              {["done", "review"].includes(a.state)
                ? "Análisis completado"
                : label(a.state)}
            </Badge>
            {a.state === "review" && a.human_review?.state !== "resolved" && (
              <Badge tone="warning">Duda de análisis pendiente</Badge>
            )}
            {a.analysis && (
              <Badge tone={a.analysis.is_risk === "Y" ? "danger" : "neutral"}>
                {a.analysis.is_risk === "Y"
                  ? "Riesgo detectado"
                  : a.analysis.is_risk === "N"
                    ? "Sin riesgo detectado"
                    : "Sin decisión"}
              </Badge>
            )}
            <EventTag analysis={a.analysis} state={a.state} />
            {a.human_review?.state === "resolved" && (
              <Badge>Revisión humana resuelta</Badge>
            )}
          </div>
          {(a as any).preliminary_relevance && (
            <p className="small-note">
              {(a as any).preliminary_relevance.level === "none"
                ? "Sin indicio preliminar de cartera; no es un descarte"
                : "Por qué leer: " +
                  (a as any).preliminary_relevance.reasons.join(" · ")}{" "}
              · No confirma afectación.
            </p>
          )}
          <h3>
            <Link
              id={"news-link-" + a.id}
              to={scopedPath(
                "/noticias/" + a.id,
                a.split === "rss" ? "rss" : "exercise",
              )}
              state={{
                newsReturnTo: scopedPath(
                  "/noticias",
                  a.split === "rss" ? "rss" : "exercise",
                ),
                newsFromList: listLocation.pathname === "/noticias",
              }}
              onClick={(e) => {
                if (listLocation.pathname === "/noticias")
                  rememberNews(
                    a.split === "rss" ? "rss" : "exercise",
                    a.id,
                    e.currentTarget,
                  );
                onOpen?.();
              }}
            >
              {a.headline}
            </Link>
          </h3>
          {a.analysis?.affected_supplier_ids?.length ? (
            <p className="small-note">
              Relacionados: {a.analysis.affected_supplier_ids.join(" · ")}
              {a.analysis.urgent === "Y"
                ? " · Atención urgente de compras"
                : ""}
            </p>
          ) : null}
          {a.state === "pending" && (
            <PendingAnalysis articles={[a]} presenter={presenter} single />
          )}
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
function NewsPage({
  articles,
  context,
  presenter,
}: {
  articles: Article[];
  context: string;
  presenter: boolean;
}) {
  const [filters, patch] = useNewsFilters(context);
  const {
    q,
    state,
    source,
    split,
    from,
    to,
    event,
    relevant,
    human,
    preliminary,
  } = filters;
  const setQ = (q: string) => patch({ q }),
    setState = (state: string) => patch({ state }),
    setSource = (source: string) => patch({ source }),
    setSplit = (split: string) => patch({ split }),
    setFrom = (from: string) => patch({ from }),
    setTo = (to: string) => patch({ to }),
    setEvent = (event: string) => patch({ event }),
    setRelevant = (relevant: boolean) => patch({ relevant });
  const filtered = articles.filter(
    (a) =>
      (!q ||
        (a.headline + " " + a.summary)
          .toLowerCase()
          .includes(q.toLowerCase())) &&
      (!state || a.state === state) &&
      (!human ||
        (human === "dismissed"
          ? Boolean(
              (a as any).human_review?.state === "resolved" &&
                (a as any).human_review?.decisions.length &&
                (a as any).human_review.decisions.every(
                  (d: any) => d.association === "rejected",
                ),
            )
          : human === "pending"
            ? a.state === "review" && a.human_review?.state !== "resolved"
            : a.human_review?.state === human)) &&
      (!preliminary || (a as any).preliminary_relevance?.level !== "none") &&
      (!source || a.source === source) &&
      (!split || a.split === split) &&
      (!from || a.published_date >= from) &&
      (!to || a.published_date.slice(0, 10) <= to) &&
      (!event ||
        a.analysis?.event_type === event ||
        a.analysis?.event_classification?.category === event) &&
      (!relevant || Boolean(a.analysis?.affected_supplier_ids.length)),
  );
  useNewsReturn(context, filtered.length);
  return (
    <section className="card news-page">
      <div className="section-heading">
        <div>
          <h2>Noticias y evidencias</h2>
          <p>Fuente, fecha y estado de cada entrada</p>
        </div>
        <Badge>{articles.length} recibidas</Badge>
      </div>
      <ProcessingPulse
        articles={articles}
        analysisArticles={filtered}
        presenter={presenter}
      />
      <div className="ranking-toolbar news-primary-filters">
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
                  a.analysis?.event_type
                    ? [
                        a.analysis.event_classification?.category ||
                          a.analysis.event_type,
                      ]
                    : [],
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
            patch({ human: "", preliminary: "" });
          }}
        >
          Limpiar
        </button>
      </div>
      <div className="ranking-toolbar">
        <label>
          Trabajo de revisión
          <select
            aria-label="Trabajo de revisión"
            value={human}
            onChange={(e) => patch({ human: e.target.value })}
          >
            <option value="">Todas las noticias</option>
            <option value="pending">Revisión pendiente</option>
            <option value="in_verification">En verificación humana</option>
            <option value="resolved">Revisión humana resuelta</option>
            <option value="dismissed">
              Asociaciones rechazadas con evidencia
            </option>
          </select>
        </label>
        {context === "rss" && (
          <label className="checkbox">
            <input
              type="checkbox"
              checked={!!preliminary}
              onChange={(e) =>
                patch({ preliminary: e.target.checked ? "yes" : "" })
              }
            />
            Con indicios preliminares de cartera · no confirma exposición
          </label>
        )}
      </div>
      <p className="small-note" role="status">
        {filtered.length} de {articles.length} noticias
      </p>
      {context === "rss" && presenter && <RssTriage articles={filtered} />}
      {filtered.length ? (
        <NewsList articles={filtered} presenter={presenter} />
      ) : (
        <Empty
          title={articles.length ? "Sin coincidencias" : "Aún no hay noticias"}
        >
          {articles.length
            ? "Prueba otra fuente o limpia los filtros para ver todas las noticias."
            : "Consulta los RSS o importa un lote desde la vista de presentador."}
        </Empty>
      )}
    </section>
  );
}
function ArticleDetail({ context, presenter, action, suppliers = [] }: any) {
  const { id } = useParams();
  const articleLocation = useLocation();
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
    return error ? (
      <section className="card detail-card" role="alert">
        <p>{error}</p>
        <button className="button" onClick={() => window.location.reload()}>
          Recuperar noticia
        </button>
      </section>
    ) : (
      <LoadingBlock label="Cargando noticia y evidencia…" />
    );
  const renderAssessment = (
    s: NonNullable<Article["analysis"]>["assessments"][number],
  ) => (
    <div className="assessment" key={s.supplier_id}>
      <Link
        to={scopedPath(
          "/proveedores/" + s.supplier_id,
          a.split === "rss" ? "rss" : "exercise",
        )}
      >
        {suppliers.find((p: Supplier) => p.supplier_id === s.supplier_id)
          ?.name || s.supplier_id}
      </Link>
      <Score value={s.priority} />
      <BuyerDecision
        assessment={s}
        impactStateUncertain={a.analysis?.context_notes?.includes(
          "impact_state_local_uncertainty:" + s.supplier_id,
        )}
      />
      <span>
        {s.needs_review ? "Propuesta por confirmar · " : ""}
        {presenter
          ? `Vínculo ${s.p_link == null ? "no estimado" : number(s.p_link * 100) + "%"} · `
          : ""}
        {riskLabel(s.is_risk)} · {urgencyLabel(s.urgent)}
      </span>
      {presenter && s.p_candidate != null && (
        <small>
          Candidatura inicial: {number(s.p_candidate * 100)}% · Asociación
          final:{" "}
          {s.association_status === "confirmed"
            ? "Sustentada"
            : s.association_status === "excluded"
              ? "Exclusión sustentada"
              : "Por confirmar"}{" "}
          · {s.geography_version}
        </small>
      )}
      {presenter && s.p_identity != null && (
        <small>
          Señal de identidad: {number(s.p_identity * 100)}% · Compatibilidad de
          exposición: {number((s.p_exposure || 0) * 100)}%. La asociación puede
          indicar identidad o exposición potencial; no confirma afectación
          individual ni embarques de Helixa. Cartera simulada.
        </small>
      )}
      {s.needs_review && <Badge tone="warning">Requiere revisión</Badge>}
      {s.review_reasons.map((r) => (
        <small key={r}>{reviewLabel(r)}</small>
      ))}
    </div>
  );
  const accepted =
    a.analysis?.assessments.filter((s) =>
      a.analysis!.affected_supplier_ids.includes(s.supplier_id),
    ) || [];
  const uncertain =
    a.analysis?.assessments.filter(
      (s) =>
        !a.analysis!.affected_supplier_ids.includes(s.supplier_id) &&
        s.needs_review,
    ) || [];
  const excluded =
    a.analysis?.assessments.filter(
      (s) =>
        !a.analysis!.affected_supplier_ids.includes(s.supplier_id) &&
        !s.needs_review,
    ) || [];
  return (
    <section className="card detail-card">
      <Link
        className="text-link"
        to={scopedPath("/noticias", a.split === "rss" ? "rss" : "exercise")}
        state={{ restoreNews: articleLocation.state?.newsFromList === true }}
      >
        ← Noticias
      </Link>
      <div className="inline">
        <Badge>{label(a.state)}</Badge>
        <EventTag analysis={a.analysis} state={a.state} />
        <span>
          {a.source} · {date(a.published_date)}
        </span>
      </div>
      <h2>{a.headline}</h2>
      <small>Origen: {a.origin_label || a.source}</small>
      {(a as any).human_review?.state === "resolved" && (
        <p className="notice">
          Revisión humana resuelta. La lectura de JEV que se conserva abajo es
          su predicción original; consulta las decisiones operativas y su
          procedencia en «Resolver la revisión».
        </p>
      )}
      <p className="article-summary">{a.summary}</p>
      {(a as any).human_review?.decisions?.length > 0 && (
        <section className="notice" aria-label="Decisiones operativas humanas">
          <strong>Decisiones humanas · separadas de JEV</strong>
          {(a as any).human_review.decisions.map((d: any) => (
            <p key={d.supplier_id}>
              {suppliers.find((s: any) => s.supplier_id === d.supplier_id)
                ?.name || d.supplier_id}
              :{" "}
              {d.association === "rejected"
                ? "asociación rechazada"
                : d.association === "unknown"
                  ? "en verificación; falta información"
                  : `asociación confirmada · ${d.risk === "Y" ? "riesgo detectado" : "sin riesgo"} · ${d.urgent === "Y" ? "acción inmediata" : "seguimiento no urgente"}`}
              .
            </p>
          ))}
        </section>
      )}
      <section className="article-decision" aria-label="Lectura para compras">
        <strong>
          {!a.analysis
            ? "Noticia pendiente de análisis"
            : a.analysis.analysis_status === "error"
              ? "Sin decisión disponible"
              : a.analysis.analysis_status === "review"
                ? "Exposición por revisar"
                : a.analysis.is_risk === "Y"
                  ? a.analysis.urgent === "Y"
                    ? "Atención de compras inmediata"
                    : "Seguimiento de continuidad"
                  : a.analysis.affected_supplier_ids.length
                    ? "Proveedor identificado · sin amenaza detectada"
                    : "Sin vínculo sustentado con esta cartera"}
        </strong>
        <p>
          {!a.analysis
            ? "Completa el análisis antes de concluir sobre el riesgo de esta noticia."
            : a.analysis.analysis_status === "error"
              ? "El error no se convierte en una decisión sin riesgo. Revisa el diagnóstico antes de reintentar."
              : a.analysis.analysis_status === "review"
                ? "Revisa la evidencia y los datos que faltan antes de decidir medidas. Puedes preparar una consulta para confirmar exposición."
                : a.analysis.is_risk === "Y"
                  ? "Consulta alcance y plazos con el proveedor usando la evidencia; no presupongas entregas afectadas ni capacidad del alternativo."
                  : a.analysis.affected_supplier_ids.length
                    ? "Conserva la fuente y su fecha para seguimiento. La identificación de un proveedor no demuestra interrupción de suministro."
                    : "El análisis no ha vinculado la noticia a un proveedor. Una consulta manual debe explicar por qué podría ser relevante y qué falta por confirmar."}
        </p>
        {a.review_scope && (
          <small>
            Revisión no obligatoria: {a.review_scope.rule} Dudas del modelo
            conservadas:{" "}
            {a.review_scope.reasons.map(reviewLabel).join(", ") || "—"}.
          </small>
        )}
        {a.analysis && (
          <ReviewGuidance analysis={a.analysis} suppliers={suppliers} />
        )}
        {a.split === "rss" && (
          <small>
            Noticias reales · exposición potencial de una cartera ficticia, sin
            confirmación de afectación individual.
          </small>
        )}
      </section>
      {presenter && a.split === "rss" && <VerificationDraft article={a} />}
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
            Observaciones no bloqueantes ({a.analysis.context_notes.length})
          </summary>
          <p>
            Estas dudas descriptivas no cambian por sí solas la decisión ni
            autorizan una alarma.
          </p>
          {a.analysis.context_notes.map((r) => (
            <p key={r}>
              {names[r.split(":")[0]] ||
                "Observación descriptiva; no bloquea por sí sola la decisión"}
              {r.includes(":") ? " · " + r.split(":")[1] : ""}
            </p>
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
      {presenter && !["error", "superseded"].includes(a.state) && (
        <RssArticleAnalysis article={a} />
      )}

      {a.state === "error" && presenter && (
        <RetryAnalysis article={a} action={action} />
      )}

      {presenter && <HumanReview article={a} suppliers={suppliers} />}
      {presenter && <AnalysisHistory article={a} />}
      {presenter && a.split === "rss" && <ComparisonControl article={a} />}
      {a.url && /^https?:\/\//.test(a.url) && (
        <a className="button" href={a.url} target="_blank" rel="noreferrer">
          Abrir fuente original <ArrowUpRight size={16} />
        </a>
      )}
      {a.analysis ? (
        <>
          {!a.analysis.review_details?.length &&
            a.analysis.review_reasons.length > 0 && (
              <details>
                <summary>
                  Motivos registrados por el motor (
                  {a.analysis.review_reasons.length})
                </summary>
                {a.analysis.review_reasons.map((r) => (
                  <p className="notice warning" key={r}>
                    {reviewLabel(r)}
                  </p>
                ))}
              </details>
            )}
          <div className="event-classification">
            <strong>
              Tipo de evento:{" "}
              {a.analysis.event_classification?.label_es ||
                label(a.analysis.event_type || "other")}
            </strong>
            <span>
              Confianza de clasificación:{" "}
              {a.analysis.event_classification?.confidence != null ||
              a.event_type_confidence != null
                ? number(
                    (a.analysis.event_classification?.confidence ??
                      a.event_type_confidence!) * 100,
                  ) + "%"
                : "no registrada"}
            </span>
            <small>
              La categoría describe el suceso; no demuestra riesgo, urgencia ni
              exposición de un proveedor. Una confianza baja indica duda entre
              categorías.
            </small>
          </div>

          {presenter && !!a.analysis.review_details?.length && (
            <details>
              <summary>Revisión por campo y relevancia</summary>
              {a.analysis.review_details.map((d, index) => (
                <div className="diagnostic-cause" key={index}>
                  <strong>
                    {reviewLabel(
                      d.code + (d.supplier_id ? ":" + d.supplier_id : ""),
                    )}
                  </strong>
                  <p>
                    {d.requires_review
                      ? "Requiere revisión"
                      : d.resolution
                        ? "Soporte comprobado · no bloquea la decisión"
                        : d.relevance === "priority"
                          ? "Advertencia de prioridad · no bloquea riesgo o urgencia"
                          : "Observación auxiliar · no bloquea la decisión"}{" "}
                    ·{" "}
                    {
                      (
                        {
                          association: "Asociación",
                          risk: "Riesgo",
                          urgency: "Urgencia",
                          priority: "Prioridad",
                          auxiliary: "Campo auxiliar",
                        } as Record<string, string>
                      )[d.relevance]
                    }
                  </p>
                  {d.requires_review && d.resolution_hint && (
                    <p className="review-next-step">{d.resolution_hint}</p>
                  )}
                  <small>
                    Campo: {d.field} · Valor:{" "}
                    {typeof d.value === "number"
                      ? d.value.toLocaleString("es-ES", {
                          maximumFractionDigits: 3,
                        })
                      : (d.value ?? "No disponible")}
                    {d.threshold != null ? " · Umbral: " + d.threshold : ""}
                  </small>
                </div>
              ))}
            </details>
          )}
          {a.analysis.assessments.some((s) => s.evidence_ids.length > 0) && (
            <h3>Evidencia literal</h3>
          )}
          {a.analysis.evidence
            .filter((e) =>
              a.analysis!.assessments.some((s) =>
                s.evidence_ids.includes(e.id),
              ),
            )
            .map((e) => (
              <blockquote key={e.id}>{e.text}</blockquote>
            ))}
          {a.analysis.assessments.length > 0 && (
            <h3>Evaluación por proveedor</h3>
          )}
          {accepted.map(renderAssessment)}
          {!accepted.length && (
            <p className="small-note">
              No hay proveedores vinculados por la decisión actual. Las
              hipótesis siguientes no son afectaciones confirmadas.
            </p>
          )}
          {uncertain.length > 0 && (
            <details className="association-group" id="provider-hypotheses">
              <summary>
                {uncertain.length}{" "}
                {uncertain.length === 1
                  ? "hipótesis de proveedor por confirmar"
                  : "hipótesis de proveedores por confirmar"}
              </summary>
              <p>
                Falta soporte para confirmar o descartar estos vínculos.
                Consulta los datos pendientes antes de decidir; una exclusión
                incierta puede ocultar una exposición relevante.
              </p>
              {uncertain.map(renderAssessment)}
            </details>
          )}
          {excluded.length > 0 && (
            <details className="association-group">
              <summary>
                {excluded.length}{" "}
                {excluded.length === 1
                  ? "candidato descartado"
                  : "candidatos descartados"}{" "}
                · sin revisión pendiente
              </summary>
              {excluded.map(renderAssessment)}
            </details>
          )}
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
              const accepted = await action(
                () =>
                  api("/articles/" + article.id + "/retry", {
                    method: "POST",
                    body: JSON.stringify({ reason }),
                  }).then((r) => {
                    window.dispatchEvent(
                      new CustomEvent("radar:analysis-queued", {
                        detail: { article_id: article.id, job_id: r.job_id },
                      }),
                    );
                    return r;
                  }),
                "Diagnóstico registrado. Ejecución encolada con historial y consumo conservados.",
              );
              if (accepted) setOpen(false);
            }}
          >
            <p>
              Indica la corrección realizada sin incluir credenciales. Los
              intentos agotados no se reinician. Si el perfil se actualizó, se
              crea una ejecución nueva y se conserva la anterior.
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
  const detailLocation = useLocation();
  const origin = new URLSearchParams(detailLocation.search).get("origen") || "";
  const { id } = useParams();
  const [s, setS] = useState<Supplier | null>(null),
    [draft, setDraft] = useState<{ id: string; text: string } | null>(null),
    [error, setError] = useState(""),
    [draftMessage, setDraftMessage] = useState(""),
    [assist, setAssist] = useState(false),
    [resolution, setResolution] = useState<string | null>(null),
    [reason, setReason] = useState(""),
    [resolving, setResolving] = useState(false),
    [resolutionError, setResolutionError] = useState("");
  useEffect(() => {
    let active = true,
      inFlight = false;
    setS(null);
    setError("");
    async function load() {
      if (inFlight) return;
      inFlight = true;
      try {
        const next = await api(
          "/suppliers/" +
            id +
            "?context=" +
            context +
            (origin ? "&origin=" + encodeURIComponent(origin) : ""),
        );
        if (active) {
          setS(next);
          setError("");
        }
      } catch (e) {
        if (active) setError((e as Error).message);
      } finally {
        inFlight = false;
      }
    }
    void load();
    const timer = setInterval(() => {
      if (!document.hidden) void load();
    }, 5000);
    window.addEventListener("focus", load);
    return () => {
      active = false;
      clearInterval(timer);
      window.removeEventListener("focus", load);
    };
  }, [id, context, origin]);
  async function create(kind: string, iid: string) {
    try {
      const d = await api("/drafts", {
        method: "POST",
        body: JSON.stringify({ supplier_id: id, incident_id: iid, kind, assist }),
      });
      setDraftMessage(
        d.llm_error ||
          (d.writer === "claude"
            ? "Redactado con IA en el idioma del destinatario. Revísalo antes de usarlo."
            : ""),
      );
      setDraft(d);
      window.dispatchEvent(
        new CustomEvent("radar:incident-drafts", { detail: iid }),
      );
    } catch (e) {
      setError((e as Error).message);
    }
  }
  if (!s)
    return error ? (
      <section className="card detail-card" role="alert">
        <p>{error}</p>
        <button className="button" onClick={() => window.location.reload()}>
          Recargar ficha
        </button>
      </section>
    ) : (
      <LoadingBlock label="Cargando proveedor y evidencias…" />
    );
  return (
    <>
      <Link className="text-link" to={scopedPath("/proveedores", context)}>
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
        <section
          className="procurement-detail"
          aria-label="Decisión de suministro"
        >
          {/* Open incidents carry their own action plan below. */}
          {(() => {
            const planned = s.incidents.some((i) => i.state !== "resolved");
            return (
              <>
                <h3>{planned ? "Impacto" : "Impacto y siguiente acción"}</h3>
                <ProcurementBrief supplier={s} context={context} hideNext={planned} />
              </>
            );
          })()}
        </section>
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
                      {i.state === "superseded"
                        ? "Análisis sustituido"
                        : label(i.state)}
                    </Badge>
                    <EventTag analysis={i.event_tag} state="unavailable" />
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
                      <div
                        key={n}
                        className={
                          h.superseded ? "superseded-evidence" : undefined
                        }
                      >
                        {h.superseded && (
                          <p className="notice">
                            Evaluación anterior sustituida. Se conserva como
                            historial; no acredita el estado actual ni una
                            recuperación.
                          </p>
                        )}
                        {presenter && h.analysis_profile && (
                          <small>
                            Perfil: {h.analysis_profile} · Ejecución{" "}
                            {(h.generation || 0) + 1}
                          </small>
                        )}
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
                          Vínculo JEV{" "}
                          {h.assessment?.p_link == null
                            ? "no estimado"
                            : number(h.assessment.p_link * 100) + "%"}{" "}
                          · Severidad {number(h.assessment?.severity)} / 10
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
                  {i.state !== "resolved" && (
                    <ActionPlan incidentId={i.id} presenter={presenter} />
                  )}
                  {presenter && <IncidentWorkspace incidentId={i.id} />}
                  <small>
                    Máximo histórico: {number(i.historical_priority)} / 100
                  </small>
                  <div className="inline">
                    <AsyncButton
                      className="button primary"
                      disabled={!presenter}
                      busyLabel="Preparando borrador…"
                      onAction={() => create("supplier", i.id)}
                    >
                      Consultar proveedor
                    </AsyncButton>
                    <AsyncButton
                      className="button"
                      disabled={!presenter || !s.alternate_id}
                      busyLabel="Preparando borrador…"
                      onAction={() => create("alternate", i.id)}
                    >
                      Consultar alternativo
                    </AsyncButton>
                    <button
                      type="button"
                      className={"ai-toggle" + (assist ? " on" : "")}
                      aria-pressed={assist}
                      disabled={!presenter}
                      title="Las consultas se redactan con IA en el idioma del destinatario; si falla, se usa la plantilla."
                      onClick={() => setAssist(!assist)}
                    >
                      <span className="ai-toggle-track" aria-hidden>
                        <span className="ai-toggle-knob" />
                      </span>
                      <Sparkles size={15} aria-hidden />
                      Redactar con IA
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
              <Empty title="Sin incidentes registrados">
                Revisa las noticias disponibles y si existe evidencia de
                exposición; no se presume afectación.
              </Empty>
            )}
            {presenter && context === "rss" && (
              <SupplierVerificationList supplierId={s.supplier_id} />
            )}
            <h3>Noticias relacionadas por el análisis</h3>
            <NewsList articles={s.articles || []} presenter={presenter} />
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
              {s.geography && (
                <details>
                  <summary>Geografía con procedencia</summary>
                  <p>
                    {s.geography.version} ·{" "}
                    {s.geography.status === "ambiguous"
                      ? "Varias coincidencias del lugar"
                      : s.geography.status === "matched"
                        ? "Lugar encontrado"
                        : "Ubicación sin resolver"}
                  </p>
                  {s.geography.places.map((p, i) => (
                    <p key={i}>
                      <a href={p.source_url} target="_blank" rel="noreferrer">
                        {p.name}
                        {p.admin1 ? " · " + p.admin1.name : ""} · GeoNames ↗
                      </a>
                    </p>
                  ))}
                  <small>
                    Coincidencias de la ciudad del catálogo, no plantas
                    verificadas ni ubicaciones adicionales del proveedor. No se
                    elige una alternativa por población.
                  </small>
                </details>
              )}
              <h3>Materiales mapeados</h3>
              {s.materials.length ? (
                s.materials.map((m) => (
                  <p key={m.material_id}>
                    <Link
                      className="text-link"
                      to={scopedPath("/materiales/" + m.material_id, context)}
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
              <h3>Alternativo registrado</h3>
              {s.alternate ? (
                <>
                  <Link
                    to={scopedPath(
                      "/proveedores/" + s.alternate.supplier_id,
                      context,
                    )}
                  >
                    {s.alternate.name}
                  </Link>
                  <p>
                    {s.alternate.city}, {s.alternate.country}
                  </p>
                  <p>
                    Oferta registrada: {s.alternate.material || "No informada"}
                  </p>
                  <p className="small-note">
                    Confirmar adecuación para este material o servicio,
                    capacidad disponible y plazo de esta consulta.
                  </p>
                  <Badge tone="warning">Stock sin confirmar</Badge>
                </>
              ) : (
                <p>Sin alternativo registrado</p>
              )}
            </div>
          </aside>
        </div>
      </section>
      {(s as any).review_work?.length > 0 && (
        <section className="card">
          <h3>Revisiones pendientes de este proveedor</h3>
          <p>
            Estas noticias conservan dudas operativas; una revisión de otra
            noticia no las cierra automáticamente.
          </p>
          {(s as any).review_work.map((w: any) => (
            <p key={w.article_id}>
              <Link
                className="text-link"
                to={scopedPath("/noticias/" + w.article_id, context)}
              >
                {w.headline} → Resolver revisión
              </Link>
            </p>
          ))}
        </section>
      )}
      {resolution && (
        <Modal title="Resolver incidente" close={() => setResolution(null)}>
          <form
            className="modal-body"
            onSubmit={async (e) => {
              e.preventDefault();
              if (resolving) return;
              setResolving(true);
              setResolutionError("");
              try {
                await api("/incidents/" + resolution + "/resolve", {
                  method: "POST",
                  body: JSON.stringify({ reason }),
                });
                setResolution(null);
                setS(await api("/suppliers/" + id + "?context=" + context));
                refresh();
              } catch (e) {
                setResolutionError((e as Error).message);
              } finally {
                setResolving(false);
              }
            }}
          >
            {resolutionError && <p role="alert">{resolutionError}</p>}
            <label htmlFor="reason">Motivo y evidencia de resolución</label>
            <textarea
              id="reason"
              minLength={8}
              maxLength={2000}
              required
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <button
              className="button primary"
              type="submit"
              disabled={resolving}
              aria-busy={resolving}
            >
              {resolving ? "Guardando resolución…" : "Registrar resolución"}
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
            {draftMessage && <p role="status">{draftMessage}</p>}
            <label htmlFor="draft">Texto de la consulta</label>
            <textarea
              id="draft"
              rows={15}
              value={draft.text}
              onChange={(e) => setDraft({ ...draft, text: e.target.value })}
            />
            <div className="inline">
              <AsyncButton
                className="button primary"
                busyLabel="Guardando…"
                onAction={async () => {
                  await api("/drafts/" + draft.id, {
                    method: "PATCH",
                    body: JSON.stringify({ text: draft.text }),
                  });
                  setDraftMessage("Borrador guardado.");
                }}
              >
                Guardar
              </AsyncButton>
              <button
                className="button"
                onClick={() =>
                  navigator.clipboard
                    .writeText(draft.text)
                    .then(() =>
                      setDraftMessage("Texto copiado al portapapeles."),
                    )
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
  const materialLocation = useLocation();
  const context =
    new URLSearchParams(materialLocation.search).get("context") === "rss"
      ? "rss"
      : "exercise";
  const { id } = useParams();
  const [m, setM] = useState<Material | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setM(null);
    setError("");
    api<Material>("/materials/" + id)
      .then((value) => {
        if (active) setM(value);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [id]);
  if (!m)
    return error ? (
      <section className="card detail-card" role="alert">
        <h2>No se pudo cargar el material</h2>
        <p>{error}</p>
        <button className="button" onClick={() => window.location.reload()}>
          Reintentar carga
        </button>
        <Link className="text-link" to={scopedPath("/materiales", context)}>
          Volver al catálogo
        </Link>
      </section>
    ) : (
      <LoadingBlock label="Cargando material y proveedores…" />
    );
  return (
    <section className="card detail-card">
      <Link className="text-link" to={scopedPath("/materiales", context)}>
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
              <Link
                className="text-link"
                to={scopedPath("/proveedores/" + m.primary_id, context)}
              >
                {m.primary.name}
              </Link>
            ) : (
              <p>No informado</p>
            )}
          </div>
          <div className="fact-box">
            <h3>Alternativo registrado</h3>
            {m.alternate ? (
              <>
                <Link
                  className="text-link"
                  to={scopedPath("/proveedores/" + m.alternate_id, context)}
                >
                  {m.alternate.name}
                </Link>
                <p>
                  Oferta registrada: {m.alternate.material || "No informada"}
                </p>
                <p className="small-note">
                  Verificar adecuación técnica y operativa antes de
                  disponibilidad y plazo.
                </p>
                <Badge tone="warning">Stock sin confirmar</Badge>
              </>
            ) : (
              <p>Sin alternativo registrado</p>
            )}
          </div>
        </aside>
      </div>
    </section>
  );
}
function Batches({ batches, presenter, action }: any) {
  const [busy, setBusy] = useState<string | null>(null),
    [profile, setProfile] = useState(DEFAULT_ANALYSIS_PROFILE);
  return (
    <section className="card batches">
      <div className="section-heading">
        <div>
          <h2>Lotes del ejercicio</h2>
          <p>Resultados y exportaciones independientes de RSS</p>
        </div>
        <Badge>{batches.length} importados</Badge>
      </div>
      {presenter && (
        <AnalysisProfile
          value={profile}
          onChange={setProfile}
          disabled={!!busy}
        />
      )}
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
              {presenter &&
                b.analysis_profiles?.map((p) => (
                  <small key={[p.profile, p.questions, p.review].join(":")}>
                    Perfil: {p.profile} · preguntas {p.questions} · revisión{" "}
                    {p.review} · {p.count} filas
                  </small>
                ))}
              {presenter && b.mixed_profiles && (
                <p className="notice warning">
                  Este lote contiene perfiles distintos por reanálisis
                  individuales. La exportación conserva el resultado actual de
                  cada fila; no representa la evaluación de un único perfil.
                </p>
              )}
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
                          body: JSON.stringify({ analysis_profile: profile }),
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
              <AsyncButton
                disabled={!presenter || b.done !== b.count || b.errors > 0}
                onAction={() =>
                  downloadFile(
                    "/api/batches/" + b.id + "/export.xlsx",
                    (b.filename || "resultados") + ".xlsx",
                  )
                }
                busyLabel="Preparando descarga…"
                successLabel="Archivo preparado. Comprueba las descargas del navegador."
              >
                <Download size={16} />
                Exportar
              </AsyncButton>
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
function Analytics({
  overview,
  articles = [],
  suppliers,
  sources,
  batches,
  context,
  ...shared
}: any) {
  const data = sources.map((s: Source) => ({
    name: s.name,
    recibidas: s.received_count,
    duplicadas: s.duplicates,
  }));
  const distribution = [
    {
      name: "Sin prioridad evaluable",
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
          Ámbito: {context === "rss" ? "RSS real" : "Ejercicio"}. Estado
          almacenado vigente de {overview?.received || 0} artículos únicos;
          todas las fechas disponibles, con el origen seleccionado. No son
          recepciones de feed.
        </p>
        <div className="analytics-stats">
          {[
            ["Artículos vigentes", "received"],
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
        <PendingAnalysis articles={articles} presenter={shared.presenter} />
        <div className="charts">
          <div>
            <h3>Recepciones RSS acumuladas · ámbito global</h3>
            <p className="small-note">
              Desde el registro de cada fuente; una recepción puede repetir un
              GUID. No comparte denominador con los artículos del ejercicio ni
              mide novedades de la última consulta.{" "}
              <Link to="/fuentes?context=rss">
                Consultar artículos RSS almacenados
              </Link>
            </p>
            <div className="chart">
              <ChartBoundary>
                <React.Suspense
                  fallback={<p role="status">Cargando gráfico de fuentes…</p>}
                >
                  <SourceVolumeChart data={data} />
                </React.Suspense>
              </ChartBoundary>
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
              {suppliers.length} proveedores únicos del contexto. Sin prioridad
              evaluable no equivale a artículo sin procesar ni a prioridad baja.
            </p>
          </div>
        </div>
        <div className="analytics-stats">
          <div>
            <small>Requiere revisión</small>
            <strong>
              {overview?.review_rate != null
                ? number(overview.review_rate * 100) + "%"
                : "—"}
            </strong>
          </div>
          <div>
            <small>Cobertura automática</small>
            <strong>
              {overview?.automatic_rate != null
                ? number(overview.automatic_rate * 100) + "%"
                : "—"}
            </strong>
          </div>
        </div>
        <p>
          Ambos porcentajes usan {overview?.processed || 0} noticias procesadas.
          La tasa de revisión no mide precisión.
          {overview?.review_scope_resolved
            ? ` ${overview.review_scope_resolved} con dudas del modelo pero sin riesgo, urgencia ni proveedor implicado se cuentan como resueltas; sus motivos se conservan en cada noticia.`
            : ""}
        </p>
        {context === "rss" && (
          <div className="analytics-stats">
            {[
              ["Texto público ampliado", "public_text"],
              ["Texto parcial", "partial"],
              ["Solo resumen", "summary_only"],
              ["Lectura sin registro", "unrecorded"],
            ].map(([title, key]) => (
              <div key={key}>
                <small>{title}</small>
                <strong>{overview?.reading_coverage?.[key] || 0}</strong>
              </div>
            ))}
          </div>
        )}
        <h3>Motivos de revisión</h3>
        {overview?.review_reasons?.length ? (
          <ul className="reason-counts">
            {overview.review_reasons.slice(0, 12).map((r: any) => (
              <li key={r.reason}>
                <span>{reviewLabel(r.reason)}</span>
                <strong>{r.articles} noticias</strong>
              </li>
            ))}
          </ul>
        ) : (
          <p>No hay motivos de revisión registrados para este contexto.</p>
        )}
        <p className="small-note">
          Una noticia puede tener varios motivos; cada motivo se cuenta una vez
          por noticia. Telemetría JEV y evaluación supervisada en{" "}
          <Link to="/modelo">Modelo</Link>.
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
  const materialsLocation = useLocation();
  const context =
    new URLSearchParams(materialsLocation.search).get("context") === "rss"
      ? "rss"
      : "exercise";
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
        <Badge>
          {loading
            ? "Cargando catálogo…"
            : error
              ? "Catálogo no disponible"
              : `${materials.length} materiales`}
        </Badge>
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
        <LoadingBlock label="Cargando materiales…" />
      ) : error ? (
        <button className="button" onClick={() => window.location.reload()}>
          Reintentar carga
        </button>
      ) : rows.length ? (
        <div className="materials-grid">
          {rows.map((m) => (
            <article className="source-card" key={m.material_id}>
              <div className="eyebrow">
                {m.material_id} · {m.category}
              </div>
              <h3>
                <Link
                  className="text-link"
                  to={scopedPath("/materiales/" + m.material_id, context)}
                >
                  {m.name}
                </Link>
              </h3>
              <p className="material-exposure">
                {supplier(m.primary_id)?.incident_count
                  ? `${supplier(m.primary_id)?.incident_count} incidentes activos del proveedor principal · exposición por contrastar para este material`
                  : "Sin incidentes activos vinculados al principal en este contexto"}
              </p>
              <p>
                Cobertura:{" "}
                {supplier(m.primary_id)?.inventory_days == null
                  ? "No informada"
                  : supplier(m.primary_id)?.inventory_days + " días"}{" "}
                · Lead time:{" "}
                {supplier(m.primary_id)?.lead_days == null
                  ? "No informado"
                  : supplier(m.primary_id)?.lead_days + " días"}
              </p>
              <p>
                {m.alternate_id
                  ? `Alternativo: ${supplier(m.alternate_id)?.name || m.alternate_id} · confirmar adecuación, capacidad y plazo`
                  : "Sin alternativo registrado"}
              </p>
              <p>
                Necesidad mensual:{" "}
                <strong>
                  {number(m.monthly_requirement)} {m.unit}
                </strong>
              </p>
              <p>
                Proveedor principal:{" "}
                <Link
                  className="text-link"
                  to={scopedPath("/proveedores/" + m.primary_id, context)}
                >
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
                to={scopedPath("/materiales/" + m.material_id, context)}
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

function SourcesPage({
  sources,
  config,
  presenter,
  refresh,
  onRss,
  context,
}: any) {
  const [worker, setWorker] = useState<any>(null),
    [stream, setStream] = useState<Article[]>([]),
    [submitting, setSubmitting] = useState(false),
    [notice, setNotice] = useState(""),
    [error, setError] = useState(""),
    [streamLoading, setStreamLoading] = useState(true),
    [loadError, setLoadError] = useState("");
  const baseline = useRef<Set<string> | null>(null);
  const pendingCount = stream.filter((a) => a.state === "pending").length;
  useEffect(() => {
    let active = true,
      inFlight = false;
    async function load() {
      if (inFlight) return;
      inFlight = true;
      try {
        const [w, rows] = await Promise.all([
          api("/worker"),
          api<Article[]>("/articles?context=rss"),
        ]);
        if (active) {
          setLoadError("");
          setWorker(w);
          setStream(rows);
          baseline.current ??= new Set(rows.map((a) => a.id));
        }
      } catch (e) {
        if (active) setLoadError((e as Error).message);
      } finally {
        inFlight = false;
        if (active) setStreamLoading(false);
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
      {loadError && (
        <p role="alert" className="notice error">
          Bandeja RSS: {loadError}.{" "}
          {stream.length
            ? "Se conservan los últimos datos consultados; no son una consulta reciente."
            : "No se conoce el total almacenado."}
        </p>
      )}
      {context !== "rss" && (
        <div className="notice info">
          Estás en Ejercicio. Esta sección muestra siempre las seis fuentes y
          noticias RSS reales, separadas de los archivos.{" "}
          <Link to="/noticias?context=rss" onClick={onRss}>
            Abrir bandeja RSS
          </Link>
        </div>
      )}
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
          <strong>
            {streamLoading
              ? "Cargando artículos…"
              : loadError && !stream.length
                ? "Total RSS no disponible"
                : `${stream.length} artículos RSS únicos almacenados`}
          </strong>
          <span>
            {newCount} incorporaciones observadas desde esta visita o
            actualización · no es el total acumulado
          </span>
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
                <strong>{s.item_count}</strong> versiones incorporadas en última
                consulta · HTTP {s.http_status || "—"}
              </div>
              <p>
                {(s as any).stored_unique ?? "—"} artículos únicos ·{" "}
                {(s as any).stored_versions ?? "—"} versiones almacenadas
              </p>
              <p className="small-note">
                Acumulado: {s.received_count} recepciones elegibles ·{" "}
                {s.duplicates} duplicadas
              </p>
              <Link
                className="text-link"
                to={"/noticias?context=rss"}
                onClick={onRss}
              >
                Consultar noticias RSS
              </Link>
              {s.error && <p className="error-text">{s.error}</p>}
            </article>
          ))}
        </div>
      </section>
      {presenter && (
        <section className="card detail-card">
          <h2>Analizar y revisar noticias RSS</h2>
          <PendingAnalysis articles={stream} presenter={presenter} />
          <p>
            {streamLoading
              ? "Consultando pendientes…"
              : loadError
                ? "No se conoce el número actual de pendientes."
                : pendingCount
                  ? `${pendingCount} noticias pendientes de analizar. Selecciona hasta diez y revisa su alcance y perfil antes de iniciar.`
                  : "No hay noticias pendientes de analizar. Puedes consultar resultados y resolver revisiones en la bandeja."}
          </p>
          <Link
            className="button primary"
            to="/noticias?context=rss"
            onClick={onRss}
          >
            {pendingCount
              ? "Seleccionar noticias y perfil"
              : "Consultar resultados RSS"}
          </Link>
        </section>
      )}
      <section className="card detail-card">
        <div className="section-heading">
          <div>
            <h2>Noticias que van llegando</h2>
            <p>
              Artículos únicos por fuente y GUID · versiones vigentes · fuente y
              fecha de publicación conservadas
            </p>
          </div>
          <Link
            className="text-link"
            to="/noticias?context=rss"
            onClick={onRss}
          >
            Ver noticias
          </Link>
        </div>
        {streamLoading ? (
          <p role="status">Cargando noticias RSS almacenadas…</p>
        ) : loadError && !stream.length ? (
          <p role="alert">
            No se pudo consultar la bandeja. Los estados de fuente no prueban
            que esté vacía.
          </p>
        ) : !stream.length ? (
          <p>
            No hay artículos RSS almacenados. Actualizar consulta las fuentes;
            una respuesta sin novedades no crea noticias. Revisa fechas y estado
            de cada fuente.
          </p>
        ) : (
          <NewsList
            articles={stream.slice(0, 12)}
            presenter={presenter}
            onOpen={onRss}
          />
        )}
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
    [analysisProfile, setAnalysisProfile] = useState(DEFAULT_ANALYSIS_PROFILE),
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
    setAnalysisProfile(DEFAULT_ANALYSIS_PROFILE);
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
            {mode === "rerun" && (
              <label>
                Perfil del ejercicio
                <select
                  aria-label="Perfil del ejercicio"
                  value={analysisProfile}
                  onChange={(e) => {
                    invalidate();
                    setAnalysisProfile(e.target.value);
                  }}
                  disabled={busy}
                >
                  <option value="1.0.0">
                    1.0.0 · anterior / rollback (RSS 2.2)
                  </option>
                  <option value="link-2.2.0">
                    link-2.2.0 · vínculo y revisión experimental
                  </option>
                  <option value={CANDIDATE}>
                    Perfil actual · 3.4.2 / revisión 1.3.1
                  </option>
                </select>
                <small>
                  Conserva versiones anteriores y borradores. El perfil actual
                  se aplica también al RSS seleccionado; 1.0 conserva el motor
                  RSS actual. Validación inspeccionada: comparación
                  retrospectiva. No ejecutar Test/LiveDay como desarrollo.
                </small>
              </label>
            )}
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
                setPreview(null);
                try {
                  const result = await api("/demo/preview", {
                    method: "POST",
                    body: JSON.stringify({
                      selection,
                      mode,
                      analysis_profile: analysisProfile,
                    }),
                  });
                  if (
                    mode === "rerun" &&
                    analysisProfile !== "1.0.0" &&
                    result.analysis_profile !== analysisProfile
                  )
                    throw new Error(
                      "El servidor no confirmó el perfil elegido. Actualiza la página antes de continuar.",
                    );
                  setPreview(result);
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
                {mode === "rerun" && (
                  <p>
                    Perfil del ejercicio confirmado:{" "}
                    <strong>{preview.analysis_profile || "1.0.0"}</strong>. RSS
                    conserva su propio perfil.
                  </p>
                )}
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
                <EventTag analysis={b} />
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
              Se ejecutarán tres análisis nuevos del perfil actual 3.4.2, con
              sus etapas condicionales y reintentos acotados: hasta 108
              peticiones en total. Se registran las peticiones reales. Los
              contrastes ya encolados conservan su configuración original.
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
        <details key={r.id || `${r.generation}:${r.created_at}`}>
          <summary>
            Análisis {r.generation + 1} · {date(r.created_at)} ·{" "}
            {label(r.result.analysis_status)} <EventTag analysis={r.result} />
          </summary>
          <p className="run-versions">
            Perfil:{" "}
            {r.result.analysis_profile ||
              r.result.question_version ||
              "No registrado"}{" "}
            · Preguntas: {r.result.question_version} · Revisión:{" "}
            {r.result.analysis_versions?.review ||
              r.result.review_policy_version ||
              "Política original"}
          </p>
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

function FollowupDesk({ suppliers, context, reviewCount }: any) {
  const tasks = suppliers
    .flatMap((s: any) =>
      (s.incidents || []).map((i: any) => ({
        supplier: s,
        incident: i,
        work: i.procurement_work,
      })),
    )
    .filter((x: any) => x.work && x.work.status !== "done")
    .sort((a: any, b: any) =>
      (a.work.due_date || "9999").localeCompare(b.work.due_date || "9999"),
    );
  const list = (rows: any[]) =>
    rows.map((x: any) => (
      <article key={x.incident.id}>
        <div>
          <strong>{x.work.action}</strong>
          <p>
            {x.supplier.name} ·{" "}
            {x.work.due_date
              ? "Fecha: " + x.work.due_date
              : "Sin fecha asignada"}{" "}
            ·{" "}
            {x.work.status === "verifying"
              ? "En verificación"
              : x.work.status === "followup"
                ? "Seguimiento"
                : "Pendiente"}
          </p>
        </div>
        <Link
          className="text-link"
          to={scopedPath("/proveedores/" + x.supplier.supplier_id, context)}
        >
          Gestionar acción
        </Link>
      </article>
    ));
  return (
    <section className="card daily-work">
      <div className="section-heading">
        <div>
          <h2>Trabajo pendiente</h2>
          <p>
            Seguimientos por fecha ascendente; sin fecha al final. Completar una
            acción no declara recuperación.
          </p>
        </div>
        <Link className="text-link" to={scopedPath("/noticias", context)}>
          {reviewCount} revisiones pendientes →
        </Link>
      </div>
      {tasks.length ? (
        list(tasks.slice(0, 3))
      ) : (
        <p>
          No hay seguimientos registrados pendientes en este ámbito. Abre un
          incidente para definir la siguiente acción.
        </p>
      )}
      {tasks.length > 3 && (
        <details>
          <summary>Ver los {tasks.length} seguimientos</summary>
          {list(tasks.slice(3))}
        </details>
      )}
    </section>
  );
}

function visibleAlerts(rows: Alert[], filter: string) {
  const live = (a: Alert) =>
    a.is_current !== false && !["superseded", "resolved"].includes(a.state);
  return rows
    .filter(
      (a) =>
        filter === "all" ||
        (filter === "current" && live(a)) ||
        (filter === "history" && !live(a)) ||
        (filter === "new" && live(a) && !a.acknowledged) ||
        (filter === "ack" && a.acknowledged) ||
        (filter === "resolved" && a.state === "resolved") ||
        (filter === "superseded" && a.state === "superseded"),
    )
    .sort((a, b) =>
      filter === "current"
        ? Number(a.acknowledged) - Number(b.acknowledged) ||
          (b.priority ?? 0) - (a.priority ?? 0) ||
          b.id - a.id
        : b.id - a.id,
    );
}
