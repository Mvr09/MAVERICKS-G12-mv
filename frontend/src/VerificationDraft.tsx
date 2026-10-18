import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { api, date } from "./api";
import { procurement } from "./procurement";
import type { Article, Supplier } from "./types";

export function RssArticleAnalysis({ article: a }: { article: Article }) {
  const [job, setJob] = useState<any>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    if (!job?.id) return;
    let active = true;
    const timer = setInterval(() => {
      api("/jobs/" + job.id)
        .then((j) => {
          if (active) {
            setJob(j);
            if (["done", "error", "cancelled"].includes(j.state))
              clearInterval(timer);
          }
        })
        .catch(() => {
          if (active) setError("No se pudo actualizar el trabajo.");
        });
    }, 1500);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [job?.id]);
  return (
    <div className="rss-single-analysis">
      <button
        className="button primary"
        disabled={busy || a.state !== "pending" || !!job}
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            const r = await api("/analysis/rss", {
              method: "POST",
              body: JSON.stringify({ limit: 1, article_ids: [a.id] }),
            });
            setJob({ id: r.job_ids[0], state: "queued" });
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy
          ? "Encolando…"
          : a.state === "pending"
            ? "Analizar esta noticia"
            : "Análisis disponible"}
      </button>
      <span role="status">
        {job?.state === "queued"
          ? "En cola · esperando worker"
          : job?.state === "running"
            ? "JEV está analizando esta noticia"
            : job?.state === "done"
              ? "Trabajo completado · resultado actualizado"
              : job?.state === "error"
                ? "El análisis falló; revisa el diagnóstico"
                : ""}
      </span>
      {error && <p role="alert">{error}</p>}
    </div>
  );
}

