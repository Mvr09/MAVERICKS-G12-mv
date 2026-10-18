"""Explicit, per-tab QA signal. No article, incident, model call or persistent alert."""
import secrets
from reference.scoring import decisions


def sample():
    facts = dict(p_link=.99, p_risk=.99, p_urgent=.99, impact_status='active', needs_review=False)
    gate = decisions(**facts)
    return {'id': -(secrets.randbelow(2**52) + 1), 'revision': 1, 'acknowledged': False,
        'sound_eligible': gate['sound_eligible'], 'qa': True,
        'title': 'QA · Alerta automática controlada', 'delay_seconds': 5,
        'eligibility_fixture': facts,
        'explanation': 'Escenario QA de elegibilidad; no es una noticia ni una clasificación JEV. Solo existe en esta pestaña.'}
