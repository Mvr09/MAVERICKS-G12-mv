import { geoNaturalEarth1, geoPath } from "d3-geo";
import type { Feature, FeatureCollection, MultiPoint } from "geojson";
import { useMemo, useState } from "react";
import { feature } from "topojson-client";
import type { GeometryCollection, Topology } from "topojson-specification";
import world from "world-atlas/countries-110m.json";
import { eventNames } from "./EventTag";
import { coordsOf } from "./geo";
import { bandFor } from "./policy";
import type { Supplier } from "./types";

export type Band = "critical" | "high" | "medium" | "low";

export interface MapSupplier {
  id: string;
  name: string;
  city: string | null;
  country: string | null;
  band: Band | null;
  priority: number | null;
  urgent: boolean;
  spend: number | null; // annual spend with the supplier, EUR
}

export interface MapEvent {
  id: string;
  label: string;
  headline: string | null;
  supplierIds: string[];
  urgent: boolean;
  byLocation: boolean;
}

const W = 960;
const H = 500;
const TOPO = world as unknown as Topology;
const LAND = feature(
  TOPO,
  TOPO.objects.countries as GeometryCollection,
) as FeatureCollection;

// Each region is a lon/lat box; the projection is fitted to it.
const REGIONS: {
  id: string;
  label: string;
  box: [[number, number], [number, number]];
}[] = [
  { id: "world", label: "Mundo", box: [[-125, -35], [145, 62]] },
  { id: "europe", label: "Europa", box: [[-12, 34], [24, 61]] },
  { id: "asia", label: "Asia", box: [[68, 0], [140, 40]] },
  { id: "america", label: "América", box: [[-110, -30], [-40, 46]] },
];

const BAND_FILL: Record<Band, string> = {
  critical: "#dc2626",
  high: "#ea580c",
  medium: "#ca8a04",
  low: "#16a34a",
};
const BAND_ORDER: [Band, string][] = [
  ["critical", "Crítica"],
  ["high", "Alta"],
  ["medium", "Media"],
  ["low", "Baja"],
];
const NO_RISK = "#94a3b8";
// Point size encodes annual spend (priority is already the colour). Area grows
// linearly with spend between R_MIN and R_MAX, so twice the spend never looks
// four times bigger.
const R_MIN = 4;
const R_MAX = 14;
const radiusFor = (spend: number | null, max: number) =>
  Math.sqrt(
    R_MIN ** 2 +
      (R_MAX ** 2 - R_MIN ** 2) * (max > 0 ? Math.max(spend ?? 0, 0) / max : 0),
  );
const eur = (v: number) =>
  v >= 1e6
    ? `${(v / 1e6).toLocaleString("es-ES", { maximumFractionDigits: 1 })} M€`
    : `${Math.round(v / 1e3).toLocaleString("es-ES")} k€`;

const fmt = (p: number | null) =>
  p === null
    ? "—"
    : p.toLocaleString("es-ES", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      });

// Band from the policy served by /api/config; the challenge cut-offs are the
// fallback while that configuration has not loaded yet.
function bandOf(p: number | null): Band | null {
  if (p === null || p <= 0) return null;
  const id = bandFor(p);
  if (id in BAND_FILL) return id as Band;
  return p >= 80 ? "critical" : p >= 65 ? "high" : p >= 35 ? "medium" : "low";
}

const LEGAL =
  /^(ltd|limited|gmbh|ag|inc|as|sa|s\.a\.|spa|s\.p\.a\.|srl|bv|nv|plc|co|corp|llc|pvt|kk|oy|ab)$/i;

// Linked by location when the supplier is not named in the news text.
function namedIn(name: string, text: string) {
  const words = name
    .split(/\s+/)
    .filter((w) => !LEGAL.test(w.replace(/[.,]/g, "")))
    .slice(0, 2);
  const haystack = text.toLowerCase();
  return words.every((w) => haystack.includes(w.toLowerCase()));
}

/** Map data for the scope being viewed: every catalogue supplier, plus one
 * event per news story behind the open (non-resolved) incidents. */
