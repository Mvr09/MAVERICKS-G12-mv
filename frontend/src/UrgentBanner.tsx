import { AlertTriangle, ArrowRight, X } from "lucide-react";
import { useState } from "react";
import type { Plan } from "./ActionPlan";

const SEEN = "radar:urgent-banner-seen";

function seen() {
  try {
    return sessionStorage.getItem(SEEN) === "1";
  } catch {
    return false;
  }
}

/** Three-line briefing shown when the app opens: how many suppliers are urgent, what is due
 * today and where to start. The arrow (or the close button) dismisses it for this session. */
export function UrgentBanner({
  plans,
  onGo,
}: {
  plans: Record<string, Plan | null>;
  onGo: () => void;
}) {
  const [hidden, setHidden] = useState(seen);
  const urgent = Object.values(plans)
    .filter((p): p is Plan => !!p && p.facts.incidente.urgente)
    .sort(
      (a, b) => (b.facts.incidente.prioridad ?? 0) - (a.facts.incidente.prioridad ?? 0),
    );
  if (hidden || !urgent.length) return null;
  const names = [...new Set(urgent.map((p) => p.facts.proveedor.nombre))];
  const actions = urgent.flatMap((p) => p.actions);
  const today = actions.filter((a) => a.deadline === "hoy").length,
    week = actions.filter((a) => a.deadline === "esta_semana").length;
  const first = urgent[0],
    next = first.actions.find((a) => a.deadline === "hoy") ?? first.actions[0];
  function dismiss() {
    try {
      sessionStorage.setItem(SEEN, "1");
    } catch {
      /* Without storage the banner simply returns on the next load. */
    }
    setHidden(true);
  }
  return (
    <section className="urgent-banner" role="alert" aria-label="Urgencias de hoy">
      <AlertTriangle size={24} aria-hidden className="urgent-banner-icon" />
      <div className="urgent-banner-text">
        <strong>
          Tienes {names.length}{" "}
          {names.length === 1 ? "proveedor" : "proveedores"} en situación
          urgente: {names.slice(0, 3).join(", ")}
          {names.length > 3 ? ` y ${names.length - 3} más` : ""}.
        </strong>
        <span>
          {today} {today === 1 ? "acción" : "acciones"} para hoy
          {week ? ` · ${week} para esta semana` : ""}.
        </span>
        {next && (
          <span>
            Empieza por: {next.label.charAt(0).toLowerCase() + next.label.slice(1)}{" "}
            ({first.facts.proveedor.nombre}).
          </span>
        )}
      </div>
      <button
        className="button urgent-banner-go"
        onClick={() => {
          dismiss();
          onGo();
        }}
      >
        Vamos a ver qué hacer <ArrowRight size={17} aria-hidden />
      </button>
      <button
        className="icon-button urgent-banner-close"
        aria-label="Cerrar aviso de urgencias"
        onClick={dismiss}
      >
        <X size={17} />
      </button>
    </section>
  );
}
