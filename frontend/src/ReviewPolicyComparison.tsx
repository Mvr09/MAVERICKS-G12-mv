import { useEffect, useState } from "react";
import { api } from "./api";

export function ReviewPolicyComparison() {
  const [data, setData] = useState<any>(null),
    [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    api("/model/review-policy")
      .then((d) => {
        if (active) setData(d);
      })
      .catch(() => {
        if (active) setError("No se pudo consultar el ensayo de revisión.");
      });
    return () => {
      active = false;
    };
  }, []);
  if (error) return <p role="alert">{error}</p>;
  if (!data?.stages) return null;
  const names: Record<string, string> = {
    "3.0_original": "3.0 · revisión original",
    policy_only: "Solo política, sin llamadas",
    review_1_0_support: "1.0 · soporte de decisión",
    review_1_1_facts: "1.1 · soporte factual",
  };
  return (
    <section
      className="card detail-card"
      aria-label="Evaluación de la política de revisión"
    >
      <h2>Histórico · automatización y atención de compras</h2>
      <p>
        30 noticias de entrenamiento, incluidas las revisadas. Se conservan las
        predicciones y prioridades; cambia cómo se acredita su soporte. No es
        una evaluación independiente.
      </p>
      <div className="candidate-grid">
        {Object.entries(data.stages).map(([key, m]: [string, any]) => (
          <article className="fact-box" key={key}>
            <h3>{names[key] || key}</h3>
            <p>
              Revisión: <strong>{m.review_count}/30</strong>
            </p>
            <p>
              Cobertura automática:{" "}
              {(m.automatic_coverage * 100).toLocaleString("es-ES", {
                maximumFractionDigits: 1,
              })}
              %
            </p>
            <p>
              Errores entre automáticos: {m.automatic_joint_errors}/
              {m.automatic?.n || 0}
            </p>
            <p>
              Riesgos positivos correctos entre automáticos:{" "}
              {m.automatic?.risk?.tp || 0}
            </p>
          </article>
        ))}
      </div>
      <p className="notice">
        Ensayo histórico {data.policy_version} sobre3.0: cinco casos correctos
        más sin revisión, tres urgentes. Los cinco casos con errores conocidos
        siguen revisados. No se rebajan umbrales.
      </p>
      <h3>Qué sigue bloqueando decisiones</h3>
      <p>
        Asociación: {data.causes_after?.articles_per_cause?.association || 0}{" "}
        noticias · riesgo: {data.causes_after?.articles_per_cause?.risk || 0} ·
        urgencia: {data.causes_after?.articles_per_cause?.urgency || 0} ·
        impacto: {data.causes_after?.articles_per_cause?.impact || 0}. Las
        causas se solapan.
      </p>
      <p>
        Una duda sobre severidad o inventario se conserva junto a la prioridad
        estimada. Una urgencia suficientemente respaldada puede requerir acción
        inmediata sin que el análisis sea incierto.
      </p>
      <p>
        Los tres urgentes automáticos de training no alcanzan todos los umbrales
        originales para sonido. El control sintético urgente sí los cumple; no
        demuestra audibilidad física.
      </p>
      <details>
        <summary>Consumo y alcance del ensayo</summary>
        <p>
          {data.consumption?.total} peticiones nuevas ·{" "}
          {data.consumption?.retries} reintentos · 35 respuestas de soporte
          reutilizadas en la segunda etapa; A/B originales conservadas. Seis
          controles de política, sin tocar validation, test ni LiveDay.
        </p>
      </details>
      <small>
        Este ensayo conserva la recomendación histórica de1.1 sobre3.0. La
        candidata operativa actual utiliza
        matching3.3/preguntas3.4.2/revisión1.3.1 y se selecciona explícitamente
        en Excel o RSS;1.0.0 sigue predeterminada. Estos doce automáticos
        históricos no son el resultado actual ni garantizan precisión fuera de
        la muestra.
      </small>
    </section>
  );
}
