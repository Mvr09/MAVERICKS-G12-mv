from copy import deepcopy
import pytest
from app import review_facts as c,review_policy
from scripts.review_scenarios import cases
from tests.helpers import answer
from tests.unit.test_review_policy import verified


def facts(case,kind='non_operational',support=.95,cite=True,confidence=.95):
    p=c.payload(case['prediction'],case['data'],case['suppliers'],'jev-1.13.0');r=answer(p)
    for key,a in r['answers'].items():
        if a['type']=='noul':a['noul']=support
        elif key=='subject_kind':a.update(choice=kind,confidence=confidence)
        else:a['choice']='e1' if cite else 'none'
    return {'binding':review_policy.binding(case['prediction']),'version':c.QUESTIONS,'response':r}


def test_non_operational_exclusion_has_independent_factual_support():
    case=cases('jev-1.13.0')[1];old=deepcopy(case['prediction'])
    r=c.apply(old,verified(case,.1),facts(case))
    assert r['analysis_status']=='done' and not r['affected_supplier_ids']
    assert r['assessments'][0]['association_status']=='excluded'
    for args in ({'support':.65},{'cite':False},{'confidence':.59},{'kind':'insufficient_context'},{'kind':'supply_event'}):
        assert c.apply(old,verified(case,.1),facts(case,**args))['analysis_status']=='review'


def test_high_conditional_risk_never_supplies_a_missing_link_or_exclusion():
    case=cases('jev-1.13.0')[2]
    assert c.apply(case['prediction'],verified(case,.1),facts(case,kind='supply_event'))['analysis_status']=='review'
    case['prediction']['assessments'][0]['p_identity']=None
    assert 'subject_kind' not in c.payload(case['prediction'],case['data'],case['suppliers'],'jev-1.13.0')['questions']
    assert c.apply(case['prediction'],verified(case,.1),facts(case))['analysis_status']=='review'


def test_factual_urgent_basis_is_not_literal_advice_and_does_not_clear_ambiguous_probability():
    case=cases('jev-1.13.0')[0];v=verified(case)
    v['response']['answers']['urgency_support_QA901']['noul']=.1
    r=c.apply(case['prediction'],v,facts(case,kind='supply_event'))
    assert r['analysis_status']=='done' and review_policy.alarm_decision(r['assessments'][0])['sound_eligible']
    case=cases('jev-1.13.0')[4]
    r=c.apply(case['prediction'],verified(case),facts(case,kind='supply_event'))
    assert r['analysis_status']=='review' and not review_policy.alarm_decision(r['assessments'][0])['sound_eligible']


def test_missing_inventory_remains_local_review_not_zero_or_audio_veto():
    case=cases('jev-1.13.0')[0];p=case['prediction'];a=p['assessments'][0]
    p['review_details'].append({'code':'inventory_missing','field':'catalog_or_buffer','supplier_id':a['supplier_id'],'relevance':'priority','requires_review':True,'value':None,'threshold':None})
    a['review_reasons'].append('inventory_missing');a['factor_values'].pop('B',None)
    r=c.apply(p,verified(case),facts(case,kind='supply_event'));a=r['assessments'][0]
    assert a['priority_requires_review'] and 'inventory_missing'in a['localized_warnings']
    assert 'B'not in a['factor_values'] and review_policy.alarm_decision(a)['sound_eligible']
