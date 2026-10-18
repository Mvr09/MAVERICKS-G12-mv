"""Review1.1: factual event basis, separate from inferred buyer action.
Keeps review1.0 and all frozen predictions reproducible.
"""
from app import review_policy
from app.settings import POLICY

VERSION='review-1.1.0-candidate'
QUESTIONS='decision-facts-1.0.0'


def payload(result, article, suppliers, model):
    from app.review_support import payload as support_payload
    p=support_payload(result,article,suppliers,model)
    p['questions']={};p['state']['protocol']=QUESTIONS
    evidence={e['id']:e['text'] for e in result['evidence']};evidence['none']='No factual passage supports the basis.'
    discarded={a['supplier_id'] for a in result['assessments'] if a['p_link']<POLICY['thresholds']['review_low'] and a.get('p_identity') is not None and a['p_identity']<POLICY['thresholds']['review_low']}
    if any(d['code']=='association_support_insufficient' and d['supplier_id']in discarded for d in result['review_details']):
        p['questions']['subject_kind']={'type':'choice','criteria':{
            'non_operational':'A standalone market/economic indicator, sports, cultural or academic topic, with no concrete supplier operational or strategic development.',
            'positive_company':'A positive company development; company identity must still be preserved.',
            'supply_event':'An operational disruption or strategic supplier development, including ownership/leadership change, financial distress, quality or regulation, even without a stoppage.',
            'insufficient_context':'The available text cannot establish which subject applies; a truncated fragment is not evidence of harmlessness.'},
            'instructions':'Classify the factual subject of state.article. Do not classify individual supplier linkage or infer that missing details are harmless.'}
        add(p,'non_operational', 'Do the available source facts positively establish a clearly non-operational subject such as a standalone macroeconomic statistic, sports, cultural or academic topic? Missing text or lack of a named supplier alone is insufficient. Operational/strategic supplier developments are not non-operational.', evidence)
    for a in result['assessments']:
        if a['is_risk']!='Y':continue
        sid=a['supplier_id'];positive=a['urgent']=='Y'
        proposition=('Does the source factually report an active or impending serious unplanned interruption of the separately associated activity: production or shipments halted, forced evacuation, production prohibition, recall, or prolonged power loss? Evaluate these source facts, not whether the author explicitly tells a buyer to act. A compatible affected class is potential exposure, not confirmed individual damage. Missing essential operational scope is insufficient.' if positive else
            'Does the source factually describe only a limited short disruption with preserved operations, or a slow strategic threat without an active serious stoppage, evacuation, prohibition or recall? This asks the factual basis for regular follow-up, not whether the text literally instructs a buyer. Inventory or missing stockout evidence alone is insufficient.')
        add(p,'urgency_basis_'+sid,'For '+sid+' using its explicit catalog and separately assessed exposure: '+proposition,evidence)
    return p


def add(p,key,proposition,evidence):
    p['questions'][key]={'type':'noul','instructions':proposition}
    p['questions'][key+'_passage']={'type':'choice','criteria':evidence,'instructions':proposition+' Select the literal factual source passage, or none if insufficient. The quote alone does not confirm exposure.'}


def apply(result, support=None, facts=None):
    out=review_policy.apply(result,support)
    if facts and (facts['binding']!=review_policy.binding(result) or facts['version']!=QUESTIONS):
        raise ValueError('Factual verification belongs to another analysis/version')
    aa=facts['response']['answers'] if facts else {};t=POLICY['thresholds'];valid={e['id'] for e in result['evidence'] if e['text'].strip()}
    def sufficient(key):
        return aa.get(key,{}).get('noul',0)>t['review_high'] and aa.get(key+'_passage',{}).get('choice')in valid
    topic=aa.get('subject_kind',{})
    nonop=topic.get('choice')=='non_operational' and topic.get('confidence',0)>=t['choice_score_confidence'] and sufficient('non_operational')
    for a in out['assessments']:
        sid=a['supplier_id']
        for d in out['review_details']:
            if d['supplier_id']!=sid:continue
            local_exclusion=(d['code']=='association_support_insufficient' and nonop and a['p_link']<t['review_low'] and a.get('p_identity') is not None and a['p_identity']<t['review_low'])
            urgent_basis=d['code']=='urgency_support_insufficient' and sufficient('urgency_basis_'+sid)
            if local_exclusion or urgent_basis:
                d['requires_review']=False;d['resolution']='factual_basis_check'
        own=[d for d in out['review_details'] if d['supplier_id']==sid]
        a['needs_review']=any(d['requires_review'] for d in own)
        a['review_reasons']=sorted({d['code'] for d in own if d['requires_review']})
        a['localized_warnings']=sorted({d['code'] for d in own if not d['requires_review'] and not d.get('resolution')})
        association=any(d['requires_review'] and d['relevance']=='association' for d in own)
        a['association_status']='review' if association else 'confirmed' if a['p_link']>=t['link'] else 'excluded'
        a['human_attention']='verify_decision' if a['needs_review'] else ('immediate_contact' if a['urgent']=='Y' else 'priority_follow_up' if a['priority_band']=='critical' else 'regular_follow_up' if a['is_risk']=='Y' else 'none')
        a['review_policy_version']=VERSION
    out['review_policy_version']=VERSION
    out['verification_question_version']=QUESTIONS if facts else review_policy.VERIFIER_VERSION if support else None
    out['review_reasons']=sorted({d['code']+(':'+d['supplier_id'] if d['supplier_id'] else '') for d in out['review_details'] if d['requires_review']})
    out['analysis_status']='review' if out['review_reasons'] else 'done'
    return out
