import { scopedPath } from "./NewsContinuity";
import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  ArrowRight,
  FileCheck2,
  Layers3,
  Radar,
} from "lucide-react";
import type { Supplier } from "./types";
import { procurement } from "./procurement";
import { DeadlinePill, marginText, type Plan } from "./ActionPlan";
import { eventNames } from "./EventTag";

export function ProcurementBrief({
  supplier: s,
  context,
  compact = false,
  incidentId,
  hideNext = false,
}: {
  supplier: Supplier;
  context: string;
  compact?: boolean;
  incidentId?: string;
  // The action plan already shows the next action next to this brief.
  hideNext?: boolean;
}) {
  const p = procurement(s, context, incidentId);
  return (
    <div className={"procurement-brief" + (compact ? " compact" : "")}>
      <div className="procurement-exposure">
        <Radar size={15} />
        <span>{p.exposure}</span>
      </div>
      {compact && (
        <div className="procurement-drivers">
          {p.drivers.slice(0, 2).map((d) => (
            <span key={d}>{d}</span>
          ))}
        </div>
      )}
      {!compact && (
        <>
          <div className="procurement-drivers">
            {p.drivers.map((d) => (
              <span key={d}>{d}</span>
            ))}
          </div>
          <div className="procurement-links">
            <Layers3 size={17} />
            <div>
              {p.materials.length ? (
                p.materials.map((m) => (
                  <Link
                    key={m.material_id}
                    to={scopedPath("/materiales/" + m.material_id, context)}
                  >
                    {m.name} <small>· {m.role}</small>
                  </Link>
                ))
              ) : (
                <span>Materiales no mapeados</span>
              )}
              <p>
                {s.products.length
                  ? "Productos relacionados: " + s.products.join(" · ")
                  : "Productos no mapeados"}
              </p>
            </div>
          </div>
        </>
      )}
      {!hideNext && (
        <div className="procurement-next">
          <FileCheck2 size={17} />
          <div>
            <strong>Siguiente acción</strong>
            <p>{p.action}</p>
            {p.work && <small>Acción registrada: {p.work.action} · {p.work.status === "done" ? "Completada" : p.work.status === "verifying" ? "En verificación" : p.work.status === "followup" ? "Seguimiento" : "Pendiente"}{p.work.due_date ? " · " + p.work.due_date : ""}</small>}
          </div>
        </div>
      )}
      {!compact && (
        <>
          <p className="small-note">{p.alternative}</p>
          <p className="small-note">{p.unknown}</p>
        </>
      )}
      {p.entry?.article_id && (
        <Link
          className="text-link procurement-evidence"
          to={scopedPath("/noticias/" + p.entry.article_id, context)}
        >
          <ArrowUpRight size={16} />
          Ver evidencia:{" "}
          {p.entry.headline || "noticia del incidente prioritario"}
        </Link>
      )}
    </div>
  );
}