export function toMapData(suppliers: Supplier[]): {
  suppliers: MapSupplier[];
  events: MapEvent[];
} {
  const events = new Map<string, MapEvent>();
  for (const s of suppliers) {
    for (const incident of s.incidents || []) {
      if (incident.state === "resolved") continue;
      const latest =
        [...(incident.history || [])].reverse().find((h) => !h.superseded) ||
        incident.history?.at(-1);
      const assessment = latest?.assessment;
      const headline = incident.current_headline || latest?.headline || null;
      // The same news can arrive in several files: one event per type + headline.
      const key = headline
        ? `${incident.event_type}|${headline}`
        : latest?.article_id || incident.id;
      const e: MapEvent = events.get(key) ?? {
        id: key,
        label: eventNames[incident.event_type] || incident.event_type,
        headline,
        supplierIds: [],
        urgent: false,
        byLocation: false,
      };
      if (!e.supplierIds.includes(s.supplier_id))
        e.supplierIds.push(s.supplier_id);
      e.urgent ||= assessment?.urgent === "Y";
      const kind = assessment?.exposure_kind;
      const text = `${latest?.headline || ""} ${(latest?.explanation || "").replace(`${s.name}:`, "")}`;
      e.byLocation ||=
        kind === "potential" ||
        kind === "unknown" ||
        (kind !== "reported" && kind !== "identity" && !namedIn(s.name, text));
      events.set(key, e);
    }
  }
  return {
    suppliers: suppliers.map((s) => {
      const priority = s.priority !== null && s.priority > 0 ? s.priority : null;
      return {
        id: s.supplier_id,
        name: s.name,
        city: s.city,
        country: s.country,
        priority,
        band: bandOf(priority),
        urgent: s.urgent,
        spend: Number.isFinite(s.annual_spend) ? s.annual_spend : null,
      };
    }),
    events: [...events.values()],
  };
}

/** Suppliers on a world map coloured by current priority band (urgent = fixed red ring).
 * Open events are listed below; hovering one highlights the suppliers it reaches. */
