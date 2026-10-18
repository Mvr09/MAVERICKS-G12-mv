"""Literal duration candidates only; JEV must still select the relevant event."""
import re

VERSION = "duration-1.1.0"
_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4,
    "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
    "diez": 10, "once": 11, "doce": 12,
}
_PATTERN = re.compile(
    r"(?<![\w.,+−-])(?:(?P<lower>at least|more than|al menos|más de)\s+)?"
    r"(?P<number>\d+(?:\.\d+)?|" + "|".join(sorted(_WORDS, key=len, reverse=True)) + r")"
    r"\s*(?P<unit>days?|weeks?|months?|días?|semanas?|meses?)\b", re.I,
)
# Reject fragments of bounds, ranges, unsupported number phrases and dates.
# Unknown periods remain unknown, rather than being converted into fixed days.
_UNSAFE_BEFORE = re.compile(
    r"(?:\b(?:up to|at most|less than|fewer than|no|not|about|around|roughly|approximately|"
    r"hasta|menos de|aproximadamente|unos|unas|hace|minus|menos|"
    r"between|entre|to|or|and|a|o|y|twenty|thirty|forty|fifty|sixty|"
    r"seventy|eighty|ninety|hundred|thousand|cien|ciento|mil)\s*|[-−–]\s*)$", re.I,
)
_UNSAFE_AFTER = re.compile(r"\s*(?:ago\b|antes\b|después\b|later\b|(?:to|or|a|o)\b|[-–])", re.I)


def durations(article):
    """Keep source spans and lower bounds; do not infer an incident duration.

    Written numbers one..twelve and un..doce are supported. Larger written
    numbers, ranges and indefinite/approximate periods are left unparsed.
    Week/month conversions preserve the existing 7/30-day convention.
    """
    out = []
    for field in ("headline", "summary"):
        source = article.get(field) or ""
        for match in _PATTERN.finditer(source):
            if _UNSAFE_BEFORE.search(source[:match.start()]) or _UNSAFE_AFTER.match(source[match.end():]):
                continue
            token = match["number"].casefold()
            amount = _WORDS[token] if token in _WORDS else float(token)
            unit = match["unit"].casefold()
            days = amount * (7 if unit.startswith(("week", "semana")) else 30 if unit.startswith(("month", "mes")) else 1)
            if days > 0:
                out.append({"id": f"d{len(out) + 1}", "text": match[0],
                    "days": float(days), "lower_bound": bool(match["lower"])})
    return out
