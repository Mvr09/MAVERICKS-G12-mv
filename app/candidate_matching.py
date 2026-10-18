"""Single principal matching candidate: joint scope, independent identity/risk.

Retrieval A is deliberately byte-identical to3.0 for exercise cache reuse.
Final exposure B evaluates source scope and catalog jointly, not a minimum of
separate marginals. Raw provider answers are never rewritten or persisted as
if the adapter's projection had been returned by JEV.
"""
from copy import deepcopy
from app import link_candidate as previous, rss_questions
from reference.jev_requests import sentences

VERSION = 'link-3.2.0'
PROFILE = 'radar-1.0.0-candidate'
RETRIEVAL_VERSION = previous.VERSION


def stage_a(article, suppliers, model, context='exercise'):
    p = previous.stage_a(article, suppliers, model)
    if context == 'rss':
        rss_questions.state(p, article)
        # Keep the already tested closed taxonomy and wildfire distinctions.
        old = rss_questions.stage_a(article, suppliers, model)
        p['questions']['event_type'] = old['questions']['event_type']
    return p


def select_candidates(article, suppliers, response):
    data = {**article, 'summary': article.get('summary','')+' '+article.get('full_text','')}
    return previous.select_candidates(data, suppliers, response)


def stage_b(article, suppliers, durations, model, context='exercise'):
    p = previous.stage_b(article, suppliers, durations, model)
    p['state']['association_protocol']['version'] = VERSION
    if context == 'rss':rss_questions.state(p, article)
    spans = rss_questions.sentences(article) if context == 'rss' else sentences(article)
    p['state']['evidence_spans'] = spans
    evidence = {e['id']:e['text'] for e in spans};evidence['none']='No source passage supports the conclusion.'
    for sid in (s['supplier_id'] for s in suppliers):
        q = p['questions']
        q['joint_exposure_'+sid] = {'type':'noul','instructions':(
            f'For supplier {sid} in state.suppliers, does the actual reported event jointly cover its stated '
            'activity AND an explicitly affected catalog location/region or explicitly declared transport service? '
            'Evaluate the whole article and catalog together, independently of retrieval and conditional risk. '
            'A broad regional utility restriction or factory production reduction can potentially expose compatible '
            'manufacturing/material activity without naming each company; this is not confirmed individual damage. '
            'For route-specific transport events require matching declared route AND mode. Company headquarters '
            'are not a shipment route. Unknown routes, plants or ambiguous provinces remain unknown. '
            'A price statistic, conference, ordinary commercial supply agreement or positive expansion does not '
            'by itself establish adverse operational exposure of other suppliers. A recovery may concern a previously '
            'disrupted compatible activity. Identity is assessed separately and can preserve a named positive supplier. '
            'Do not assume a factory process, barge use, Helixa shipment or alternate capacity.')}
        q['risk_'+sid]['instructions'] = (
            f'For {sid}, conditional on separately established identity or operational exposure: does the source '
            'report a credible threat to continued production, deliveries or strategic security of supply? '
            'A partial reduction of production/capacity or slower/blocked transport is risk even when production '
            'continues, inventory covers the delay, and urgency is low. Do not equate risk with stockout. '
            'Financial distress, competitor acquisition and material leadership instability may be strategic '
            'watch-list threats without a shutdown. Positive expansion/approval, harmless geography or market '
            'prices alone are not supply disruption. This conditional risk judgment never establishes a link.')
        q['inclusion_support_'+sid]['instructions'] = (
            f'For {sid}, do source facts plus explicit catalog/geography substantiate actual identity or potential '
            'operational exposure? Identity may link positive news. Regional exposure requires affected catalog '
            'location AND compatible activity; a declared transport service requires an affected route AND matching '
            'mode, not an affected headquarters city. Essential unknown province, route or process is insufficient. '
            'A quotation or high conditional risk alone is not association support.')
        q['risk_support_'+sid]['instructions'] = (
            f'For {sid}, conditional on independently established identity/exposure, are there enough factual source '
            'details to assess whether this reported event is a supply/strategic threat or a genuinely harmless/positive '
            'development? Partial capacity reduction supports a threat without proving a missed individual shipment. '
            'Do not demand damage to a fictional company. Unknown essential operational facts, inventory coverage '
            'or lack of urgency alone do not establish no risk. This asks source support, not association.')
        for prefix in ('evidence','link_evidence'):q[prefix+'_'+sid]['criteria']=evidence
        # Compact representation; supplier and geography are in shared state.
        for key,question in q.items():
            if key.endswith('_'+sid) and isinstance(question.get('instructions'),dict):
                text=question['instructions']['question']
                question['instructions']=f'For {sid}, using its state.suppliers catalog/geography and state.article: '+text
    return p


def normalize(article, suppliers, a, b, durations):
    projected = deepcopy(b) if b else None
    if projected:
        for s in suppliers:
            sid=s['supplier_id'];answers=projected['answers']
            if 'joint_exposure_'+sid not in answers:continue
            # Explicit mathematical projection into the frozen normalizer.
            # It is max(identity, joint exposure), never conditional risk.
            exposure=answers['joint_exposure_'+sid]['noul']
            answers['area_'+sid]={'type':'noul','noul':exposure}
            answers['operation_'+sid]={'type':'noul','noul':1.0}
    result=previous.normalize(article,suppliers,a,projected,durations)
    result['question_version']=VERSION
    result['matching_version']=VERSION
    result['analysis_profile']=PROFILE
    if article.context == 'rss':
        result['evidence']=rss_questions.sentences(article.data)
        category=a['answers']['event_type']['choice']
        result['event_type']=rss_questions.canonical_event(category)
        result['event_classification']={'category':category,'confidence':a['answers']['event_type']['confidence'],
            'taxonomy_version':rss_questions.TAXONOMY_VERSION,'label_es':rss_questions.EVENT_LABELS.get(category,category)}
    return result
