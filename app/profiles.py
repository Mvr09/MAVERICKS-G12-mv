"""Explicit versions: geography candidate does not promote the link experiment."""
LEGACY_PROFILE = "1.0.0"
GEOGRAPHY_PROFILE = "geo-1.0.1"
EXPERIMENTAL_PROFILE = "link-2.2.0"
CANDIDATE_PROFILE = "radar-1.0.0-candidate"
DEFAULT_PROFILE = LEGACY_PROFILE  # Retained: the isolated geography candidate regressed.
EXERCISE_PROFILES = (LEGACY_PROFILE, GEOGRAPHY_PROFILE, EXPERIMENTAL_PROFILE, CANDIDATE_PROFILE)
PUBLIC_EXERCISE_PROFILES = (LEGACY_PROFILE, EXPERIMENTAL_PROFILE, CANDIDATE_PROFILE)  # Geography candidate failed development checks.


def maximum_requests(profile):
    """Four conditional stages for the candidate, two for the stable paths."""
    return 12 if profile == CANDIDATE_PROFILE else 6
