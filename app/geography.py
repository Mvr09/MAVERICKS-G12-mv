"""Versioned place enrichment; never asserts additional supplier facilities."""
import json
import re
import unicodedata
from functools import lru_cache
from app.settings import ROOT


@lru_cache(maxsize=1)
def gazetteer():
    return json.loads((ROOT / "config/geography.json").read_text())


def fold(text):
    text = text.casefold().translate(str.maketrans({"ł":"l", "ø":"o", "đ":"d", "æ":"ae", "œ":"oe"}))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def location(supplier):
    data = gazetteer()
    found = data["locations"].get(supplier.get("country", "") + "|" + supplier.get("city", ""))
    return {"version": data["version"], "attribution": data["attribution"],
        "catalog_country": supplier.get("country"), "catalog_city": supplier.get("city"),
        **(found or {"status": "unresolved", "places": []}),
        "limitation": "Place candidates only, not verified company facilities. Multiple cities remain ambiguous; no population-based selection."}


def matches(text, term):
    term = fold(term)
    return bool(term and len(term) >= 4 and re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text))


def retrieval_hints(article, supplier):
    """High recall hints ONLY. Even harmless geography enters independent B."""
    text = fold(article.get("headline", "") + " " + article.get("summary", ""))
    geo = location(supplier)
    hints = []
    for place in geo["places"]:
        if any(matches(text, n) for n in place["aliases"] + [place["name"]]):
            hints.append({"kind": "city", "geoname_id": place["geoname_id"], "source_url": place["source_url"]})
        admin = place.get("admin1")
        if admin and any(matches(text, n) for n in (admin["name"], admin["ascii_name"])):
            hints.append({"kind": "region", "geoname_id": admin["geoname_id"], "source_url": "https://www.geonames.org/" + admin["geoname_id"] + "/"})
    country = geo.get("country", {})
    if matches(text, country.get("name", "")) or matches(text, geo.get("catalog_country", "")):
        hints.append({"kind": "country", "code": country.get("code")})
    name = re.sub(r"\b(ltd|inc|gmbh|ag|as|sl|spa|co)\b", "", fold(supplier["name"]))
    name = " ".join(name.split())
    if len(name.split()) >= 2 and matches(text, name):
        hints.append({"kind": "name", "limitation": "Candidate retrieval, not verified identity"})
    return hints


def payload_location(article, supplier):
    """Compact relevant projection; all alternative places, matched aliases only."""
    geo = location(supplier)
    text = fold(article.get("headline", "") + " " + article.get("summary", ""))
    return {"version": geo["version"], "status": geo["status"], "catalog_city": supplier.get("city"),
        "country": geo.get("country"),
        "places": [{"geoname_id": p["geoname_id"], "name": p["name"], "admin1": p.get("admin1"),
            "matched_aliases": [name for name in p["aliases"] if matches(text, name)], "source_url": p["source_url"]} for p in geo["places"]],
        "limitation": geo["limitation"]}
