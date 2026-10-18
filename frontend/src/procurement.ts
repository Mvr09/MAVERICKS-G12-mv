import type { Supplier } from "./types";

/** Display-only interpretation of recorded data. Never changes decisions or scores. */
export function procurement(s: Supplier, context: string, incidentId?: string) {
  const active = s.incidents.filter(
    (i) => i.state === "active" || i.state === "monitoring",
  );
  const incident = incidentId
    ? s.incidents.find((i) => i.id === incidentId)
    : [...active].sort((a, b) => b.priority - a.priority)[0];
  const entry = incident?.history
    .filter((h) => h.assessment && !h.superseded)
    .slice()
    .sort(
      (a, b) =>
        ((b as any).published_date || "").localeCompare(
          (a as any).published_date || "",
        ) || (b.at || "").localeCompare(a.at || ""),
    )[0];
  const physical = !["Logistics", "Services"].includes(s.category);
  const inventory = !physical
    ? "Inventario no aplicable"
    : s.inventory_days == null
      ? "Inventario no informado"
      : `${s.inventory_days} días de inventario`;
  const lead =
    s.lead_days == null
      ? "Lead time no informado"
      : `${s.lead_days} días de lead time`;
  const drivers = [
    s.criticality === "High"
      ? "Criticidad alta"
      : s.criticality === "Medium"
        ? "Criticidad media"
        : s.criticality === "Low"
          ? "Criticidad baja"
          : "Criticidad no informada",
    s.single_source === "Y"
      ? "Fuente única"
      : s.single_source === "N"
        ? "Varias fuentes"
        : "Dependencia no informada",
    inventory,
    lead,
  ];
  const isResolved =
    incident?.state === "resolved" || (!incidentId && s.status === "resolved");
  const review = incidentId
    ? !!entry?.assessment?.needs_review
    : s.needs_review;
  const urgent = incidentId ? entry?.assessment?.urgent === "Y" : s.urgent;
  const superseded = incident?.state === "superseded";
  const action = superseded
    ? "Análisis anterior sustituido: consultar el último resultado antes de decidir medidas."
    : isResolved
      ? "Confirmar la normalización de entregas y conservar el historial."
      : review
        ? "Validar el vínculo y los hechos con el proveedor antes de decidir medidas."
        : urgent
          ? "Contactar al proveedor y confirmar entregas comprometidas y medidas de continuidad."
          : incident
            ? "Confirmar alcance y plazos con el proveedor; mantener seguimiento del evento."
            : s.status === "resolved"
              ? "Confirmar la normalización de entregas y conservar el historial."
              : s.status === "pending"
                ? "Analizar noticias antes de concluir sobre exposición."
                : s.status === "unlinked"
                  ? "Mantener seguimiento: las noticias procesadas no sustentan un vínculo con este proveedor."
                  : "Mantener seguimiento; sin riesgo activo detectado en las noticias procesadas.";
  const exposure = superseded
    ? "Evidencia anterior · conservada en el historial"
    : entry?.assessment?.exposure_kind === "reported"
      ? "Afectación reportada por la fuente · cartera ficticia"
      : isResolved
        ? "Evento recuperado · cartera ficticia"
        : s.status === "pending"
          ? "Exposición sin establecer"
          : context === "rss"
            ? "Exposición potencial · cartera simulada"
            : "Datos del ejercicio · cartera ficticia";
  const materials = s.materials.map((m) => ({
    ...m,
    role: m.primary_id === s.supplier_id ? "Principal" : "Alternativo",
  }));
  return {
    incident,
    entry,
    inventory,
    lead,
    drivers,
    action,
    exposure,
    materials,
    alternative: s.alternate_id
      ? "Alternativo registrado: confirmar disponibilidad, capacidad y plazo antes de recurrir a él."
      : "No hay alternativo registrado: consultar opciones aprobadas con procurement.",
    unknown:
      "La noticia y la relación de catálogo no confirman daños individuales ni entregas afectadas.",
  };
}
