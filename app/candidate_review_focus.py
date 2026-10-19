"""Localise active-versus-monitoring ambiguity only when action is supported.

No lower probability gates, no new associations, no clearance of source gaps or
possible recovery. Current-threat check is same-source semantic consistency.
"""
from app import candidate_review as previous
from app.settings import POLICY

VERSION='review-1.3.0'


def apply(base,support=None,facts=None,exclusions=None,focus=None,changes=()):
    out=previous.apply(base,support,facts,exclusions);t=POLICY['thresholds']
    if focus:
        aa=focus['answers'];supported=(support or {}).get('response',{}).get('answers',{})
        ff=(facts or {}).get('response',{}).get('answers',{})
        ev={e['id'] for e in out['evidence']};changed={c['supplier_id'] for c in changes}
        for a in out['assessments']:
            sid=a['supplier_id']
            urgency_supported=any(answers.get(score,{}).get('noul',0)>t['review_high'] and answers.get(passage,{}).get('choice') in ev for answers,score,passage in (
                (supported,'urgency_support_'+sid,'urgency_passage_'+sid),(ff,'urgency_basis_'+sid,'urgency_basis_'+sid+'_passage')))
            if not (sid in changed and a['association_status']=='confirmed' and a['p_risk']>t['review_high'] and a['p_urgent']<t['review_low'] and a['impact_status'] in ('active','monitoring') and urgency_supported and aa.get('focus_current_'+sid,{}).get('noul',0)>t['review_high']):continue
            for d in out['review_details']:
                if d['supplier_id']==sid and d['code']=='impact_state_confidence_low':
                    d.update(requires_review=False,resolution='factual_basis_check',resolution_hint='Amenaza actual respaldada y seguimiento no urgente verificado; la distinción activo/seguimiento sigue incierta.')
                    out.setdefault('context_notes',[]).append('impact_state_local_uncertainty:'+sid)
    previous.refresh(out);out['review_policy_version']=VERSION
    for a in out['assessments']:a['review_policy_version']=VERSION
    return out
