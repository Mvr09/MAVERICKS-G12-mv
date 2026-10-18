import type { EventInfo } from "./types";

export const eventNames: Record<string, string> = {
  wildfire: "Incendio forestal",
  fire_incident: "Incendio industrial o de instalaciones",
  natural_disaster: "Fenómeno natural",
  labour_strike: "Huelga o conflicto laboral",
  regulatory_action: "Medida regulatoria",
  export_restriction: "Restricción comercial o de exportación",
  financial_distress: "Dificultades financieras",
  quality_recall: "Problema de calidad o retirada",
  logistics_disruption: "Interrupción logística",
  utility_outage: "Corte de servicios básicos",
  leadership_change: "Cambio de dirección",
  acquisition: "Adquisición o cambio de propiedad",
  recovery: "Recuperación de operaciones",
  positive_news: "Mejora empresarial",
  other: "Otro evento comercial u operativo",
  not_relevant: "Sin evento de suministro",
};

export function EventTag({
  analysis,
  state,
}: {
  analysis?: EventInfo | null;
  state?: string;
}) {
  const category =
    analysis?.event_classification?.category || analysis?.event_type;
  const eventName =
    category === "natural_disaster" && analysis?.event_classification
      ? "Otro fenómeno natural"
      : category
        ? eventNames[category]
        : undefined;
  const failed = state === "error" || analysis?.analysis_status === "error";
  const uncertain = [
    ...(analysis?.context_notes || []),
    ...(analysis?.review_reasons || []),
  ].includes("event_type_confidence_low");
  const text = failed
    ? "Tipo sin determinar · Error de análisis"
    : !category
      ? state === "unavailable"
        ? "Tipo no registrado"
        : analysis
          ? "Tipo sin determinar"
          : "Tipo pendiente de análisis"
      : !eventNames[category]
        ? "Tipo no reconocido · Por confirmar"
        : eventName + (uncertain ? " · Por confirmar" : "");
  return (
    <span
      className={
        "badge event-tag " +
        (failed || uncertain || (category && !eventNames[category])
          ? "warning"
          : category
            ? "purple"
            : "neutral")
      }
      aria-label={"Tipo de noticia: " + text}
      title="Describe el suceso; no implica riesgo, urgencia ni exposición del proveedor."
    >
      {text}
    </span>
  );
}
