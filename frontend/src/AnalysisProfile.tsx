export const CANDIDATE = "radar-1.0.0-candidate";
export const DEFAULT_ANALYSIS_PROFILE = CANDIDATE;
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
        <option value={CANDIDATE}>Perfil actual · 3.4.2 · recomendado</option>
        <optgroup label="Opciones avanzadas · perfiles anteriores">
          <option value="1.0.0">
            1.0.0 · anterior / rollback{rss ? " (RSS 2.2)" : ""}
          </option>
          {!rss && (
            <option value="link-2.2.0">2.2 · experimental anterior</option>
          )}
        </optgroup>
      </select>
      {value === CANDIDATE && (
        <small>
          Perfil actual 3.4.2 · matching 3.3 / revisión 1.3.1. Conserva dudas
          que pueden cambiar la decisión. Evaluación conocida; no demuestra
          generalización a RSS.
        </small>
      )}
    </label>
  );
}
