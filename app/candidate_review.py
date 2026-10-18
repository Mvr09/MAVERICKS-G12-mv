"""Principal candidate review policy, based on frozen review1.1.

Model checks are consistency checks against one source, never independent
corroboration. Risk/urgency/matching/priority probabilities remain untouched.
"""
from copy import deepcopy
from app.settings import POLICY
from app.review_policy import binding, VERIFIER_VERSION
from app.review_facts import QUESTIONS as FACTS_VERSION

VERSION = 'review-1.2.0'
EXCLUSION_VERSION = 'relational-exclusion-1.0.0'


def exclusion_payload(result, article, suppliers, model):
    from app.review_support import payload
    p = payload(result, article, suppliers, model)
    p['questions'] = {}
    p['state']['protocol'] = EXCLUSION_VERSION
    spans = {e['id']: e['text'] for e in result['evidence']}
    spans['none'] = 'No source passage justifies this relationship.'
    t = POLICY['thresholds']
    doubtful = {d['supplier_id'] for d in result['review_details']
                if d['code'] == 'association_support_insufficient' and d['requires_review']}
    for a in result['assessments']:
        sid = a['supplier_id']
        if sid not in doubtful or a['p_link'] >= t['review_low'] or a.get('p_identity') is None or a['p_identity'] >= t['review_low']:
            continue
        prefix = f'For {sid}, using source and this supplier catalog only: '
        question = ('Does the article describe a different actual subject/activity than the supplier products or services, '
            'so any overlap is only a place or broad sector name? A conference, passenger statistic or legislative debate '
            'is not an actual production/transport restriction. This is RELATIVE to this supplier; the article may discuss '
            'normal operations of another activity. An unknown route/site during a compatible disruption is UNKNOWN, '
            'not unrelated. A named actual supplier remains identified even in positive news. '
            'Do not infer unrelatedness merely from low inclusion confidence or absence of the company name.')
        p['questions']['unrelated_subject_'+sid] = {'type':'noul', 'instructions':prefix+question}
        p['questions']['relationship_'+sid] = {'type':'choice', 'instructions':prefix+'Identify the factual relationship; do not answer risk or urgency.', 'criteria':{
            'identity':'The actual supplier organisation is identified, including positive news.',
            'potential_scope':'The actual affected area/activity or declared service includes this supplier; potential, not confirmed individual damage.',
            'different_subject':'The actual subject/activity differs; only a harmless place/sector mention overlaps.',
            'unknown_scope':'Essential location, route, activity or source context is missing. Unknown is not exclusion.'}}
        p['questions']['relationship_passage_'+sid] = {'type':'choice', 'criteria':spans, 'instructions':prefix+question+' Select a literal passage or none. A quote alone does not establish exclusion.'}
    return p


def hint(code, field):
    if code == 'geography_requires_review':
        return 'Confirma la provincia de la ubicación del proveedor; no se han supuesto otras plantas.'
    if 'association' in code or 'link_' in code or field == 'final_link':
        return 'Confirma que la ubicación, actividad o ruta declarada del proveedor estén dentro del alcance de la noticia.'
    if field == 'risk_evidence' or 'risk_' in code:
        return 'Aclara qué operación, material o entrega amenaza el hecho. Una cita o el inventario disponible no resuelven por sí solos el riesgo.'
    if field == 'urgent' or 'urgency' in code:
        return 'Confirma el estado actual y el plazo del impacto que harían necesaria coordinación inmediata.'
    if field == 'impact_state':
        return 'Confirma si el impacto sigue activo, es preventivo o ya se ha recuperado.'
    if 'inventory' in code:
        return 'Falta inventario físico verificable; no es cero y la prioridad es una estimación.'
    if field in ('severity', 'duration', 'catalog_or_buffer'):
        return 'Completa el dato indicado para afinar la prioridad. No se ha inventado capacidad ni cobertura.'
    return 'Contrasta el campo indicado con la fuente y los datos disponibles del proveedor.'


