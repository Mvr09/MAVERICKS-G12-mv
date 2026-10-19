import type { Assessment } from "./types";

export function BuyerDecision({
  assessment: a,
  impactStateUncertain = false,
}: {
  assessment: Assessment;
  impactStateUncertain?: boolean;
}) {
  return (
    <div
      className="buyer-decision"
      aria-label={"Decisión y acción · " + a.supplier_id}
    >
      <strong>
        {a.needs_review ? "Decisión por confirmar" : "Análisis automático"}
      </strong>
      {a.exposure_kind && (
        <span className="exposure-label">
          {
            {
              reported: "Afectación reportada por la fuente",
              potential: "Exposición potencial · confirmar entregas",
              identity: "Proveedor identificado · sin amenaza detectada",
              unknown: "Vínculo por confirmar",
              excluded: "Sin exposición sustentada",
            }[a.exposure_kind]
          }
        </span>
      )}
      <p>
        {a.needs_review
          ? "Verificar las dudas indicadas antes de dar la afectación por confirmada."
          : a.urgent === "Y"
            ? "Acción inmediata: contactar al proveedor y confirmar entregas y medidas de continuidad."
            : a.is_risk === "Y"
              ? "Seguimiento de compras: confirmar alcance y evolución del riesgo."
              : "Sin acción urgente sustentada por esta noticia."}
      </p>
      {a.requires_pathway_confirmation && (
        <small>
          La compatibilidad de ubicación y actividad no prueba que una planta,
          ruta o entrega de este proveedor esté afectada. Confirmar el alcance
          con el proveedor.
        </small>
      )}
      {impactStateUncertain && (
        <small>
          Queda precisar si el impacto está activo o en seguimiento. Esta duda
          no cambia por sí sola la acción recomendada y se conserva como
          observación.
        </small>
      )}
      {a.priority_requires_review && (
        <small className="notice warning">
          Prioridad estimada: hay datos o severidad por confirmar. Esta
          advertencia no implica incertidumbre sobre el riesgo o la urgencia.
        </small>
      )}
    </div>
  );
}
