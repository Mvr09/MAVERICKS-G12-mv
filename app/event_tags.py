"""Public descriptive metadata only; no decisions, evidence or evaluation labels."""


def event_tag(result):
    if not result:
        return None
    return {
        k: result[k]
        for k in (
            "event_type", "event_classification", "analysis_status",
            "context_notes", "review_reasons",
        )
        if k in result
    }
