import { useLayoutEffect, useRef, type CSSProperties, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Boxes, Euro, Hourglass, Link2Off } from "lucide-react";
import type { Supplier } from "./types";
import { scopedPath } from "./NewsContinuity";
import { exposureMetrics } from "./exposureMetrics";
import "./BusinessKpis.css";

const euro = new Intl.NumberFormat("es-ES", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});
const decimal = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 1 });

/** Compact euros for the tile (31,8 M€ · 400 k€); the full amount goes in the hover hint. */
const compactEuro = (v: number) =>
  v >= 999_950
    ? `${decimal.format(v / 1_000_000)} M€`
    : v >= 1_000
      ? `${decimal.format(Math.round(v / 1_000))} k€`
      : euro.format(v);

const share = (v: number | null) =>
  v == null ? "sin gasto registrado" : v > 0 && v < 1 ? "<1 %" : `${Math.round(v)} %`;

export function BusinessKpis({
  suppliers,
  context,
}: {
  suppliers: Supplier[];
  context: string;
}) {
  const k = exposureMetrics(suppliers);
  const tiles: {
    label: string;
    value: string | number;
    unit?: string;
    /** Shown on hover over the whole card. */
    hint?: string;
    note: string;
    icon: ReactNode;
    tone: string;
  }[] = [
    {
      label: "Gasto anual expuesto",
      value: compactEuro(k.exposedSpend),
      note: `${share(k.spendShare)} del gasto de cartera`,
      hint: `${euro.format(k.exposedSpend)} · gasto total del proveedor, no por producto`,
      icon: <Euro />,
      tone: "cyan",
    },
    {
      label: "Productos sin\u00a0plan\u00a0B",
      value: `${k.unbackedProducts} / ${k.products}`,
      note: `expuestos en total: ${k.riskProducts}\u00a0/\u00a0${k.products}`,
      icon: <Boxes />,
      tone: "blue",
    },
    {
      label: "Fuente única afectados",
      value: k.singleSource,
      note: `${k.singleSource} de ${k.singleSourceTotal} fuentes únicas de la cartera`,
      hint: k.singleSourceNames.join(", ") || undefined,
      icon: <Link2Off />,
      tone: "purple",
    },
    {
      label: "Cobertura insuficiente",
      value: k.coverageShort,
      // Non-breaking spaces keep "sin dato: N" and "no aplica: N" on one line.
      note: `Stock menor que el plazo de reposición · sin\u00a0dato:\u00a0${k.coverageUnknown} · no\u00a0aplica:\u00a0${k.coverageNotApplicable}`,
      hint: k.coverageShortNames.join(", ") || undefined,
      icon: <Hourglass />,
      tone: "green",
    },
  ];
  const grid = useRef<HTMLDivElement>(null);
  const shown = tiles.map((t) => `${t.value} ${t.unit || ""}`).join("|");
  // Same size as the Resumen tiles; shrink every value together only when one does not fit.
  useLayoutEffect(() => {
    const el = grid.current;
    if (!el) return;
    let width = -1;
    const fit = () => {
      const values = [...el.querySelectorAll<HTMLElement>(".bkpi-value")];
      values.forEach((v) => (v.style.fontSize = ""));
      const scale = Math.min(1, ...values.map((v) => v.clientWidth / v.scrollWidth || 1));
      if (scale >= 1 || !values.length) return;
      const base = parseFloat(getComputedStyle(values[0]).fontSize);
      const size = Math.max(14, Math.floor(base * scale * 0.98));
      values.forEach((v) => (v.style.fontSize = size + "px"));
    };
    fit();
    const observer = new ResizeObserver(([entry]) => {
      if (entry.contentRect.width === width) return;
      width = entry.contentRect.width;
      fit();
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [shown]);
  return (
    <section className="bkpi" aria-labelledby="bkpi-title">
      <div className="bkpi-heading">
        <div>
          <div className="eyebrow">COMPRAS · EXPOSICIÓN DE CARTERA</div>
          <h2 id="bkpi-title">Exposición de compras</h2>
          <p>
            Sobre {k.exposed}{" "}
            {k.exposed === 1 ? "proveedor" : "proveedores"} con incidente
            activo ({k.activeIncidents}{" "}
            {k.activeIncidents === 1 ? "incidente" : "incidentes"}) en el origen
            seleccionado · por validar: {k.exposedReview}{" "}
            · cartera ficticia, solo lectura
          </p>
        </div>
        <Link className="text-link" to={scopedPath("/proveedores", context)}>
          Ver proveedores <ArrowRight size={16} />
        </Link>
      </div>
      <div
        className="bkpi-grid"
        ref={grid}
        style={{ "--bkpi-cols": tiles.length } as CSSProperties}
      >
        {tiles.map((t) => (
          <div className="kpi card" key={t.label} title={t.hint}>
            <div className="kpi-top">
              <span>{t.label}</span>
              <div className={"kpi-icon " + t.tone}>{t.icon}</div>
            </div>
            <div className="kpi-value bkpi-value">
              <span className="bkpi-num">{t.value}</span>
              {t.unit && <span className="bkpi-unit">{t.unit}</span>}
            </div>
            <small>{t.note}</small>
          </div>
        ))}
      </div>
    </section>
  );
}
