import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, date, number } from "./api";

const scopes: Record<string, string> = {
  decision: "Decisión relevante",
  discarded_candidate: "Candidato no aceptado",
  auxiliary: "Campo auxiliar",
  inherited: "Revisión heredada",
  unattributed: "Sin atribución suficiente",
};
const reasons: Record<string, string> = {
  link_ambiguous: "Vínculo ambiguo",
  event_type_confidence_low: "Tipo de evento incierto",
  event_state_confidence_low: "Estado general incierto",
  severity_confidence_low: "Severidad incierta",
  impact_state_confidence_low: "Estado del impacto incierto",
  evidence_confidence_low: "Selección de evidencia incierta",
  duration_confidence_low: "Duración incierta",
  evidence_missing: "Sin evidencia seleccionada",
  decision_ambiguous_or_contradictory:
    "Decisión ambigua, contradictoria o revisión propagada",
  inventory_missing: "Inventario desconocido",
  buffer_horizon_missing: "Sin horizonte de cobertura",
};
const decisions = (value: string) =>
  value === "Y" ? "Sí" : value === "N" ? "No" : "Sin determinar";
const probability = (value: number | null) =>
  value == null
    ? "No evaluada"
    : value.toLocaleString("es-ES", { maximumFractionDigits: 3 });
const ids = (value: string[]) => value.join(", ") || "Ninguno";