export function AttentionDesk({
  suppliers,
  context,
  origin = "",
  plans = {},
}: {
  suppliers: Supplier[];
  context: string;
  origin?: string;
  plans?: Record<string, Plan | null>;
}) {
  // The supplier's highest-priority open incident carries the plan shown on the card.
  const planOf = (s: Supplier) => {
    const top = (s.incidents ?? [])
      .filter((i) => i.state === "active" || i.state === "monitoring")
      .sort((a, b) => b.priority - a.priority)[0];
    return top ? (plans[top.id] ?? null) : null;
  };
  const attention = suppliers
    .filter((s) => s.incident_count > 0 || s.needs_review)
    .slice(0, 3);
  return (
    <section className="attention-desk" aria-labelledby="attention-title">
      <div className="section-heading">
        <div>
          <div className="eyebrow">HELIXA · MESA DE ATENCIÓN</div>
          <h2 id="attention-title">De la señal a la siguiente decisión</h2>
          <p>
            Prioridad empresarial, evidencia y acciones sobre una cartera
            ficticia.
          </p>
        </div>
        <Link className="text-link" to={scopedPath("/alertas", context)}>
          Ver alertas <ArrowRight size={16} />
        </Link>
      </div>
      {attention.length ? (
        <div className="attention-grid">
          {attention.map((s, i) => (
            <article className="attention-card" key={s.supplier_id}>
              <div className="attention-card-top">
                <span className="attention-index">0{i + 1}</span>
                <span
                  className={
                    "badge " +
                    (s.needs_review
                      ? "warning"
                      : s.urgent
                        ? "danger"
                        : "neutral")
                  }
                >
                  {s.needs_review
                    ? "Validar evidencia"
                    : s.urgent
                      ? "Atención inmediata"
                      : "Seguimiento"}
                </span>
                <strong className="attention-score">
                  {s.priority == null ? "—" : s.priority.toFixed(1)}
                  <small> / 100</small>
                </strong>
              </div>
              <Link
                className="attention-name"
                to={scopedPath(
                  "/proveedores/" +
                    s.supplier_id +
                    (origin ? "?origen=" + encodeURIComponent(origin) : ""),
                  context,
                )}
              >
                {s.name}
                <ArrowUpRight size={18} />
              </Link>
              <p className="attention-material">{s.material}</p>
              {(() => {
                const plan = planOf(s);
                if (!plan)
                  return (
                    <>
                      <p className="attention-reason">{s.reason}</p>
                      <ProcurementBrief supplier={s} context={context} compact />
                    </>
                  );
                const f = plan.facts;
                return (
                  <div className="attention-plan">
                    <div className="attention-badges">
                      {f.incidente.urgente && (
                        <span className="badge danger">Urgente</span>
                      )}
                      <span className="badge info">Decide: {plan.decision}</span>
                      {f.proveedor.criticidad && (
                        <span className="badge purple">
                          Criticidad{" "}
                          {{ High: "alta", Medium: "media", Low: "baja" }[
                            f.proveedor.criticidad
                          ] ?? f.proveedor.criticidad}
                        </span>
                      )}
                      {f.proveedor.fuente_unica && (
                        <span className="badge purple">Fuente única</span>
                      )}
                    </div>
                    {f.incidente.titular && (
                      <p className="attention-reason">
                        <strong>
                          {eventNames[f.incidente.tipo_evento ?? ""] ?? "Evento"}:
                        </strong>{" "}
                        {f.incidente.titular}
                      </p>
                    )}
                    <div className="attention-next">
                      <div className="eyebrow">Siguiente acción</div>
                      <ul>
                        {plan.actions
                          .filter((a) => a.code !== "monitor")
                          .slice(0, 2)
                          .map((a) => (
                            <li key={a.code}>
                              <DeadlinePill action={a} />
                              <span>{a.label}</span>
                            </li>
                          ))}
                      </ul>
                      <small>
                        Margen de stock: {marginText(f.stock.margen_dias)} ·
                        Productos:{" "}
                        {Array.isArray(f.productos)
                          ? f.productos.join(", ")
                          : f.productos}
                      </small>
                    </div>
                  </div>
                );
              })()}
              <Link
                className="button"
                to={scopedPath(
                  "/proveedores/" +
                    s.supplier_id +
                    (origin ? "?origen=" + encodeURIComponent(origin) : ""),
                  context,
                )}
              >
                {planOf(s) ? "Ver plan completo y borradores" : "Revisar suministro"}{" "}
                <ArrowRight size={15} />
              </Link>
            </article>
          ))}
        </div>
      ) : (
        <div className="attention-empty">
          <FileCheck2 size={24} />
          <div>
            <strong>Sin incidentes activos identificados</strong>
            <p>
              Las noticias pendientes aún necesitan análisis. Revisa las
              novedades y el estado de las fuentes.
            </p>
          </div>
          <Link className="text-link" to="/noticias">
            Explorar noticias →
          </Link>
        </div>
      )}
    </section>
  );
}