def apply(result, support=None, facts=None, exclusions=None):
    out = deepcopy(result)
    if out['analysis_status'] == 'error':
        return out
    t = POLICY['thresholds']
    for envelope, version in ((support, VERIFIER_VERSION), (facts, FACTS_VERSION), (exclusions, EXCLUSION_VERSION)):
        if envelope and (envelope['binding'] != binding(result) or envelope['version'] != version):
            raise ValueError('Consistency check belongs to another analysis/version')
    aa = support['response']['answers'] if support else {}
    ff = facts['response']['answers'] if facts else {}
    ee = exclusions['response']['answers'] if exclusions else {}
    evidence = {e['id'] for e in result['evidence'] if e['text'].strip()}
    def supported(answers, score, passage):
        return answers.get(score, {}).get('noul', 0) > t['review_high'] and answers.get(passage, {}).get('choice') in evidence
    details = out['review_details']
    represented = {d['code']+(':'+d['supplier_id'] if d['supplier_id'] else '') for d in details}
    for reason in set(out['review_reasons']) - represented:
        code, _, sid = reason.partition(':')
        details.append({'code':code,'field':'unclassified','supplier_id':sid or None,'relevance':'risk','requires_review':True,'value':None,'threshold':None})
    topic = ff.get('subject_kind', {})
    nonop = topic.get('choice') == 'non_operational' and topic.get('confidence', 0) >= t['choice_score_confidence'] and supported(ff, 'non_operational', 'non_operational_passage')
    for a in out['assessments']:
        sid = a['supplier_id']
        own_codes = {d['code'] for d in details if d['supplier_id'] == sid}
        for code in set(a['review_reasons']) - own_codes:
            details.append({'code':code,'field':'unclassified','supplier_id':sid,'relevance':'risk','requires_review':True,'value':None,'threshold':None})
        if support and a['is_risk'] == 'Y' and not supported(aa, 'urgency_support_'+sid, 'urgency_passage_'+sid):
            details.append({'code':'urgency_support_insufficient','field':'urgent','supplier_id':sid,'relevance':'urgency','requires_review':True,'value':aa.get('urgency_support_'+sid,{}).get('noul'),'threshold':t['review_high']})
        relationship = ee.get('relationship_'+sid, {})
        unrelated = (relationship.get('choice') == 'different_subject' and relationship.get('confidence', 0) >= t['choice_score_confidence']
                     and supported(ee, 'unrelated_subject_'+sid, 'relationship_passage_'+sid))
        excluded_certainly = a['p_link'] < t['review_low'] and a.get('p_identity') is not None and a['p_identity'] < t['review_low']
        for d in details:
            if d['supplier_id'] not in (None, sid):
                continue
            d.setdefault('original_requires_review', d['requires_review'])
            if d['relevance'] == 'priority':
                d['requires_review'] = False
            if d['supplier_id'] != sid:
                continue
            resolved = None
            if d['code'] == 'association_support_insufficient':
                if supported(aa, 'link_support_'+sid, 'link_passage_'+sid):resolved = 'model_consistency_check'
                elif excluded_certainly and nonop:resolved = 'factual_basis_check'
                elif excluded_certainly and unrelated:resolved = 'relational_scope_check'
            elif d['code'] == 'risk_evidence_insufficient' and supported(aa, 'risk_support_'+sid, 'risk_passage_'+sid):resolved = 'model_consistency_check'
            elif d['code'] == 'urgency_support_insufficient' and supported(ff, 'urgency_basis_'+sid, 'urgency_basis_'+sid+'_passage'):resolved = 'factual_basis_check'
            if resolved:
                d['requires_review'] = False;d['resolution'] = resolved
            d['resolution_hint'] = hint(d['code'], d['field'])
    refresh(out)
    out['review_policy_version'] = VERSION
    out['verification_question_version'] = EXCLUSION_VERSION if exclusions else FACTS_VERSION if facts else VERIFIER_VERSION if support else None
    return out


def refresh(out):
    t = POLICY['thresholds']
    for a in out['assessments']:
        own = [d for d in out['review_details'] if d['supplier_id'] == a['supplier_id']]
        # Unknown global blockers remain decisive; known coverage concerns can
        # coexist with a separately supported supplier without suppressing it.
        global_doubts = [d for d in out['review_details'] if d['supplier_id'] is None and d['field'] == 'unclassified' and d['requires_review']]
        a['needs_review'] = any(d['requires_review'] for d in own + global_doubts)
        a['review_reasons'] = sorted({d['code'] for d in own + global_doubts if d['requires_review']})
        a['priority_requires_review'] = any(d['relevance'] == 'priority' for d in own)
        a['localized_warnings'] = sorted({d['code'] for d in own if not d['requires_review'] and not d.get('resolution')})
        ar = any(d['requires_review'] and d['relevance'] == 'association' for d in own)
        a['association_status'] = 'review' if ar else 'confirmed' if a['p_link'] >= t['link'] else 'excluded'
        a['human_attention'] = 'verify_decision' if a['needs_review'] else 'immediate_contact' if a['urgent'] == 'Y' else 'priority_follow_up' if a['priority_band'] == 'critical' else 'regular_follow_up' if a['is_risk'] == 'Y' else 'none'
        a['review_policy_version'] = VERSION
    out['review_reasons'] = sorted({d['code']+(':'+d['supplier_id'] if d['supplier_id'] else '') for d in out['review_details'] if d['requires_review']})
    out['analysis_status'] = 'review' if out['review_reasons'] else 'done'
    out['context_notes'] = sorted(set(out.get('context_notes', []) + [d['code']+(':'+d['supplier_id'] if d['supplier_id'] else '') for d in out['review_details'] if not d['requires_review'] and not d.get('resolution')]))
