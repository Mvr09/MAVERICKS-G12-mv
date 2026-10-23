import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { api } from "./api";

export const PRESENTATION_ORIGIN =
  "https://helixa-signal-to-action.jvaswiss-9277.chatgpt.site";
const embedded = () => window.self !== window.top;

export function EmbedIntegration({
  ready,
  presenter,
  context,
  onSession,
}: {
  ready: boolean;
  presenter: boolean;
  context: string;
  onSession: (s: { presenter: boolean; csrf?: string }) => void;
}) {
  const location = useLocation(),
    requestId = useRef<string | null>(null);
  const [busy, setBusy] = useState(false),
    [message, setMessage] = useState("");
  useEffect(() => {
    if (!embedded()) return;
    const send = (type: string) => {
      if (!ready || !requestId.current) return;
      window.parent.postMessage(
        {
          type,
          version: 1,
          requestId: requestId.current,
          path: location.pathname,
          context: context === "rss" ? "rss" : "exercise",
        },
        PRESENTATION_ORIGIN,
      );
    };
    const receive = (e: MessageEvent) => {
      if (e.source !== window.parent || e.origin !== PRESENTATION_ORIGIN)
        return;
      const d = e.data;
      if (
        !d ||
        d.type !== "helixa:hello" ||
        d.version !== 1 ||
        typeof d.requestId !== "string" ||
        !/^[a-zA-Z0-9-]{16,80}$/.test(d.requestId)
      )
        return;
      requestId.current = d.requestId;
      send("radar:ready");
    };
    window.addEventListener("message", receive);
    send("radar:ready");
    return () => window.removeEventListener("message", receive);
  }, [ready, location.pathname, context]);
  if (!embedded()) return null;
  return (
    <aside
      className="embed-notice"
      aria-label="Aplicación integrada en presentación"
    >
      <div>
        <strong>Modo presentación</strong>
        <span>
          {presenter
            ? "Sesión de presentador activa en este marco."
            : "Puedes consultar la demo o iniciar sesión aquí. El navegador puede aislar esta sesión."}
        </span>
      </div>
      <a
        className="button small"
        target="_blank"
        rel="noopener noreferrer"
        href={
          window.location.origin +
          location.pathname +
          "?context=" +
          (context === "rss" ? "rss" : "exercise")
        }
      >
        Abrir app en una ventana ↗
      </a>
      {!presenter && (
        <details>
          <summary>¿El navegador no conserva tu sesión?</summary>
          <p>
            Primero intenta iniciar sesión dentro de la app. Si el navegador la
            bloquea, abre la app en una ventana, inicia sesión allí y vuelve
            para conceder acceso. También puedes continuar en esa ventana.
          </p>
          <button
            className="button small"
            disabled={busy}
            aria-busy={busy}
            onClick={async () => {
              setBusy(true);
              setMessage("");
              try {
                const doc = document as Document & {
                  requestStorageAccess?: () => Promise<void>;
                };
                if (!doc.requestStorageAccess)
                  throw new Error(
                    "Este navegador no ofrece acceso de sesión adicional. Continúa con «Abrir app en una ventana».",
                  );
                // Call directly in the user gesture; never use a token/URL/message bridge.
                await doc.requestStorageAccess();
                const s = await api("/session");
                if (!s.presenter)
                  throw new Error(
                    "Acceso concedido. Inicia sesión aquí o abre la app en una ventana para autenticarte.",
                  );
                onSession(s);
                setMessage(
                  "Sesión recuperada. Ya puedes operar en la presentación.",
                );
              } catch (e) {
                setMessage(
                  (e as Error).name === "NotAllowedError"
                    ? "El navegador no ha concedido acceso. Abre la app en una ventana e inicia sesión allí; puedes continuar en esa ventana sin cambiar sus protecciones."
                    : (e as Error).message,
                );
              } finally {
                setBusy(false);
              }
            }}
          >
            {busy ? "Comprobando acceso…" : "Conceder acceso a mi sesión"}
          </button>
          {message && <p role="status">{message}</p>}
        </details>
      )}
    </aside>
  );
}
