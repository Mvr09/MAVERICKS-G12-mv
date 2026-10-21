import { AsyncButton } from "./OperationFeedback";
import { useEffect, useState } from "react";
import { api } from "./api";

type PlanAction = {
  code: string;
  label: string;
  reason: string;
  deadline: string;
  deadline_label: string;
};
type Plan = {
  revision: number;
  rules_version: string;
  actions: PlanAction[];
  summary: string;
  summary_source: "llm" | "template";
  summary_error: string | null;
  llm: { model: string; served_by: string | null } | null;
};
type PlanResponse = {
  plan: Plan | null;
  llm: { model: string; configured: boolean };
};

const DEADLINE_DAYS: Record<string, number> = { hoy: 0, esta_semana: 7 };

function dueDate(deadline: string) {
  const days = DEADLINE_DAYS[deadline];
  if (days === undefined) return "";
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

/** Suggested actions only. Adopting one pre-fills the human follow-up; nothing is saved automatically. */
export function ActionPlan({ incidentId }: { incidentId: string }) {
  const [data, setData] = useState<PlanResponse | null>(null),
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
  }, [incidentId]);
  // The Claude summary is a low-priority worker job: check back a few times.
  const waiting =
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
  if (!data) return <p role="status">Cargando plan sugerido…</p>;
  const plan = data.plan;
  if (!plan) return null;
  return (
    <details className="incident-work action-plan" open>
      <summary>
        Plan sugerido · {plan.actions.length} acciones
        {plan.summary_source === "llm" ? " · redactado por Claude" : ""}
      </summary>
      <p className="small-note">
        Sugerencia por reglas ({plan.rules_version}). No cambia la
        clasificación, la prioridad ni las alertas, y no se guarda en el
        seguimiento hasta que tú lo registres.
      </p>
      <div className="fact-box">
        <span
          className={
            "badge " + (plan.summary_source === "llm" ? "purple" : "neutral")
          }
        >
          {plan.summary_source === "llm"
            ? "Claude · " + (plan.llm?.served_by || plan.llm?.model || "")
            : "Plantilla"}
        </span>
        <p>{plan.summary}</p>
        {waiting && (
          <small role="status">Claude está redactando el resumen…</small>
        )}
        {plan.summary_error && <small>{plan.summary_error}</small>}
      </div>
      <ol className="plan-actions">
        {plan.actions.map((a) => (
          <li key={a.code}>
            <div>
              <strong>{a.label}</strong>
              <span
                className={"badge " + (a.deadline === "hoy" ? "danger" : "neutral")}
              >
                {a.deadline_label}
              </span>
            </div>
            <small>{a.reason}</small>
            <button
              className="button"
              onClick={() =>
                window.dispatchEvent(
                  new CustomEvent("radar:plan-action", {
                    detail: {
                      incidentId,
                      action: a.label,
                      due: dueDate(a.deadline),
                    },
                  }),
                )
              }
            >
              Usar en el seguimiento
            </button>
          </li>
        ))}
      </ol>
      {data.llm.configured && (
        <AsyncButton
          className="button"
          busyLabel="Claude está redactando…"
          onAction={async () => {
            try {
              setData(
                await api("/incidents/" + incidentId + "/plan/summary", {
                  method: "POST",
                }),
              );
            } catch (e) {
              setError((e as Error).message);
              throw e;
            }
          }}
        >
          Volver a redactar con Claude
        </AsyncButton>
      )}
    </details>
  );
}
