import { useEffect, useState } from "react";
import { api } from "./api";
const score = (value: number | null) =>
  value == null
    ? "No calculable"
    : value.toLocaleString("es-ES", { maximumFractionDigits: 3 });
export function CandidateComparison() {
  const [data, setData] = useState<any>(null),
    [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    api("/model/candidates")
      .then((d) => {
        if (active) setData(d);
      })
      .catch(() => {
        if (active) setError("No se pudo consultar la comparación almacenada.");
      });
    return () => {
      active = false;
    };
  }, []);
  if (error) return <p role="alert">{error}</p>;
  if (!data?.metrics) return null;
  return (
    <section className="card detail-card">
      <h2>Selección de candidato · evidencia de desarrollo</h2>
      <p>
        30 noticias de entrenamiento, incluidas las revisadas. Resultados
        almacenados; no son métricas en vivo ni una evaluación independiente.
      </p>
      <p className="notice">
        Preferido para descubrimiento asistido:{" "}
        <strong>{data.preferred_candidate}</strong>. Predeterminado:{" "}
        {data.default_profile}. No se promueve inferencia automática ni se
        ejecutan nuevas llamadas desde esta vista.
      </p>
      <div className="candidate-grid">
        {Object.entries(data.metrics).map(([version, m]: [string, any]) => (
          <article className="fact-box" key={version}>
            <h3>{version}</h3>
            {["risk", "urgent", "suppliers"].map((k) => (
              <p key={k}>
                <strong>
                  {
                    {
                      risk: "Riesgo",
                      urgent: "Urgencia",
                      suppliers: "Proveedores",
                    }[k]
                  }
                </strong>{" "}
                · TP{m[k].tp} / FP{m[k].fp} / FN{m[k].fn} · Prec{" "}
                {score(m[k].precision)} / Rec {score(m[k].recall)} / F1{" "}
                {score(m[k].f1)}
              </p>
            ))}
            <p>Conjunto exacto: {m.suppliers.exact}/30</p>
            <p>
              Revisión: {m.review_count}/30 · Automáticos: {m.automatic?.n || 0}
              /30
            </p>
            <p>
              Errores de salida entre automáticos: {m.automatic_joint_errors}/
              {m.automatic?.n || 0}
            </p>
            <p>
              Omisiones de proveedores críticos:{" "}
              {data.operational_strata[version].fn_high} · fuente única:{" "}
              {data.operational_strata[version].fn_single_source}
            </p>
          </article>
        ))}
      </div>
      <p>
        3.0 recupera más exposición crítica, pero conserva falsos vínculos en
        revisión y pierde un servicio marítimo declarado. 2.2 es la referencia
        de precisión. 4.0.1 resuelve los controles de ruta y modo, pero no
        mejora el balance de errores de la cartera.
      </p>
      <small>
        La comparación histórica de2.2 precede al extractor duration-1.1.0; no
        se atribuyen las diferencias únicamente a una pregunta. Cero errores
        entre pocos automáticos no demuestra seguridad fuera de la muestra.
      </small>
    </section>
  );
}
