import type { Supplier } from "./types";

/** Read-only aggregation of recorded portfolio data. Never changes decisions or scores. */
export function exposureMetrics(suppliers: Supplier[]) {
  // Same definition as views.py: an active or monitoring incident in the current scope.
  const exposed = suppliers.filter((s) => s.incident_count > 0);
  const spend = (rows: Supplier[]) =>
    rows.reduce((sum, s) => sum + (Number(s.annual_spend) || 0), 0);
  const totalSpend = spend(suppliers);
  const exposedSpend = spend(exposed);

  const allProducts = new Set<string>();
  const riskProducts = new Set<string>();
  const unbackedProducts = new Set<string>();
  for (const s of suppliers)
    for (const m of s.materials || []) {
      if (m.primary_id !== s.supplier_id) continue;
      for (const p of m.products || []) {
        allProducts.add(p);
        if (s.incident_count > 0) {
          riskProducts.add(p);
          if (!m.alternate_id) unbackedProducts.add(p);
        }
      }
    }

  const singleSource = exposed.filter((s) => s.single_source === "Y");
  // Logistics and services carry no inventory, as in procurement.ts.
  const physical = exposed.filter(
    (s) => !["Logistics", "Services"].includes(s.category),
  );
  const coverageUnknown = physical.filter(
    (s) => s.inventory_days == null || s.lead_days == null,
  );
  const coverageShort = physical.filter(
    (s) =>
      s.inventory_days != null &&
      s.lead_days != null &&
      s.inventory_days < s.lead_days,
  );

  return {
    suppliers: suppliers.length,
    exposed: exposed.length,
    exposedReview: exposed.filter((s) => s.needs_review).length,
    // Distinct active incidents, as the "Incidentes activos" tile on Resumen.
    activeIncidents: exposed.reduce((sum, s) => sum + s.incident_count, 0),
    totalSpend,
    exposedSpend,
    spendShare: totalSpend > 0 ? (exposedSpend / totalSpend) * 100 : null,
    products: allProducts.size,
    riskProducts: riskProducts.size,
    unbackedProducts: unbackedProducts.size,
    singleSource: singleSource.length,
    singleSourceTotal: suppliers.filter((s) => s.single_source === "Y").length,
    singleSourceNames: singleSource.map((s) => s.name),
    coverageShort: coverageShort.length,
    coverageShortNames: coverageShort.map((s) => s.name),
    coverageUnknown: coverageUnknown.length,
    coverageNotApplicable: exposed.length - physical.length,
  };
}
