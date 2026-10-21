import { AsyncButton } from "./OperationFeedback";
import { Bot, CalendarClock, FileText, Package, Repeat2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "./api";

export type PlanAction = {
  code: string;
  label: string;
  reason: string;
  deadline: "hoy" | "esta_semana" | "proximo_informe";
  deadline_label: string;
};
export type PlanDraft = {
  id: string;
  kind: string;
  label: string;
  language: string;
  writer: string;
};
export type Plan = {
  id: string | null;
  incident_id: string;
  revision: number;
  rules_version: string;
  actions: PlanAction[];
  summary: string;
  summary_source: "llm" | "template";
  summary_error: string | null;
  llm: { model: string; served_by: string | null } | null;
  decision: "JEV" | "humano";
  facts: {
    incidente: { urgente: boolean; titular: string | null; tipo_evento: string | null };
    proveedor: { criticidad: string | null; fuente_unica: boolean };
    stock: {
      margen_dias: number | string;
      fecha_rotura_si_continua: string | null;
    };
    productos: string[] | string;
    alternativo: { nombre: string; ciudad: string; afectado: boolean } | null;
  };
  drafts: PlanDraft[];
};
type Llm = { model: string; configured: boolean };

const DATE = new Intl.DateTimeFormat("es-ES", {
  day: "numeric",
  month: "short",
  year: "numeric",
});
export const planDay = (v: string) => DATE.format(new Date(v.slice(0, 10)));

export function marginText(m: number | string, long = false) {
  if (typeof m === "number") return m + " días";
  return m === "no aplica"
    ? long
      ? "No aplica (logística o servicios)"
      : "no aplica"
    : "No informado";
}

export function DeadlinePill({ action }: { action: PlanAction }) {
  return (
    <span className={"deadline-pill " + action.deadline}>
      <CalendarClock size={13} aria-hidden /> {action.deadline_label}
    </span>
  );
}

/** Plans of every open incident in the context. Public read; a presenter read also stores them. */
export function usePlans(context: string, refreshKey: unknown) {
  const [plans, setPlans] = useState<Record<string, Plan | null>>({});
  useEffect(() => {
    let active = true;
    api("/plans?context=" + encodeURIComponent(context))
      .then((r) => active && setPlans(r.plans || {}))
      .catch(() => active && setPlans({}));
    return () => {
      active = false;
    };
  }, [context, refreshKey]);
  return plans;
}

const DUE_DAYS: Record<string, number> = { hoy: 0, esta_semana: 7 };
function dueDate(deadline: string) {
  const days = DUE_DAYS[deadline];
  if (days === undefined) return "";
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

/** Suggested actions only: rules pick them, Claude may draft the summary. Adopting one
 * pre-fills the human follow-up; nothing is saved or sent automatically. */
export function PlanCard({
  plan,
  presenter,
  llm,
  onPlan,
}: {
  plan: Plan;
  presenter: boolean;
  llm?: Llm;
  onPlan?: (p: Plan) => void;
}) {
  const f = plan.facts;
  const [draft, setDraft] = useState<any>(null),
    [message, setMessage] = useState(""),
    [error, setError] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (draft) dialog.current?.showModal();
  }, [draft?.id]);
  return (
    <section className="plan-card" aria-label="Plan de acción">
      <div className="plan-head">
        <h4>Plan de acción</h4>
        <span>
          Reglas {plan.rules_version} · acciones elegidas por reglas; cifras de
          la base de datos
        </span>
      </div>
      <ol className="plan-actions">
        {plan.actions.map((a) => (
          <li key={a.code}>
            <DeadlinePill action={a} />
            <div>
              <strong>{a.label}</strong>
              <small>{a.reason}</small>
            </div>
            {presenter && (
              <button
                className="text-button"
                onClick={() =>
                  window.dispatchEvent(
                    new CustomEvent("radar:plan-action", {
                      detail: {
                        incidentId: plan.incident_id,
                        action: a.label,
                        due: dueDate(a.deadline),
                      },
                    }),
                  )
                }
              >
                Usar en el seguimiento
              </button>
            )}
          </li>
        ))}
      </ol>
      <dl className="plan-facts">
        <div>
          <dt>Margen de stock</dt>
          <dd>{marginText(f.stock.margen_dias, true)}</dd>
          {f.stock.fecha_rotura_si_continua && (
            <dd className="plan-note">
              Rotura estimada si la parada continúa:{" "}
              {planDay(f.stock.fecha_rotura_si_continua)}
            </dd>
          )}
        </div>
        <div>
          <dt>
            <Package size={13} aria-hidden /> Productos en juego
          </dt>
          <dd>
            {Array.isArray(f.productos) ? f.productos.join(", ") : f.productos}
          </dd>
        </div>
        <div>
          <dt>
            <Repeat2 size={13} aria-hidden /> Alternativo aprobado
          </dt>
          <dd>
            {f.alternativo
              ? `${f.alternativo.nombre} (${f.alternativo.ciudad})`
              : "Sin alternativo aprobado"}
          </dd>
          {f.alternativo && (
            <dd>
              <span
                className={
                  "badge " + (f.alternativo.afectado ? "danger" : "success")
                }
              >
                {f.alternativo.afectado
                  ? "También afectado"
                  : "Sin incidente activo · stock sin confirmar"}
              </span>
            </dd>
          )}
        </div>
      </dl>
      <p className="plan-summary">
        {plan.summary_source === "llm" && (
          <span className="badge purple ai-badge">
            <Bot size={12} aria-hidden /> Redactado por IA
          </span>
        )}
        {plan.summary}
      </p>
      {presenter && plan.summary_error && (
        <p className="plan-note">{plan.summary_error}</p>
      )}
      <div className="plan-buttons">
        {plan.drafts.map((d) => (
          <AsyncButton
            key={d.id}
            className="button"
            disabled={!presenter}
            busyLabel="Abriendo correo…"
            onAction={async () => {
              try {
                setMessage("");
                setDraft(await api("/drafts/" + d.id));
              } catch (e) {
                setError((e as Error).message);
                throw e;
              }
            }}
          >
            <FileText size={16} aria-hidden /> {d.label} (
            {d.language.toUpperCase()})
          </AsyncButton>
        ))}
        {presenter && llm?.configured && onPlan && (
          <AsyncButton
            className="button"
            busyLabel="Claude está redactando…"
            onAction={async () => {
              try {
                const r = await api(
                  "/incidents/" + plan.incident_id + "/plan/summary",
                  { method: "POST" },
                );
                if (r.plan) onPlan(r.plan);
              } catch (e) {
                setError((e as Error).message);
                throw e;
              }
            }}
          >
            <Bot size={16} aria-hidden /> Volver a redactar con Claude
          </AsyncButton>
        )}
      </div>
      {!presenter && plan.drafts.length > 0 && (
        <p className="plan-note">
          Los correos se abren con acceso de presentador.
        </p>
      )}
      {error && <p role="alert">{error}</p>}
      <dialog
        ref={dialog}
        className="workspace-dialog"
        onClose={() => setDraft(null)}
      >
        <div className="section-heading">
          <h3>Correo del plan</h3>
          <button
            className="button"
            aria-label="Cerrar correo"
            onClick={() => dialog.current?.close()}
          >
            Cerrar
          </button>
        </div>
        <p>
          Borrador editable en el idioma del destinatario. No se envía a nadie.
        </p>
        {message && <p role="status">{message}</p>}
        {draft && (
          <>
            <label>
              Texto del correo
              <textarea
                aria-label="Texto del correo del plan"
                value={draft.text}
                onChange={(e) => setDraft({ ...draft, text: e.target.value })}
              />
            </label>
            <div className="inline">
              <AsyncButton
                className="button primary"
                busyLabel="Guardando…"
                onAction={async () => {
                  await api("/drafts/" + draft.id, {
                    method: "PATCH",
                    body: JSON.stringify({ text: draft.text }),
                  });
                  setMessage("Correo guardado.");
                }}
              >
                Guardar
              </AsyncButton>
              <button
                className="button"
                onClick={() =>
                  navigator.clipboard
                    .writeText(draft.text)
                    .then(() => setMessage("Texto copiado al portapapeles."))
                }
              >
                Copiar
              </button>
              {llm?.configured && (
                <AsyncButton
                  className="button"
                  busyLabel="Claude está redactando…"
                  onAction={async () => {
                    const r = await api("/drafts/" + draft.id + "/assist", {
                      method: "POST",
                    });
                    setDraft({ ...draft, text: r.text });
                    setMessage(
                      r.llm_error ||
                        "Reescrito por Claude en el mismo idioma. Revísalo antes de usarlo.",
                    );
                  }}
                >
                  <Bot size={16} aria-hidden /> Mejorar con Claude
                </AsyncButton>
              )}
            </div>
          </>
        )}
      </dialog>
    </section>
  );
}

