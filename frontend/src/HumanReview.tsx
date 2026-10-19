import { useEffect, useState } from "react";
import { api, date } from "./api";

/** Human operational record, never edits Analysis or evaluation labels. */
export function HumanReview({
  article,
  suppliers,
}: {
  article: any;
  suppliers: any[];
}) {
  const [expanded, setExpanded] = useState(article.state === "review"),
    [record, setRecord] = useState<any>(null),
    [scopeConfirmed, setScopeConfirmed] = useState(false),
    [sid, setSid] = useState(""),
    [association, setAssociation] = useState("unknown"),
    [risk, setRisk] = useState("N"),
    [urgent, setUrgent] = useState("N"),
    [severity, setSeverity] = useState(""),
    [exposure, setExposure] = useState("potential"),
    [impact, setImpact] = useState(""),
    [note, setNote] = useState(""),
    [evidence, setEvidence] = useState(""),
    [source, setSource] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState("");
  async function load() {
    try {
      const value = await api("/articles/" + article.id + "/review");
      if (
        !Array.isArray(value.history) ||
        !Array.isArray(value.remaining_suppliers)
      )
        throw new Error(
          "Revisión no disponible. Recarga para volver a intentarlo.",
        );
      setRecord(value);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    setRecord(null);
    setSid("");
    setNote("");
    setMessage("");
    void load();
  }, [article.id]);
  const assessments = article.analysis?.assessments || [],
    selected = suppliers.find((s) => s.supplier_id === sid),
    original = assessments.find((a: any) => a.supplier_id === sid),
    previous = record?.history.find(
      (r: any) => !r.obsolete && r.supplier_id === sid,
    );
  const proposed = [
    ...new Set([
      ...(record?.remaining_suppliers || []),
      ...(article.analysis?.affected_supplier_ids || []),
    ]),
  ];
  const choose = (value: string) => {
    setSid(value);
    setScopeConfirmed(false);
    setAssociation("unknown");
    setRisk("N");
    setUrgent("N");
    setSeverity("");
    setExposure("potential");
    setImpact("");
    setEvidence("");
    setSource("");
    setNote("");
    setMessage("");
  };
  if (!article.analysis || article.state === "error") return null;
  return (
    <details
      className="card operational-review"
      open={expanded}
      onToggle={(e) => {
        if (e.target === e.currentTarget) setExpanded(e.currentTarget.open);
      }}
    >
      <summary>
        {record?.state === "not_required"
          ? "Registrar revisión humana opcional"
          : "Revisión humana · " +
            (record?.state === "resolved"
              ? "resuelta"
              : record?.state === "in_verification"
                ? "en verificación"
                : "pendiente")}
      </summary>
      <section aria-label="Revisión humana">
        <div className="section-heading">
          <div>
            <h2>Resolver la revisión</h2>
            <p>
              Decide por proveedor, conserva la evidencia y deja una salida al
              trabajo.
            </p>
          </div>
          <span className="badge">
            {record?.state === "resolved"
              ? "Revisión resuelta"
              : record?.state === "in_verification"
                ? "En verificación"
                : record?.state === "not_required"
                  ? "Sin revisión pendiente"
                  : "Pendiente"}
          </span>
        </div>
        <p className="small-note">
          La predicción original de JEV permanece intacta. Las decisiones
          humanas cambian la gestión operativa; no corrigen sus métricas ni la
          exportación del reto y no se convierten en etiquetas de entrenamiento.
        </p>
        {error && (
          <p role="alert" className="notice error">
            {error}{" "}
            <button className="button" onClick={load}>
              Recargar revisión
            </button>
          </p>
        )}
        {!record && !error && <p role="status">Cargando decisiones…</p>}
        {record &&
          (record.generation !== article.generation ||
            record.source_version !== article.version) && (
            <p role="alert" className="notice warning">
              El análisis o la fuente cambió. Tu texto se conserva;{" "}
              <button className="button" onClick={load}>
                Recargar revisión
              </button>{" "}
              antes de decidir.
            </p>
          )}
        {record && (
          <>
            <p>
              {record.remaining_suppliers.length} proveedores con decisiones
              pendientes. {record.resolved_suppliers.length} decisiones
              registradas y cerradas.
            </p>
            <label>
              Proveedor que vas a verificar
              <select
                aria-label="Proveedor de la revisión"
                value={sid}
                onChange={(e) => choose(e.target.value)}
              >
                <option value="">Seleccionar proveedor</option>
                <optgroup label="Decisiones del análisis">
                  {suppliers
                    .filter((s) => proposed.includes(s.supplier_id))
                    .map((s) => (
                      <option key={s.supplier_id} value={s.supplier_id}>
                        {s.name}
                      </option>
                    ))}
                </optgroup>
                <optgroup label="Resto del catálogo · asociación manual">
                  {suppliers
                    .filter((s) => !proposed.includes(s.supplier_id))
                    .map((s) => (
                      <option key={s.supplier_id} value={s.supplier_id}>
                        {s.name}
                      </option>
                    ))}
                </optgroup>
              </select>
            </label>
            {sid && (
              <form
                className="operation-form"
                onSubmit={async (e) => {
                  e.preventDefault();
                  setBusy(true);
                  setError("");
                  try {
                    const next = await api(
                      "/articles/" + article.id + "/review",
                      {
                        method: "POST",
                        body: JSON.stringify({
                          supplier_id: sid,
                          generation: record.generation,
                          source_version: record.source_version,
                          analysis_id: record.analysis_id,
                          source_hash: record.source_hash,
                          case_scope_confirmed: scopeConfirmed,
                          previous_id: previous?.id || null,
                          association,
                          risk: association === "confirmed" ? risk : null,
                          urgent:
                            association === "confirmed" && risk === "Y"
                              ? urgent
                              : association === "confirmed"
                                ? "N"
                                : null,
                          severity:
                            association === "confirmed" && risk === "Y"
                              ? Number(severity)
                              : null,
                          exposure:
                            association === "confirmed"
                              ? exposure
                              : "potential",
                          impact_status:
                            association === "confirmed" && risk === "Y"
                              ? impact
                              : null,
                          note,
                          evidence,
                          evidence_source: source,
                        }),
                      },
                    );
                    setRecord(next);
                    setMessage(
                      "Decisión guardada. La gestión operativa se actualizará; JEV y sus métricas no cambian.",
                    );
                  } catch (ex) {
                    setError((ex as Error).message);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                <div className="notice">
                  <strong>Qué está en duda</strong>
                  <p>
                    {original
                      ? `Vínculo: ${original.association_status === "confirmed" ? "sustentado por el modelo" : "por verificar"} · Riesgo: ${original.is_risk === "Y" ? "detectado" : "no detectado"} · Urgencia: ${original.urgent === "Y" ? "urgente" : "no urgente"}.`
                      : "El análisis no confirmó este proveedor. Una asociación nueva necesita evidencia propia."}
                  </p>
                  <p>
                    {selected?.geography?.status === "ambiguous"
                      ? "La ciudad tiene varias coincidencias: confirma provincia y dirección. No se elegirá una ubicación por su nombre."
                      : "Confirma que la ubicación, actividad o ruta estén dentro del alcance publicado. Una coincidencia geográfica no demuestra una entrega afectada."}
                  </p>
                  <p>
                    {selected?.material} · {selected?.city}, {selected?.country}
                  </p>
                </div>
                <label>
                  Conclusión del vínculo
                  <select
                    aria-label="Conclusión del vínculo"
                    value={association}
                    onChange={(e) => setAssociation(e.target.value)}
                  >
                    <option value="unknown">
                      Falta información · seguir verificando
                    </option>
                    <option value="confirmed">
                      Confirmar asociación sustentada
                    </option>
                    <option value="rejected">
                      Rechazar asociación con evidencia
                    </option>
                  </select>
                </label>
                {association === "confirmed" && (
                  <div className="form-grid">
                    <label>
                      Decisión de riesgo
                      <select
                        aria-label="Decisión humana de riesgo"
                        value={risk}
                        onChange={(e) => {
                          setRisk(e.target.value);
                          setUrgent("N");
                        }}
                      >
                        <option value="N">Sin riesgo</option>
                        <option value="Y">Riesgo detectado</option>
                      </select>
                    </label>
                    <label>
                      Decisión de urgencia
                      <select
                        aria-label="Decisión humana de urgencia"
                        value={urgent}
                        disabled={risk !== "Y"}
                        onChange={(e) => setUrgent(e.target.value)}
                      >
                        <option value="N">Seguimiento, no urgente</option>
                        <option value="Y">Acción inmediata</option>
                      </select>
                    </label>
                    <label>
                      Alcance confirmado
                      <select
                        value={exposure}
                        onChange={(e) => setExposure(e.target.value)}
                      >
                        <option value="potential">
                          Exposición potencial · entregas por confirmar
                        </option>
                        <option value="reported">
                          Afectación individual confirmada por evidencia
                        </option>
                      </select>
                    </label>
                    {risk === "Y" && (
                      <label>
                        Estado del impacto, distinto de urgencia
                        <select
                          aria-label="Estado humano del impacto"
                          required
                          value={impact}
                          onChange={(e) => setImpact(e.target.value)}
                        >
                          <option value="">Seleccionar estado</option>
                          <option value="active">
                            Interrupción activa según evidencia
                          </option>
                          <option value="monitoring">
                            Seguimiento / exposición potencial
                          </option>
                        </select>
                      </label>
                    )}
                    {risk === "Y" && (
                      <label>
                        Severidad validada por el presentador (1–10)
                        <input
                          aria-label="Severidad humana"
                          type="number"
                          min="1"
                          max="10"
                          step="0.1"
                          required
                          value={severity}
                          onChange={(e) => setSeverity(e.target.value)}
                        />
                        <small>
                          JEV estimó {original?.severity ?? "sin determinar"}.
                          No se copia automáticamente.
                        </small>
                      </label>
                    )}
                  </div>
                )}
                <label>
                  Evidencia que respalda la decisión
                  <textarea
                    aria-label="Evidencia humana"
                    value={evidence}
                    minLength={association === "unknown" ? 0 : 8}
                    required={association !== "unknown"}
                    onChange={(e) => setEvidence(e.target.value)}
                  />
                </label>
                <button
                  className="button"
                  type="button"
                  onClick={() => {
                    setEvidence(
                      article.analysis.evidence
                        ?.map((v: any) => v.text)
                        .join("\n") || article.summary,
                    );
                    setSource(
                      article.url || `${article.source} · ${article.news_id}`,
                    );
                  }}
                >
                  Usar fragmentos de la noticia como punto de partida
                </button>
                <p className="small-note">
                  Una cita prueba lo que dice la fuente, no por sí sola la
                  asociación ni la urgencia. Añade la información de ubicación,
                  ruta o entrega que realmente hayas comprobado.
                </p>
                <label>
                  Procedencia de la evidencia
                  <input
                    aria-label="Procedencia humana"
                    value={source}
                    required={association !== "unknown"}
                    onChange={(e) => setSource(e.target.value)}
                    placeholder="Fuente publicada o referencia de confirmación del proveedor"
                  />
                </label>
                <label>
                  Resultado o información concreta que falta
                  <textarea
                    aria-label="Observación de revisión"
                    value={note}
                    minLength={8}
                    required
                    maxLength={4000}
                    onChange={(e) => setNote(e.target.value)}
                  />
                </label>
                {record.general_pending && (
                  <label className="checkbox">
                    <input
                      type="checkbox"
                      checked={scopeConfirmed}
                      disabled={association === "unknown"}
                      onChange={(e) => setScopeConfirmed(e.target.checked)}
                    />
                    He contrastado las dudas generales del análisis con la
                    evidencia registrada; no solo la asociación de este
                    proveedor.
                  </label>
                )}
                {record.general_pending && (
                  <p className="small-note">
                    Quedan dudas generales de alcance o decisión:{" "}
                    {record.general_questions?.join(" · ") ||
                      "riesgo y estado del evento por verificar"}
                    . Sin confirmación explícita la revisión global seguirá
                    abierta.
                  </p>
                )}
                {previous && (
                  <button
                    type="button"
                    className="button"
                    disabled={busy}
                    onClick={async () => {
                      setBusy(true);
                      setError("");
                      try {
                        setRecord(
                          await api("/articles/" + article.id + "/review", {
                            method: "POST",
                            body: JSON.stringify({
                              intent: "note",
                              supplier_id: sid,
                              generation: record.generation,
                              source_version: record.source_version,
                              analysis_id: record.analysis_id,
                              source_hash: record.source_hash,
                              previous_id: previous.id,
                              association: "unknown",
                              note,
                            }),
                          }),
                        );
                        setMessage(
                          "Observación guardada; la decisión anterior y la prioridad no cambian.",
                        );
                      } catch (ex) {
                        setError((ex as Error).message);
                      } finally {
                        setBusy(false);
                      }
                    }}
                  >
                    Añadir observación sin cambiar decisión
                  </button>
                )}
                <button
                  className="button primary"
                  disabled={
                    busy ||
                    record.generation !== article.generation ||
                    record.source_version !== article.version
                  }
                >
                  {busy
                    ? "Guardando…"
                    : association === "unknown"
                      ? "Guardar solicitud de verificación"
                      : "Registrar decisión humana"}
                </button>
              </form>
            )}
            {message && (
              <p role="status" className="notice">
                {message}
              </p>
            )}
            <details>
              <summary>Historial humano ({record.history.length})</summary>
              {record.history.map((h: any) => (
                <article key={h.id} className="fact-box">
                  <strong>
                    {suppliers.find((s) => s.supplier_id === h.supplier_id)
                      ?.name || h.supplier_id}{" "}
                    ·{" "}
                    {h.association === "unknown"
                      ? "En verificación"
                      : h.association === "rejected"
                        ? "Asociación rechazada"
                        : "Asociación confirmada"}
                  </strong>
                  <p>
                    {h.entry_kind === "note"
                      ? "Observación añadida, sin nueva decisión: "
                      : ""}
                    {h.note}
                  </p>
                  {h.association === "confirmed" && (
                    <p>
                      {h.risk === "Y" ? "Riesgo detectado" : "Sin riesgo"} ·{" "}
                      {h.urgent === "Y"
                        ? "Acción inmediata"
                        : "Seguimiento no urgente"}{" "}
                      ·{" "}
                      {h.exposure === "reported"
                        ? "Afectación individual confirmada por el presentador"
                        : "Exposición potencial, entregas por confirmar"}
                    </p>
                  )}
                  <blockquote>{h.evidence}</blockquote>
                  <small>
                    {h.evidence_source} · {date(h.created_at)} · {h.actor}
                    {h.obsolete
                      ? " · Ejecución anterior, no aplicada al análisis actual"
                      : ""}
                  </small>
                </article>
              ))}
            </details>
          </>
        )}
      </section>
    </details>
  );
}
