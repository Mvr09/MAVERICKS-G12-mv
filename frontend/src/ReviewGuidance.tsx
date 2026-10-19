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
  const causes = [...(analysis.review_details || [])];
  for (const reason of analysis.review_reasons || []) {
    const [code, sid] = reason.split(":");
    if (
      !causes.some(
        (d) => d.code === code && (d.supplier_id || "") === (sid || ""),
      )
    )
      causes.push({
        code,
        supplier_id: sid || null,
        field: "legacy",
        relevance: "unknown",
        requires_review: true,
        value: null,
        threshold: null,
      });
  }
  for (const d of causes) {
    if (!d.requires_review) continue;
    const strategic =
      ["leadership_change", "acquisition", "financial_distress"].includes(
        analysis.event_type || "",
      ) &&
      (d.relevance === "risk" || /risk/.test(d.code));
    const hint =
      (strategic
        ? "Verifica si el cambio organizativo o financiero descrito supone una amenaza para la continuidad estratégica; no implica por sí mismo una parada de producción."
        : d.code === "risk_fact_prediction_conflict"
          ? "La fuente describe un hecho adverso respaldado, pero la clasificación es negativa. Contrasta esa interpretación antes de tratarlo como ausencia de riesgo."
          : d.code === "risk_ambiguous"
            ? "Interpretación de riesgo por confirmar: contrasta si la reducción, demora o cambio descritos amenazan la continuidad, aunque el inventario cubra las entregas."
            : d.code === "urgency_ambiguous"
              ? "El modelo duda entre seguimiento y acción inmediata. Verifica el estado y el plazo del impacto; la criticidad o la fuente única no demuestran urgencia por sí solas."
              : d.resolution_hint) ||
      (/source_text|evidence_missing|no_evidence/.test(d.code)
        ? "Completa la lectura de la fuente y conserva un fragmento literal que respalde la conclusión."
        : /inventory/.test(d.code)
          ? "Confirma el inventario físico que falta; desconocido no significa cero."
          : /severity|duration/.test(d.code)
            ? "Confirma gravedad y duración para afinar la prioridad; no se han supuesto días ni stock."
            : /event_type/.test(d.code)
              ? "Contrasta el tipo de suceso con la fuente. La versión guardada dejó esta categoría pendiente; eso no demuestra urgencia."
              : /impact_state|event_state|recovered/.test(d.code)
                ? "Confirma si la interrupción sigue activa, es preventiva o se ha recuperado."
                : d.relevance === "association" ||
                    /link|association|geography/.test(d.code)
                  ? "Confirma que la ubicación, actividad o ruta del proveedor estén dentro del alcance de la noticia."
                  : d.relevance === "urgency" || /urgency|urgent/.test(d.code)
                    ? "Confirma el estado actual y el plazo del impacto antes de dar por sustentada una acción inmediata."
                    : d.relevance === "risk" || /risk/.test(d.code)
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
      {analysis.assessments.some(
        (a) =>
          a.needs_review &&
          !analysis.affected_supplier_ids.includes(a.supplier_id),
      ) && (
        <a
          className="text-link"
          href="#provider-hypotheses"
          onClick={(event) => {
            event.preventDefault();
            const group = document.getElementById(
              "provider-hypotheses",
            ) as HTMLDetailsElement | null;
            if (group) {
              group.open = true;
              group.scrollIntoView({ block: "start", behavior: "instant" });
              group.querySelector("summary")?.focus({ preventScroll: true });
            }
          }}
        >
          Ver hipótesis y datos pendientes por proveedor →
        </a>
      )}
    </section>
  );
}
