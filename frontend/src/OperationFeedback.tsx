import { useRef, useState } from "react";
import type { ReactNode } from "react";
export function LoadingBlock({
  label = "Cargando datos…",
}: {
  label?: string;
}) {
  return (
    <section className="card loading-block" role="status" aria-busy="true">
      <p>
        <span className="operation-spinner" aria-hidden="true" />
        {label}
      </p>
      <div className="skeleton-row" />
      <div className="skeleton-grid">
        <span />
        <span />
        <span />
      </div>
    </section>
  );
}
export function AsyncButton({
  children,
  onAction,
  busyLabel = "Procesando…",
  className = "button",
  disabled = false,
  successLabel = "",
}: {
  children: ReactNode;
  onAction: () => Promise<unknown>;
  busyLabel?: string;
  className?: string;
  disabled?: boolean;
  successLabel?: string;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  const fence = useRef(false);
  return (
    <span className="async-control">
      <button
        type="button"
        className={className}
        disabled={disabled || busy}
        aria-busy={busy}
        onClick={async () => {
          if (fence.current) return;
          fence.current = true;
          setBusy(true);
          setError("");
          setMessage("");
          try {
            await onAction();
            setMessage(successLabel);
          } catch (e) {
            setError(
              (e as Error).message ||
                "No se pudo completar. Conservamos tus datos.",
            );
          } finally {
            fence.current = false;
            setBusy(false);
          }
        }}
      >
        {busy ? (
          <>
            <span className="operation-spinner" aria-hidden="true" />
            {busyLabel}
          </>
        ) : (
          children
        )}
      </button>
      {message && <small role="status">{message}</small>}
      {error && <small role="alert">{error}</small>}
    </span>
  );
}
export async function downloadFile(url: string, filename: string) {
  const controller = new AbortController(),
    timer = setTimeout(() => controller.abort(), 30000);
  try {
    const r = await fetch(url, {
      credentials: "same-origin",
      signal: controller.signal,
    });
    if (!r.ok)
      throw new Error(
        "No se pudo preparar la descarga. Revisa si el lote terminó sin errores.",
      );
    const blob = await r.blob();
    const href = URL.createObjectURL(blob),
      a = document.createElement("a");
    a.href = href;
    a.download = filename;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(href), 1000);
  } catch (e) {
    if (controller.signal.aborted)
      throw new Error(
        "La descarga tardó demasiado. Puedes volver a prepararla.",
      );
    if (e instanceof TypeError)
      throw new Error(
        "No se pudo descargar. Comprueba la conexión y vuelve a intentarlo.",
      );
    throw e;
  } finally {
    clearTimeout(timer);
  }
}
