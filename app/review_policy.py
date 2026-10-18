"""Candidate review policy. Classification and business priority are immutable.

Urgent buyer attention is not uncertainty. Priority estimates retain their own
review flag; they do not veto a separately supported urgent decision.
"""
from copy import deepcopy
from app.settings import POLICY
from app.importer import digest
from reference.scoring import decisions

VERSION = 'review-1.0.0-candidate'
VERIFIER_VERSION = 'decision-support-1.0.0'


def binding(result):
    return digest({k: result[k] for k in ('article_id', 'question_version',
        'affected_supplier_ids', 'is_risk', 'urgent', 'assessments', 'evidence')})


def apply(result, verification=None):
    out = deepcopy(result)
    if out['analysis_status'] == 'error':
        return out
    if out['question_version'] != 'link-3.0.0-dev':
        raise ValueError('Review candidate is evaluated only on frozen link-3.0.0-dev')
    if verification and (verification['binding'] != binding(result) or
                         verification['version'] != VERIFIER_VERSION):
        raise ValueError('Support verification belongs to another analysis/version')
    answers = verification['response']['answers'] if verification else {}
    valid_evidence = {e['id'] for e in result['evidence'] if e['text'].strip()}
    t = POLICY['thresholds']
    def supported(field, sid):
        score = answers.get(field + '_support_' + sid, {}).get('noul', 0)
        passage = answers.get(field + '_passage_' + sid, {}).get('choice', 'none')
        return score > t['review_high'] and passage in valid_evidence
    details = out['review_details']
    represented = {d['code'] + (':' + d['supplier_id'] if d['supplier_id'] else '') for d in details}
    # Reconciliation and future engines may add causes outside structured
    # details. Never clear an unknown blocker by reconstructing the list.
    for reason in set(out['review_reasons']) - represented:
        code, _, sid = reason.partition(':')
        details.append({'code': code, 'field': 'unclassified', 'supplier_id': sid or None,
            'relevance': 'risk', 'requires_review': True, 'value': None, 'threshold': None})
    for a in out['assessments']:
        own_codes = {d['code'] for d in details if d['supplier_id'] == a['supplier_id']}
        for code in set(a['review_reasons']) - own_codes:
            details.append({'code': code, 'field': 'unclassified', 'supplier_id': a['supplier_id'],
                'relevance': 'risk', 'requires_review': True, 'value': None, 'threshold': None})
        if verification and a['is_risk'] == 'Y' and not supported('urgency', a['supplier_id']):
            details.append({'code': 'urgency_support_insufficient', 'field': 'urgent',
                'supplier_id': a['supplier_id'], 'relevance': 'urgency', 'requires_review': True,
                'value': answers.get('urgency_support_'+a['supplier_id'],{}).get('noul'),
                'threshold': t['review_high']})
    for d in details:
        d['original_requires_review'] = d['requires_review']
        if d['relevance'] == 'priority':
            # Preserve the uncertainty in the score, including missing physical
            # inventory. Never fill a value or claim that its priority is exact.
            d['requires_review'] = False
        elif d['code'] in ('association_support_insufficient', 'risk_evidence_insufficient'):
            field = 'link' if d['relevance'] == 'association' else 'risk'
            if supported(field, d['supplier_id']):
                d['requires_review'] = False
                d['resolution'] = 'independent_support_check'
    out['review_policy_version'] = VERSION
    out['verification_question_version'] = VERIFIER_VERSION if verification else None
    for a in out['assessments']:
        own = [d for d in details if d['supplier_id'] == a['supplier_id']]
        a['needs_review'] = any(d['requires_review'] for d in own)
        a['review_reasons'] = sorted({d['code'] for d in own if d['requires_review']})
        a['priority_requires_review'] = any(d['relevance'] == 'priority' for d in own)
        a['localized_warnings'] = sorted({d['code'] for d in own if not d['requires_review']
            and d.get('resolution') != 'independent_support_check'})
        association = any(d['requires_review'] and d['relevance'] == 'association' for d in own)
        a['association_status'] = 'review' if association else 'confirmed' if a['p_link'] >= t['link'] else 'excluded'
        # Attention and certainty are separate axes. A reviewed hypothesis can
        # require prompt verification; it is never a confirmed urgent alarm.
        a['human_attention'] = 'verify_decision' if a['needs_review'] else (
            'immediate_contact' if a['urgent'] == 'Y' else
            'priority_follow_up' if a['priority_band'] == 'critical' else
            'regular_follow_up' if a['is_risk'] == 'Y' else 'none')
        a['review_policy_version'] = VERSION
    out['review_reasons'] = sorted({d['code'] + (':' + d['supplier_id'] if d['supplier_id'] else '')
        for d in details if d['requires_review']})
    out['analysis_status'] = 'review' if out['review_reasons'] else 'done'
    out['context_notes'] = sorted(set(out.get('context_notes', []) + [
        d['code'] + (':' + d['supplier_id'] if d['supplier_id'] else '')
        for d in details if not d['requires_review'] and d.get('resolution') != 'independent_support_check']))
    return out


def alarm_decision(assessment):
    """Same calibrated probability/active-state gates; supplier-local doubt only."""
    return decisions(p_link=assessment['p_link'], p_risk=assessment['p_risk'],
        p_urgent=assessment['p_urgent'], impact_status=assessment['impact_status'],
        needs_review=assessment['needs_review'])
