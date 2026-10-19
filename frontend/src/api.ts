let csrf = "";
export function setCsrf(v: string) {
  csrf = v;
}
export async function api<T = any>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  if (options.method && options.method !== "GET")
    headers.set("X-CSRF-Token", csrf);
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 30000);
  try {
    const response = await fetch("/api" + path, {
      ...options,
      headers,
      credentials: "same-origin",
      signal: options.signal
        ? AbortSignal.any([options.signal, controller.signal])
        : controller.signal,
    });
    if (!response.ok) {
      const e = await response.json().catch(() => ({}));
      const error = new Error(
        (typeof e.detail === "string" ? e.detail : e.message) ||
          "No se pudo completar la operación",
      ) as Error & { status: number };
      error.status = response.status;
      throw error;
    }
    return await response.json();
  } catch (e) {
    if (controller.signal.aborted)
      throw new Error(
        "La operación tardó demasiado. Consulta su estado guardado antes de reintentar.",
      );
    if (e instanceof TypeError)
      throw new Error(
        "No se pudo conectar. Conservamos los datos visibles; vuelve a consultar el estado.",
      );
    throw e;
  } finally {
    clearTimeout(timer);
  }
}
export const date = (v?: string) =>
  v
    ? new Intl.DateTimeFormat("es-ES", {
        dateStyle: "short",
        timeStyle: "short",
        timeZone: "Europe/Madrid",
      }).format(new Date(v))
    : "Sin consultar";
export const number = (v: number | null | undefined) =>
  v == null ? "—" : v.toLocaleString("es-ES", { maximumFractionDigits: 1 });
