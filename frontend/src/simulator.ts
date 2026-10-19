export function integer(value: string): number | null {
  if (!value.trim()) return null;
  const n = Number(value);
  return Number.isSafeInteger(n) && n >= 0 ? n : null;
}
export function estimate(
  x: string,
  y: string,
  rate: string,
  mean: number | null,
) {
  const news = integer(x),
    tokensPerNews = integer(y),
    price = rate.trim() ? Number(rate) : NaN;
  if (
    news === null ||
    tokensPerNews === null ||
    !Number.isFinite(price) ||
    price < 0
  )
    return {
      error:
        "Introduce noticias y tokens enteros no negativos y una tasa finita no negativa.",
    };
  const tokens = news * tokensPerNews,
    cost = (tokens / 1_000_000) * price;
  const seconds = news === 0 ? 0 : mean == null ? null : news * mean;
  if (
    ![tokens, cost, ...(seconds == null ? [] : [seconds])].every(
      Number.isFinite,
    )
  )
    return { error: "El escenario excede el rango numérico disponible." };
  return { tokens, cost, seconds };
}
export function amount(n: number) {
  if (n > 0 && n < 1e-8) return "<0,00000001 $";
  return (
    n.toLocaleString("es-ES", {
      minimumFractionDigits: n === 0 ? 0 : 4,
      maximumFractionDigits: 8,
    }) + " $"
  );
}
