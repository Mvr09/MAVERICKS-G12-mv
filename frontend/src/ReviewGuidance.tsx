import type { Analysis, Supplier } from "./types";

export function ReviewGuidance({
  analysis,
  suppliers = [],
}: {
  analysis: Analysis;
  suppliers?: Supplier[];
}) {
  if (analysis.analysis_status !== "review") return null;
  const groups = new Map<string, Set<string>>();
  for (const d of analysis.review_details || []) {
    if (!d.requires_review) continue;
    const hint =
      d.resolution_hint ||
      (d.relevance === "association"
        ? "Confirma que la ubicación, actividad o ruta del proveedor estén dentro del alcance de la noticia."
        : d.relevance === "urgency"
          ? "Confirma el estado actual y el plazo del impacto antes de dar por sustentada una acción inmediata."
          : d.relevance === "risk"
            ? "Aclara qué operación, material o entrega amenaza el hecho publicado."
            : "Completa el dato indicado con evidencia de la fuente o del proveedor.");
    if (!groups.has(hint)) groups.set(hint, new Set());
    if (d.supplier_id)
      groups
        .get(hint)!
        .add(
          suppliers.find((s) => s.supplier_id === d.supplier_id)?.name ||
            d.supplier_id,
        );
  }
  if (!groups.size) return null;
  return (
    <section
      className="review-guidance"
      aria-label="Qué confirmar antes de decidir"
    >
      <h3>Qué confirmar antes de decidir</h3>
      <p>
        Estas dudas pueden cambiar el vínculo, el riesgo o la acción. La
        prioridad de compras y la certeza del análisis son distintas.
      </p>
      <ul>
        {[...groups].map(([hint, names]) => (
          <li key={hint}>
            <strong>{hint}</strong>
            {names.size > 0 && (
              <small>
                {[...names].slice(0, 3).join(" · ")}
                {names.size > 3 ? ` y ${names.size - 3} hipótesis más` : ""}
              </small>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