export function SupplierMap({
  suppliers,
  events,
  onSupplierClick,
}: {
  suppliers: MapSupplier[];
  events: MapEvent[];
  onSupplierClick?: (id: string) => void;
}) {
  const [region, setRegion] = useState("world");
  const [focus, setFocus] = useState<string | null>(null);

  // Urgent events first, then the ones that reach more suppliers.
  const sortedEvents = useMemo(
    () =>
      [...events].sort(
        (x, y) =>
          Number(y.urgent) - Number(x.urgent) ||
          y.supplierIds.length - x.supplierIds.length,
      ),
    [events],
  );

  const box = REGIONS.find((r) => r.id === region)!.box;
  const projection = useMemo(() => {
    const frame: Feature<MultiPoint> = {
      type: "Feature",
      properties: {},
      geometry: {
        type: "MultiPoint",
        coordinates: [
          box[0],
          [box[1][0], box[0][1]],
          box[1],
          [box[0][0], box[1][1]],
        ],
      },
    };
    return geoNaturalEarth1().fitExtent(
      [
        [16, 16],
        [W - 16, H - 16],
      ],
      frame,
    );
  }, [box]);
  const path = geoPath(projection);
  const highlighted = new Set(
    focus ? sortedEvents.find((e) => e.id === focus)?.supplierIds : [],
  );

  const spends = suppliers.flatMap((s) => (s.spend !== null ? [s.spend] : []));
  const maxSpend = Math.max(0, ...spends);

  const points = suppliers
    .map((s) => ({ s, ll: coordsOf(s.city, s.country) }))
    .filter(
      (p): p is { s: MapSupplier; ll: [number, number] } => p.ll !== null,
    )
    .map((p) => ({ ...p, px: projection(p.ll) }))
    .filter((p) => p.px !== null)
    // draw suppliers at risk last so they stay on top
    .sort((a, b) => (a.s.priority ?? -1) - (b.s.priority ?? -1));

  const presentBands = new Set<Band>(
    points.flatMap((p) => (p.s.band ? [p.s.band] : [])),
  );
  const hasNoRisk = points.some((p) => !p.s.band);
  const legend: [string, string][] = [
    ...BAND_ORDER.filter(([b]) => presentBands.has(b)).map(
      ([b, l]) => [BAND_FILL[b], l] as [string, string],
    ),
    ...(hasNoRisk
      ? ([[NO_RISK, "Sin riesgo abierto"]] as [string, string][])
      : []),
  ];

  return (
    <div className="flex flex-col gap-3">
      <div
        className="flex flex-wrap gap-1.5"
        role="group"
        aria-label="Región del mapa"
      >
        {REGIONS.map((r) => (
          <button
            key={r.id}
            type="button"
            onClick={() => setRegion(r.id)}
            aria-pressed={region === r.id}
            className={`min-h-[36px] rounded-full px-3 text-sm ring-1 ring-inset ${
              region === r.id
                ? "bg-accent text-white ring-accent"
                : "bg-white text-slate-500 ring-slate-200 hover:text-accent"
            }`}
          >
            {r.label}
          </button>
        ))}
      </div>

      <figure className="m-0 overflow-hidden rounded-lg border border-slate-200 bg-sky-50/60">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="block h-auto w-full"
          role="img"
          aria-label="Mapa de proveedores coloreados por prioridad"
        >
          <g>
            {LAND.features.map((f, i) => (
              <path
                key={i}
                d={path(f) ?? undefined}
                fill="#e2e8f0"
                stroke="#ffffff"
                strokeWidth={0.6}
              />
            ))}
          </g>
          {points.map(({ s, px }) => {
            const [x, y] = px as [number, number];
            const on = highlighted.has(s.id);
            const r = radiusFor(s.spend, maxSpend);
            return (
              <g
                key={s.id}
                data-supplier={s.id}
                className={onSupplierClick ? "cursor-pointer" : undefined}
                onClick={
                  onSupplierClick ? () => onSupplierClick(s.id) : undefined
                }
                opacity={focus && !on ? 0.25 : 1}
              >
                {s.urgent && (
                  <circle
                    cx={x}
                    cy={y}
                    r={r + 4}
                    fill="none"
                    stroke="#dc2626"
                    strokeWidth={2}
                  />
                )}
                <circle
                  cx={x}
                  cy={y}
                  r={r}
                  fill={s.band ? BAND_FILL[s.band] : NO_RISK}
                  stroke={on ? "#1e1b4b" : "#ffffff"}
                  strokeWidth={on ? 2.5 : 1.2}
                />
                <title>
                  {`${s.name} (${s.city}, ${s.country})${
                    s.band
                      ? ` · prioridad ${fmt(s.priority)}${s.urgent ? " · urgente" : ""}`
                      : " · sin riesgo abierto"
                  }${s.spend !== null ? ` · gasto anual ${eur(s.spend)}` : ""}`}
                </title>
              </g>
            );
          })}
        </svg>
        <figcaption className="flex flex-wrap gap-x-3 gap-y-1 px-3 py-2 text-xs text-slate-500">
          {/* Only the bands that are on the map: never show a band nobody has. */}
          <span className="font-medium">Prioridad:</span>
          {legend.map(([c, l]) => (
            <span key={l} className="inline-flex items-center gap-1">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ background: c }}
              />{" "}
              {l}
            </span>
          ))}
          <span className="inline-flex items-center gap-1">
            ·{" "}
            <span className="inline-block h-3 w-3 rounded-full border-2 border-red-600" />{" "}
            Urgente
          </span>
          {maxSpend > 0 && <span>· Tamaño = Gasto anual</span>}
          <span>
            · pulse un punto para abrir la ficha · ubicación aproximada por
            ciudad
          </span>
        </figcaption>
      </figure>

      {sortedEvents.length > 0 && (
        <div>
          <p className="mb-1.5 text-sm font-semibold">
            Eventos abiertos ({sortedEvents.length}) · pase el ratón o pulse
            para ver a quién afectan
          </p>
          <ul className="m-0 flex list-none flex-wrap gap-1.5 p-0">
            {sortedEvents.map((e) => (
              <li key={e.id} className="min-w-0 max-w-full">
                <button
                  type="button"
                  onMouseEnter={() => setFocus(e.id)}
                  onMouseLeave={() => setFocus(null)}
                  onFocus={() => setFocus(e.id)}
                  onBlur={() => setFocus(null)}
                  onClick={() => setFocus(focus === e.id ? null : e.id)}
                  title={e.headline ?? e.label}
                  className={`min-h-[36px] max-w-full truncate rounded-full px-3 text-left text-xs ring-1 ring-inset sm:max-w-[22rem] ${
                    focus === e.id
                      ? "bg-accent text-white ring-accent"
                      : e.urgent
                        ? "bg-red-50 text-red-900 ring-red-200"
                        : "bg-white text-slate-700 ring-slate-200"
                  }`}
                >
                  <span className="font-semibold">{e.label}</span>
                  {e.headline ? `: ${e.headline}` : ""} ·{" "}
                  {e.supplierIds.length} prov.
                  {e.byLocation ? " · por ubicación" : ""}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
