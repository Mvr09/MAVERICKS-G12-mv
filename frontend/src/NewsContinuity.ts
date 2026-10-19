import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigationType } from "react-router-dom";

export function scopedPath(path: string, context: string) {
  const url = new URL(path, "https://radar.invalid");
  url.searchParams.set("context", context === "rss" ? "rss" : "exercise");
  return url.pathname + url.search + url.hash;
}
const defaults = {
  q: "",
  state: "",
  human: "",
  preliminary: "",
  source: "",
  split: "",
  from: "",
  to: "",
  event: "",
  relevant: false,
};
type Filters = typeof defaults;
const filterKey = (context: string) => "radar:news-filters:" + context;
const positionKey = (context: string) => "radar:news-position:" + context;
export function useNewsFilters(context: string) {
  const [filters, setFilters] = useState<Filters>(() => {
    try {
      const stored = JSON.parse(
        sessionStorage.getItem(filterKey(context)) || "{}",
      );
      const safe = { ...defaults };
      for (const key of [
        "q",
        "state",
        "human",
        "preliminary",
        "source",
        "split",
        "from",
        "to",
        "event",
      ] as const)
        if (typeof stored[key] === "string") safe[key] = stored[key];
      safe.relevant = stored.relevant === true;
      return safe;
    } catch {
      return { ...defaults };
    }
  });
  useEffect(() => {
    try {
      sessionStorage.setItem(filterKey(context), JSON.stringify(filters));
    } catch {
      /* Session storage may be disabled. */
    }
  }, [context, filters]);
  return [
    filters,
    (patch: Partial<Filters>) => setFilters((old) => ({ ...old, ...patch })),
  ] as const;
}
export function rememberNews(
  context: string,
  id: string,
  element: HTMLElement,
) {
  try {
    sessionStorage.setItem(
      positionKey(context),
      JSON.stringify({
        id,
        y: scrollY,
        offset: element.getBoundingClientRect().top,
      }),
    );
  } catch {
    /* Navigation still works. */
  }
}
export function useNewsReturn(context: string, count: number) {
  const location = useLocation(),
    navigation = useNavigationType(),
    restored = useRef(false);
  useEffect(() => {
    if (restored.current || !count) return;
    if (!location.state?.restoreNews && navigation !== "POP") return;
    try {
      const saved = JSON.parse(
        sessionStorage.getItem(positionKey(context)) || "null",
      );
      if (!saved || typeof saved.y !== "number") return;
      const frame = requestAnimationFrame(() => {
        restored.current = true;
        const anchor = document.getElementById("news-link-" + saved.id);
        const y =
          anchor && typeof saved.offset === "number"
            ? anchor.getBoundingClientRect().top + scrollY - saved.offset
            : saved.y;
        anchor?.focus({ preventScroll: true });
        scrollTo({ top: Math.max(0, y), behavior: "instant" });
      });
      return () => cancelAnimationFrame(frame);
    } catch {
      /* A missing/invalid saved position is non-blocking. */
    }
  }, [context, count, location.state, navigation]);
}
