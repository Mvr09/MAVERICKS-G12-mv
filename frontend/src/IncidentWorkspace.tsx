import { useEffect, useRef, useState } from "react";
import { api, date } from "./api";
const labels: Record<string, string> = {
  pending: "Pendiente",
  verifying: "En verificación",
  followup: "Seguimiento",
  done: "Acción completada",
};
export function IncidentWorkspace({ incidentId }: { incidentId: string }) {
  const [work, setWork] = useState<any>(null),
    [status, setStatus] = useState("pending"),
    [action, setAction] = useState(""),
    [note, setNote] = useState(""),
    [due, setDue] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [draft, setDraft] = useState<any>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  async function load() {
    try {
      const w = await api("/incidents/" + incidentId + "/workspace");
      if (!Array.isArray(w.history) || !Array.isArray(w.drafts))
        throw new Error(
          "Seguimiento no disponible. Recarga para volver a intentarlo.",
        );
      setWork(w);
      setStatus(w.current?.status || "pending");
      setAction(w.current?.action || "");
      setDue(w.current?.due_date || "");
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    void load();
    const update = async (e: Event) => {
      if ((e as CustomEvent).detail === incidentId) {
        try {
          const w = await api("/incidents/" + incidentId + "/workspace");
          if (Array.isArray(w.drafts)) setWork(w);
        } catch (ex) {
          setError((ex as Error).message);
        }
      }
    };
    window.addEventListener("radar:incident-drafts", update);
    return () => window.removeEventListener("radar:incident-drafts", update);
  }, [incidentId]);
  useEffect(() => {
    if (draft) dialog.current?.showModal();
  }, [draft?.id]);
  return (
    <details className="incident-work">
      <summary>
        Acción y seguimiento · {labels[work?.current?.status || "pending"]}
      </summary>
      <p className="small-note">
        Completar una acción no confirma la recuperación del incidente. Usa
        «Resolver incidente» únicamente con evidencia de normalización.
      </p>
      {error && (
        <p role="alert">
          {error}{" "}
          <button className="button" onClick={load}>
            Recargar seguimiento
          </button>
        </p>
      )}
      {!work && !error && <p role="status">Cargando seguimiento…</p>}
      {work && (
        <>
          <form
            className="operation-form"
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              setError("");
              try {
                const w = await api("/incidents/" + incidentId + "/workspace", {
                  method: "POST",
                  body: JSON.stringify({
                    previous_id: work.current?.id || null,
                    status,
                    action,
                    note,
                    due_date: due || null,
                  }),
                });
                setWork(w);
                setNote("");
                setMessage("Acción registrada con su historial.");
              } catch (ex) {
                setError((ex as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              Estado de la acción
              <select
                aria-label="Estado de la acción"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                {Object.entries(labels).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Siguiente acción concreta
              <input
                aria-label="Siguiente acción concreta"
                value={action}
                required
                minLength={8}
                maxLength={500}
                onChange={(e) => setAction(e.target.value)}
              />
            </label>
            <label>
              Fecha de seguimiento
              <input
                aria-label="Fecha de seguimiento"
                type="date"
                value={due}
                onChange={(e) => setDue(e.target.value)}
              />
            </label>
            <label>
              Qué se hizo o qué falta confirmar
              <textarea
                aria-label="Observación de seguimiento"
                value={note}
                required
                minLength={8}
                maxLength={4000}
                onChange={(e) => setNote(e.target.value)}
              />
            </label>
            <button className="button primary" disabled={busy}>
              {busy ? "Guardando…" : "Guardar seguimiento"}
            </button>
          </form>
          {message && <p role="status">{message}</p>}
          <h4>Consultas de este incidente</h4>
          {work.drafts.length ? (
            work.drafts
              .slice()
              .sort(
                (a: any, b: any) =>
                  Number(a.context_changed) - Number(b.context_changed),
              )
              .map((d: any) => (
                <button
                  key={d.id}
                  data-draft-id={d.id}
                  className="button saved-query"
                  onClick={async () => {
                    try {
                      setDraft(await api("/drafts/" + d.id));
                    } catch (e) {
                      setError((e as Error).message);
                    }
                  }}
                >
                  Abrir consulta{" "}
                  {d.kind === "alternate" ? "al alternativo" : "al proveedor"}
                  {d.context_changed
                    ? " · contexto anterior, revisar"
                    : " · contexto vigente"}
                  {d.preview && <small>{d.preview}</small>}
                </button>
              ))
          ) : (
            <p>
              No hay consultas guardadas. Crea una con los botones del incidente
              tras verificar sus hechos.
            </p>
          )}
          <details>
            <summary>Historial de acciones ({work.history.length})</summary>
            {work.history.map((h: any) => (
              <article className="fact-box" key={h.id}>
                <strong>
                  {labels[h.status]} · {h.action}
                </strong>
                <p>{h.note}</p>
                <small>
                  {date(h.created_at)}
                  {h.due_date ? " · Seguimiento: " + h.due_date : ""}
                </small>
              </article>
            ))}
          </details>
        </>
      )}
      <dialog
        ref={dialog}
        className="workspace-dialog"
        onClose={() => setDraft(null)}
      >
        <div className="section-heading">
          <h3>Consulta guardada del incidente</h3>
          <button
            className="button"
            aria-label="Cerrar consulta guardada"
            onClick={() => dialog.current?.close()}
          >
            Cerrar
          </button>
        </div>
        <p>No se envía externamente.</p>
        {draft && (
          <>
            <label>
              Texto de la consulta
              <textarea
                aria-label="Texto de la consulta guardada"
                value={draft.text}
                onChange={(e) => setDraft({ ...draft, text: e.target.value })}
              />
            </label>
            <button
              className="button primary"
              onClick={async () => {
                try {
                  await api("/drafts/" + draft.id, {
                    method: "PATCH",
                    body: JSON.stringify({ text: draft.text }),
                  });
                  setMessage("Consulta guardada.");
                  dialog.current?.close();
                } catch (e) {
                  setError((e as Error).message);
                }
              }}
            >
              Guardar consulta
            </button>
          </>
        )}
      </dialog>
    </details>
  );
}