/** Plan of one incident on the supplier page; the Claude summary arrives from a low-priority job. */
export function ActionPlan({
  incidentId,
  presenter,
}: {
  incidentId: string;
  presenter: boolean;
}) {
  const [data, setData] = useState<{ plan: Plan | null; llm: Llm } | null>(
      null,
    ),
    [error, setError] = useState("");
  async function load() {
    try {
      setData(await api("/incidents/" + incidentId + "/plan"));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    void load();
  }, [incidentId, presenter]);
  const waiting =
    presenter &&
    !!data?.plan &&
    data.llm.configured &&
    data.plan.summary_source === "template" &&
    !data.plan.summary_error;
  useEffect(() => {
    if (!waiting) return;
    let tries = 0;
    const timer = setInterval(() => {
      if (++tries > 12) clearInterval(timer);
      else if (!document.hidden) void load();
    }, 5000);
    return () => clearInterval(timer);
  }, [waiting, incidentId]);
  if (error)
    return (
      <p role="alert">
        {error}{" "}
        <button className="button" onClick={load}>
          Recargar plan
        </button>
      </p>
    );
  if (!data) return <p role="status">Cargando plan de acción…</p>;
  if (!data.plan) return null;
  return (
    <>
      <PlanCard
        plan={data.plan}
        presenter={presenter}
        llm={data.llm}
        onPlan={(plan) => setData({ ...data, plan })}
      />
      {waiting && (
        <small role="status">Claude está redactando el resumen…</small>
      )}
    </>
  );
}
