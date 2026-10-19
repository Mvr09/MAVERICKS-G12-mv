export const CANDIDATE = "radar-1.0.0-candidate";
export function AnalysisProfile({
  value,
  onChange,
  rss = false,
  disabled = false,
}: {
  value: string;
  onChange: (value: string) => void;
  rss?: boolean;
  disabled?: boolean;
}) {
  return (
    <label className="analysis-profile">
      Perfil de análisis
      <select
        aria-label={rss ? "Perfil de análisis RSS" : "Perfil de análisis Excel"}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="1.0.0">
          {rss ? "RSS actual · versión 2.2" : "1.0.0 · predeterminado"}
        </option>
        {!rss && (
          <option value="link-2.2.0">2.2 · experimental anterior</option>
        )}
        <option value={CANDIDATE}>
          Candidata · exposición y revisión focalizada
        </option>
      </select>
      {value === CANDIDATE && (
        <small>
          Candidata 3.4.2 · matching 3.3 / revisión 1.3.1. Conserva dudas que
          pueden cambiar la decisión; no sustituye al predeterminado.
        </small>
      )}
    </label>
  );
}
