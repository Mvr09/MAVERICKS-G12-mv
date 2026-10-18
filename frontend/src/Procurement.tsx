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

export function ProcurementBrief({
  supplier: s,
  context,
  compact = false,
  incidentId,
}: {
  supplier: Supplier;
  context: string;
  compact?: boolean;
  incidentId?: string;
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
      <div className="procurement-next">
        <FileCheck2 size={17} />
        <div>
          <strong>Siguiente acción</strong>
          <p>{p.action}</p>
        </div>
      </div>
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
}: {
  suppliers: Supplier[];
  context: string;
  origin?: string;
}) {
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
        <Link className="text-link" to="/alertas">
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
                to={
                  "/proveedores/" +
                  s.supplier_id +
                  (origin ? "?origen=" + encodeURIComponent(origin) : "")
                }
              >
                {s.name}
                <ArrowUpRight size={18} />
              </Link>
              <p className="attention-material">{s.material}</p>
              <p className="attention-reason">{s.reason}</p>
              <ProcurementBrief supplier={s} context={context} compact />
              <Link
                className="button"
                to={
                  "/proveedores/" +
                  s.supplier_id +
                  (origin ? "?origen=" + encodeURIComponent(origin) : "")
                }
              >
                Revisar suministro <ArrowRight size={15} />
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
