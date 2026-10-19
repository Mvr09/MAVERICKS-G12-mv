const pct = (n: number | null) =>
  n == null
    ? "No calculable"
    : (100 * n).toLocaleString("es-ES", { maximumFractionDigits: 1 }) + "%";
export function CurrentRefinement({ data }: { data: any }) {
  if (!data) return null;
  return (
    <section
      className="card detail-card"
      aria-label="Refinamiento actual de riesgo y revisión"
    >
      <h2>Candidata 3.4.2 · riesgo respaldado y revisión focalizada</h2>
      <p className="notice">
        Seleccionable; <strong>1.0.0 sigue predeterminada</strong>. Matching3.3,
        preguntas3.4.2 y revisión1.3.1. La asociación y la probabilidad de
        urgencia no cambian. El tiempo del hecho se interpreta en la fecha de
        publicación.
      </p>
      <p>
        18 sintéticos nuevos con referencias razonadas antes de JEV:14
        puntuables y4 con datos insuficientes. Incluye las predicciones
        revisadas. Evidencia controlada, sin precisión independiente demostrada
        sobre RSS real.
      </p>
      <div className="candidate-grid">
        {Object.entries(data.fresh.metrics).map(([key, m]: [string, any]) => (
          <article className="fact-box" key={key}>
            <h3>
              {
                {
                  baseline: "1.0 · referencia",
                  prior_3_3: "3.3 · anterior",
                  candidate_3_4_2: "3.4.2 · seleccionable",
                }[key]
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
                · TP{m[k].tp}/FP{m[k].fp}/FN{m[k].fn}
                <br />
                Prec {pct(m[k].precision)} · Rec {pct(m[k].recall)} · F1{" "}
                {pct(m[k].f1)}
              </p>
            ))}
            <p>
              Revisión {m.review_count}/{m.n} · Automáticas{" "}
              {m.automatic?.n || 0}/{m.n} · errores {m.automatic_joint_errors}/
              {m.automatic?.n || 0}
            </p>
          </article>
        ))}
      </div>
      <p>
        Frente a3.3:en los14 casos nuevos se corrige una omisión de riesgo y se
        automatiza correctamente una noticia adicional. No se añaden falsas
        urgencias ni asociaciones; una asociación incorrecta heredada permanece
        revisada. Los4 controles indeterminados siguen revisados.
      </p>
      <p>
        Training permanece en16/30 automáticas,0errores; una omisión de
        riesgo,tres falsas asociaciones ydos falsas urgencias siguen revisadas.
        En18controles ya inspeccionados de desarrollo,las revisiones bajan6→2
        ylas omisiones de riesgo2→0. A06 sigue abierto; no se inventa la
        provincia deS003.
      </p>
      <details>
        <summary>Consumo y límites del refinamiento</summary>
        <p>
          {data.consumption.additional_new_requests} peticiones nuevas locales,
          {data.consumption.retries} reintentos; contador
          {data.consumption.counter_before}→{data.consumption.counter_after}.
          A/B y preguntas idénticas de soporte se reutilizan. Las latencias
          locales incluyen caché y no son A20 ni rendimiento de Railway. La
          muestra propia no acredita generalización a noticias reales.
        </p>
      </details>
    </section>
  );
}