export function DiagnosticPanel({ bid }: { bid: string }) {
  const [open, setOpen] = useState(false),
    [data, setData] = useState<any>(null),
    [error, setError] = useState("");
  useEffect(() => {
    setData(null);
    setError("");
  }, [bid]);
  useEffect(() => {
    if (!open) return;
    let active = true,
      busy = false;
    async function load() {
      if (busy) return;
      busy = true;
      try {
        const result = await api("/model/diagnostics/" + bid, {
          cache: "no-store",
        });
        if (active) {
          setData(result);
          setError("");
        }
      } catch (e: any) {
        if (active) {
          setData(null);
          setError(e.message);
        }
      } finally {
        busy = false;
      }
    }
    load();
    const timer = window.setInterval(load, 3000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [bid, open]);
  return (
    <details
      className="diagnostic-panel"
      onToggle={(e) => {
        if (e.target === e.currentTarget) setOpen(e.currentTarget.open);
      }}
    >
      <summary>Diagnóstico por noticia · acceso de presentador</summary>
      <p>
        Consulta resultados almacenados; no llama a JEV ni cambia umbrales. La
        revisión se atribuye por su causa, sin retirarla automáticamente.
      </p>
      {error && <p role="alert">{error}</p>}
      {open && !data && !error && (
        <p role="status">Reconstruyendo decisiones y revisión…</p>
      )}
      {data && (
        <>
          <p>
            <strong>{data.filename}</strong> · Consulta {date(data.created_at)}{" "}
            · Actualiza cada 3 segundos mientras está abierto.
          </p>
          {data.split === "validation" && (
            <div className="notice warning">
              Validación ya inspeccionada. Las correcciones deben desarrollarse
              con entrenamiento; repetir este lote no constituye una nueva
              evaluación independiente.
            </div>
          )}
          <p>
            {data.summary.risk_false_negatives} omisiones de riesgo ·{" "}
            {data.summary.missing_supplier_associations} asociaciones de
            proveedor faltantes · {data.summary.reviewed_news} noticias en
            revisión.
          </p>
          <p>
            Umbrales conservados: vínculo {number(data.thresholds.link)}, riesgo{" "}
            {number(data.thresholds.risk)}, urgencia{" "}
            {number(data.thresholds.urgent)}; intervalo de revisión [
            {number(data.thresholds.review_low)},{" "}
            {number(data.thresholds.review_high)}]; confianza Choice/Score{" "}
            {number(data.thresholds.choice_score_confidence)}.
          </p>
          <button
            className="button small"
            onClick={() => {
              const url = URL.createObjectURL(
                new Blob([JSON.stringify(data, null, 2)], {
                  type: "application/json",
                }),
              );
              const a = document.createElement("a");
              a.href = url;
              a.download = "diagnostico-privado-" + data.split + ".json";
              a.click();
              URL.revokeObjectURL(url);
            }}
          >
            Descargar diagnóstico privado
          </button>
          {data.rows.map((row: any) => (
            <article className="diagnostic-row" key={row.article_id}>
              <h3>
                <Link to={"/noticias/" + row.article_id}>
                  {row.news_id} · {row.headline}
                </Link>
              </h3>
              <div className="diagnostic-comparison">
                <div>
                  <h4>Referencia</h4>
                  <p>
                    Riesgo: {decisions(row.reference.is_risk)} · Urgencia:{" "}
                    {decisions(row.reference.urgent)}
                  </p>
                  <p>Proveedores: {ids(row.reference.affected_supplier_ids)}</p>
                </div>
                <div>
                  <h4>Predicción</h4>
                  <p>
                    Riesgo: {decisions(row.prediction.is_risk)} · Urgencia:{" "}
                    {decisions(row.prediction.urgent)}
                  </p>
                  <p>
                    Proveedores: {ids(row.prediction.affected_supplier_ids)}
                  </p>
                </div>
              </div>
              {row.risk_false_negative && (
                <p className="error-text">
                  Omisión de riesgo: la referencia indica riesgo y la predicción
                  indica que no.
                </p>
              )}
              <p>
                Proveedores omitidos: {ids(row.missing_suppliers)} ·
                Adicionales: {ids(row.extra_suppliers)}
              </p>
              <p>
                {row.prediction.analysis_status === "review"
                  ? "Requiere revisión"
                  : "Sin revisión"}{" "}
                · Raíces:{" "}
                {row.review.root_scopes
                  .map((s: string) => scopes[s])
                  .join(" · ") || "Ninguna"}
              </p>
              {row.review.decision_gates?.length > 0 && (
                <details>
                  <summary>
                    Puertas de decisión que también generan revisión
                  </summary>
                  <p>
                    Valores que activan la regla de revisión aunque el motivo
                    genérico no se haya guardado por existir otro motivo previo.
                    No son nuevas decisiones ni motivos almacenados adicionales.
                  </p>
                  <pre className="diagnostic-gates">
                    {JSON.stringify(row.review.decision_gates, null, 2)}
                  </pre>
                </details>
              )}
              {row.reference.explanation && (
                <details>
                  <summary>Justificación de referencia</summary>
                  <p>{row.reference.explanation}</p>
                </details>
              )}
              <details>
                <summary>Puertas de decisión por proveedor</summary>
                {row.supplier_gates.map((s: any) => (
                  <p key={s.supplier_id}>
                    <strong>{s.supplier_id}</strong>
                    {s.p_candidate != null && (
                      <span>
                        {" "}
                        · Candidatura {probability(s.p_candidate)} · Identidad{" "}
                        {probability(s.p_identity)} · Exposición{" "}
                        {probability(s.p_exposure)}
                      </span>
                    )}
                    : vínculo {probability(s.p_link)}, riesgo{" "}
                    {probability(s.p_risk)}, urgencia {probability(s.p_urgent)}{" "}
                    · etapa B {s.stage_b_evaluated ? "evaluada" : "no evaluada"}{" "}
                    ·{" "}
                    {
                      (
                        {
                          excluded_before_stage_b: "Excluido antes de etapa B",
                          below_link_threshold:
                            "Vínculo bajo el umbral de aceptación",
                          below_risk_threshold: "Riesgo bajo el umbral",
                          risk_accepted: "Riesgo aceptado",
                          raw_unavailable: "Respuesta original no disponible",
                          assessment_unavailable: "Evaluación no disponible",
                        } as Record<string, string>
                      )[s.gate]
                    }
                  </p>
                ))}
              </details>
              <details>
                <summary>
                  Motivos exactos de revisión ({row.review.causes.length})
                </summary>
                {!row.review.raw_available && (
                  <p>
                    Respuesta original ausente: atribución limitada a motivos
                    normalizados.
                  </p>
                )}
                {row.review.causes.map((r: any, i: number) => (
                  <div className="diagnostic-cause" key={i}>
                    <strong>
                      {reasons[r.code.split(":")[0]] || r.code}{" "}
                      {r.supplier_id && "· " + r.supplier_id}
                    </strong>
                    <p>
                      {scopes[r.scope]} · <code>{r.code}</code>
                    </p>
                    <pre>{JSON.stringify(r.details, null, 2)}</pre>
                  </div>
                ))}
              </details>
            </article>
          ))}
        </>
      )}
    </details>
  );
}
