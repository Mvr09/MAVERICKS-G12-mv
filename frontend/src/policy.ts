// Numeric band boundaries are supplied by config/risk_policy.json through the API.
export interface Band {
  id: string;
  label_es: string;
  min: number;
}
let bands: Band[] = [];
export function setBands(value: Band[]) {
  bands = [...value].sort((a, b) => a.min - b.min);
}
export function getBands() {
  return bands;
}
export function bandFor(value: number | null) {
  if (value === null) return "pending";
  return bands.filter((b) => value >= b.min).at(-1)?.id || "unknown";
}
