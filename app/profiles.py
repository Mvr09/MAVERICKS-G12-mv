"""Versioned execution profiles; final promotion retains historical identifiers."""
import json
from pathlib import Path
FINAL_COMPONENTS = json.loads((Path(__file__).resolve().parents[1]/"config/final_profile.json").read_text())["components"]
LEGACY_PROFILE = "1.0.0"
GEOGRAPHY_PROFILE = "geo-1.0.1"
EXPERIMENTAL_PROFILE = "link-2.2.0"
CANDIDATE_PROFILE = "radar-1.0.0-candidate"
DEFAULT_PROFILE = CANDIDATE_PROFILE  # Product promotion authorized; frozen campaign 6c4ca3ce.
EXERCISE_PROFILES = (LEGACY_PROFILE, GEOGRAPHY_PROFILE, EXPERIMENTAL_PROFILE, CANDIDATE_PROFILE)
PUBLIC_EXERCISE_PROFILES = (LEGACY_PROFILE, EXPERIMENTAL_PROFILE, CANDIDATE_PROFILE)  # Geography candidate failed development checks.


def maximum_requests(profile):
    """Four conditional stages for the candidate, two for the stable paths."""
    if profile == CANDIDATE_PROFILE:
        from app.jev_transport import CONFIG
        return CONFIG["max_http_attempts_per_article"]
    return 6


def candidate_versions():
    from app.candidate_engine import VERSIONS
    from app.jev_transport import VERSION
    return {**VERSIONS, "transport": VERSION}


def profile_snapshot(profile, context="exercise"):
    from app.settings import POLICY, settings
    from app.duration import VERSION
    if profile == CANDIDATE_PROFILE:
        result = {**candidate_versions(), "policy": POLICY["version"], "model": settings.jev_model}
        if result != FINAL_COMPONENTS:
            raise ValueError("El perfil actual no coincide con los componentes evaluados; revisa la configuración.")
        return result
    return {"profile": profile, "questions": __import__("app.rss_questions",fromlist=["VERSION"]).VERSION if context == "rss" else profile,
            "duration": VERSION, "policy": POLICY["version"], "model": settings.jev_model}