export function VerificationDraft({ article: a }: { article: Article }) {
  const ref = useRef<HTMLDialogElement>(null),
    returnFocus = useRef<HTMLElement | null>(null);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]),
    [sid, setSid] = useState(""),
    [ids, setIds] = useState<string[]>([]),
    [note, setNote] = useState(""),
    [ack, setAck] = useState(false),
    [error, setError] = useState(""),
    [status, setStatus] = useState(""),
    [busy, setBusy] = useState(false),
    [draft, setDraft] = useState<{ id: string; text: string } | null>(null),
    [snapshot, setSnapshot] = useState<{
      generation: number;
      version: number;
      evidence: any[];
    } | null>(null);
  const [saved, setSaved] = useState<{ id: string; supplier_id: string }[]>([]);
  useEffect(() => {
    let active = true;
    api("/articles/" + a.id + "/drafts")
      .then((v) => {
        if (active) setSaved(v);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [a.id, draft?.id]);
  const stale =
    snapshot &&
    (snapshot.generation !== (a.generation || 0) ||
      snapshot.version !== a.version);
  const chosen = suppliers.find((s) => s.supplier_id === sid);
  const close = () => {
    ref.current?.close();
    returnFocus.current?.focus();
  };
  const open = async (e: any) => {
    returnFocus.current = e.currentTarget;
    setSnapshot({
      generation: a.generation || 0,
      version: a.version,
      evidence: a.analysis?.evidence || [],
    });
    setDraft(null);
    setIds([]);
    setAck(false);
    setError("");
    setStatus("");
    ref.current?.showModal();
    try {
      setSuppliers((await api("/suppliers?context=rss")).items);
    } catch {
      setError("No se pudo cargar la cartera.");
    }
  };
  return (
    <section
      className="verification-entry"
      aria-label="Consultar posible exposición"
    >
      <div>
        <strong>De la evidencia a una pregunta concreta</strong>
        <p>
          Si el vínculo está en revisión, consulta al proveedor sin dar por
          confirmada la afectación. La consulta conserva la fuente y tu
          hipótesis; no cambia riesgo, prioridad ni alertas.
        </p>
      </div>
      <button
        className="button"
        disabled={!a.analysis || a.analysis.analysis_status === "error"}
        onClick={open}
      >
        Preparar consulta de verificación
      </button>
      {saved.length > 0 && (
        <details>
          <summary>Consultas guardadas ({saved.length})</summary>
          {saved.map((item) => (
            <button
              className="button"
              key={item.id}
              onClick={async (e) => {
                returnFocus.current = e.currentTarget;
                try {
                  const value = await api("/drafts/" + item.id);
                  setDraft(value);
                  setSnapshot(value.evidence_snapshot);
                  setStatus(
                    "Consulta recuperada de PostgreSQL con su evidencia original.",
                  );
                  setError("");
                  ref.current?.showModal();
                } catch (err) {
                  setError((err as Error).message);
                }
              }}
            >
              Abrir consulta · {item.supplier_id}
            </button>
          ))}
        </details>
      )}
      <dialog
        ref={ref}
        onCancel={(e) => {
          e.preventDefault();
          close();
        }}
      >
        <header>
          <h2>Consulta de exposición potencial</h2>
          <button
            className="icon-button"
            aria-label="Cerrar consulta"
            onClick={close}
          >
            ×
          </button>
        </header>
        <div className="modal-body verification-body">
          <p className="notice">
            Cartera ficticia · hipótesis de compras. No confirma daños ni
            entregas afectadas. No se envía externamente.
          </p>
          {stale && (
            <p className="notice warning">
              La noticia cambió.{" "}
              {draft
                ? "Este borrador conserva los fragmentos de su versión original."
                : "Cierra y vuelve a abrir para revisar la nueva versión."}
            </p>
          )}
          {error && (
            <p role="alert" className="notice error">
              {error}
            </p>
          )}
          {status && <p role="status">{status}</p>}
          {!draft ? (
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                if (!snapshot || stale) return;
                setBusy(true);
                setError("");
                try {
                  setDraft(
                    await api("/verification-drafts", {
                      method: "POST",
                      body: JSON.stringify({
                        article_id: a.id,
                        supplier_id: sid,
                        generation: snapshot.generation,
                        version: snapshot.version,
                        evidence_ids: ids,
                        note,
                        acknowledged: ack,
                      }),
                    }),
                  );
                  setStatus(
                    "Borrador guardado con evidencia y versión de la fuente.",
                  );
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              <label htmlFor="verification-supplier">
                Proveedor al que consultar
              </label>
              <select
                id="verification-supplier"
                value={sid}
                required
                onChange={(e) => setSid(e.target.value)}
              >
                <option value="">Selecciona una identidad de la cartera</option>
                {suppliers.map((s) => (
                  <option key={s.supplier_id} value={s.supplier_id}>
                    {s.name} · {s.material}
                  </option>
                ))}
              </select>
              {chosen && (
                <div className="fact-box">
                  <strong>{chosen.material}</strong>
                  <p>{procurement(chosen, "rss").drivers.join(" · ")}</p>
                  <p>
                    {chosen.products.length
                      ? "Productos relacionados: " + chosen.products.join(" · ")
                      : "Productos no mapeados"}
                  </p>
                  <p>{procurement(chosen, "rss").alternative}</p>
                  <Link
                    className="text-link"
                    to={"/proveedores/" + sid + "?context=rss"}
                    onClick={close}
                  >
                    Ver ficha del proveedor →
                  </Link>
                </div>
              )}
              <fieldset className="verification-evidence">
                <legend>Selecciona de 1 a 3 fragmentos que has leído</legend>
                <small>
                  {a.source} · {date(a.published_date)} · citas literales, no
                  prueba de asociación
                </small>
                {snapshot?.evidence.map((e) => (
                  <label key={e.id}>
                    <input
                      type="checkbox"
                      checked={ids.includes(e.id)}
                      disabled={!ids.includes(e.id) && ids.length >= 3}
                      onChange={(ev) =>
                        setIds((v) =>
                          ev.target.checked
                            ? [...v, e.id]
                            : v.filter((x) => x !== e.id),
                        )
                      }
                    />
                    <span>{e.text}</span>
                  </label>
                ))}
              </fieldset>
              <label htmlFor="verification-note">
                Por qué podría ser relevante (hipótesis, no hecho confirmado)
              </label>
              <textarea
                id="verification-note"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                required
                minLength={12}
                maxLength={500}
                rows={3}
              />
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={ack}
                  onChange={(e) => setAck(e.target.checked)}
                  required
                />
                He leído los fragmentos y entiendo que la exposición está
                pendiente de confirmar.
              </label>
              <button
                className="button primary"
                disabled={busy || !!stale || !ack || !ids.length || !sid}
              >
                {busy
                  ? "Guardando con evidencia…"
                  : "Crear borrador de verificación"}
              </button>
            </form>
          ) : (
            <>
              <label htmlFor="verification-text">
                Texto editable de la consulta
              </label>
              <textarea
                id="verification-text"
                rows={15}
                value={draft.text}
                onChange={(e) => setDraft({ ...draft, text: e.target.value })}
              />
              <div className="inline">
                <button
                  className="button primary"
                  disabled={busy}
                  onClick={async () => {
                    setBusy(true);
                    try {
                      await api("/drafts/" + draft.id, {
                        method: "PATCH",
                        body: JSON.stringify({ text: draft.text }),
                      });
                      setStatus("Edición guardada.");
                    } catch (e) {
                      setError((e as Error).message);
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Guardar consulta
                </button>
                <button
                  className="button"
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(draft.text);
                      setStatus("Consulta copiada.");
                    } catch {
                      setError("Selecciona el texto y cópialo manualmente.");
                    }
                  }}
                >
                  Copiar consulta
                </button>
                <button
                  className="button"
                  onClick={() => {
                    const url = URL.createObjectURL(
                      new Blob([draft.text], {
                        type: "text/plain;charset=utf-8",
                      }),
                    );
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = "consulta-exposicion.txt";
                    link.click();
                    URL.revokeObjectURL(url);
                  }}
                >
                  Descargar consulta TXT
                </button>
              </div>
            </>
          )}
        </div>
      </dialog>
    </section>
  );
}
