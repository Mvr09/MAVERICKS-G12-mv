import { useEffect, useState } from "react";
import { api } from "./api";
import { Link } from "react-router-dom";
import { CurrentRefinement } from "./CurrentRefinement";
const pct = (x: number | null) =>
  x == null
    ? "No calculable"
    : (100 * x).toLocaleString("es-ES", { maximumFractionDigits: 1 }) + "%";
export function WindowEvaluation() {
  const [data, setData] = useState<any>(null),
    [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    api("/model/operational-candidate")
      .then((r) => {
        if (active) setData(r);
      })
      .catch(() => {
        if (active)
          setError("No se pudo leer la evaluación de la candidata operativa.");
      });
    return () => {
      active = false;
    };
  }, []);
  if (error) return <p role="alert">{error}</p>;
  if (!data?.controlled_final) return null;
  return (
    <>
      <CurrentRefinement data={data.refinement_342} />
      <section
        className="card detail-card"
        aria-label="Candidata operativa y muestra controlada"
      >
        <h2>Histórico 3.3 · exposición y revisión focalizada</h2>
        <p className="notice">
          Comparación anterior conservada. Matching link-3.3.0 · revisión1.2.0.
          La candidata seleccionable actual se indica arriba. Predeterminado:{" "}
          <strong>{data.default}</strong>. No promovida.
        </p>
        <p>
          Comprobación congelada de3.3:24 sintéticos, con referencias redactadas
          antes de llamar:18 puntuables y 6 con datos deliberadamente
          insuficientes. Incluye todas las predicciones revisadas. Es evidencia
          controlada; no demuestra precisión independiente sobre RSS real. Ya
          están inspeccionados y son desarrollo para futuras versiones.
        </p>
        <p>
          <strong>
            Cobertura sobre las 24 entradas:{" "}
            {data.controlled_final.all_case_states?.candidate?.done || 0}/24
            automáticas;{" "}
            {data.controlled_final.all_case_states?.candidate?.review || 0}/24
            revisadas.
          </strong>{" "}
          La tabla calcula precisión y errores solo donde existe referencia
          completa, sin excluir las predicciones revisadas.
        </p>
        <div className="candidate-grid">
          {Object.entries(data.controlled_final.metrics).map(
            ([name, m]: [string, any]) => (
              <article className="fact-box" key={name}>
                <h3>
                  {
                    {
                      baseline: "1.0 · predeterminado",
                      prior: "3.0 + revisión 1.1",
                      candidate: "3.3 + revisión 1.2",
                    }[name]
                  }
                </h3>
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
                    · TP{m[k].tp} / FP{m[k].fp} / FN{m[k].fn}
                    <br />
                    Prec {pct(m[k].precision)} · Rec {pct(m[k].recall)} · F1{" "}
                    {pct(m[k].f1)}
                  </p>
                ))}
                <p>
                  Automáticos {m.automatic?.n || 0}/{m.n} · errores{" "}
                  {m.automatic_joint_errors}/{m.automatic?.n || 0} · revisión{" "}
                  {m.review_count}/{m.n}
                </p>
              </article>
            ),
          )}
        </div>
        <p>
          La candidata automatiza correctamente los cuatro controles urgentes
          graves y ambas noticias positivas con identidad. Los seis controles
          indeterminados siguen revisados, sin atribuir daños individuales.
          Persisten dos omisiones de riesgo y tres asociaciones añadidas, todas
          revisadas.
        </p>
        <details>
          <summary>Consumo, límites y decisión de adopción</summary>
          <p>
            {data.consumption.new_requests} peticiones nuevas de desarrollo
            local / {data.consumption.retries} reintentos en esta ventana;
            contador local conservado {data.consumption.counter_before} →{" "}
            {data.consumption.counter_after}. El perfil anterior produjo un
            HTTP400 en un control ambiguo de gran tamaño; se conservó como
            error, sin repetirlo ni convertirlo en negativo. La candidata
            completó ese control.
          </p>
          <p>
            Training: 3.3 recupera las 22 asociaciones de referencia, con tres
            falsas (dos de criticidad alta), dos falsas urgencias y una omisión
            de riesgo. Esos errores requieren revisión. A06 sigue abierto;
            provincia de S003 desconocida. No se promueve por F1 agregado ni por
            reducir revisión.
          </p>
          <p>
            RSS periódico de pago desactivado. La muestra no usa validation,
            test, LiveDay ni answer key. A20 sigue como medición histórica del
            predeterminado; no certifica este perfil.
          </p>
        </details>
        {data.followup_experiments?.length > 0 && (
          <details>
            <summary>Ensayos adicionales descartados</summary>
            <p>
              Se conserva una única candidata operativa. Estos intentos no
              modifican el perfil seleccionable ni se ejecutan al analizar
              noticias.
            </p>
            {data.followup_experiments.map((trial: any) => (
              <p key={trial.version}>
                <strong>{trial.version}</strong> · {trial.requests} peticiones.{" "}
                {trial.decision_es}
              </p>
            ))}
          </details>
        )}
        {data.rss_rehearsal && (
          <details>
            <summary>Recorrido RSS real comprobado en Railway</summary>
            <p>
              {data.rss_rehearsal.new_requests} peticiones nuevas, incluidos dos
              intentos fallidos diagnosticados; contador RSS{" "}
              {data.rss_rehearsal.counter_before} →{" "}
              {data.rss_rehearsal.counter_after}. Pago periódico desactivado.
              Estos artículos no tienen etiquetas de referencia para medir
              precisión.
            </p>
            {data.rss_rehearsal.articles.map((article: any) => (
              <p key={article.id}>
                <Link
                  className="text-link"
                  to={"/noticias/" + article.id + "?context=rss"}
                >
                  {article.headline} →
                </Link>
                <br />
                {article.status === "review"
                  ? "Requiere verificar exposición; sin proveedor vinculado por la decisión."
                  : "Análisis automático sin vínculo sustentado con la cartera."}
              </p>
            ))}
          </details>
        )}
      </section>
    </>
  );
}
