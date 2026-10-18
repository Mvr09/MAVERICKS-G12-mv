from copy import deepcopy
import json
import pytest
from jsonschema import validate
from scripts.review_scenarios import cases
from app import review_policy, review_support
from app.schemas import NormalizedAnalysis
from tests.helpers import answer


def verified(c, level=.95, cite=True):
    p=review_support.payload(c['prediction'], c['data'], c['suppliers'], 'jev-1.13.0')
    response=answer(p)
    for key,a in response['answers'].items():
        if a['type']=='noul':a['noul']=level
        else:a['choice']='e1' if cite else 'none'
    return review_support.envelope(c['prediction'], response)


def test_urgent_is_certain_with_local_priority_warning_and_audio():
    c=cases('jev-1.13.0')[0];original=deepcopy(c['prediction'])
    r=review_policy.apply(c['prediction'],verified(c));a=r['assessments'][0]
    assert r['analysis_status']=='done' and a['urgent']=='Y'
    assert a['human_attention']=='immediate_contact' and a['priority_requires_review']
    assert 'severity_confidence_low' in a['localized_warnings']
    assert review_policy.alarm_decision(a)['sound_eligible']
    assert c['prediction']==original
    NormalizedAnalysis.model_validate(r)
    validate(r,json.load(open('contracts/article_analysis.schema.json')))


@pytest.mark.parametrize('level,cite',[(.65,True),(.1,True),(.95,False)])
def test_support_and_literal_are_both_required(level,cite):
    c=cases('jev-1.13.0')[0];r=review_policy.apply(c['prediction'],verified(c,level,cite))
    assert r['analysis_status']=='review' and not review_policy.alarm_decision(r['assessments'][0])['sound_eligible']


def test_discarded_scope_uncertainty_and_unknown_cause_are_not_dropped():
    c=cases('jev-1.13.0')[2];p=c['prediction']
    r=review_policy.apply(p,verified(c,.1));assert r['analysis_status']=='review'
    assert r['affected_supplier_ids']==[] and r['assessments'][0]['association_status']=='review'
    c=cases('jev-1.13.0')[0];c['prediction']['review_reasons'].append('future_unknown_blocker')
    assert 'future_unknown_blocker' in review_policy.apply(c['prediction'],verified(c))['review_reasons']


def test_binding_labels_and_source_integrity():
    c=cases('jev-1.13.0')[0];v=verified(c)
    for field in ('Is_Risk','Urgent','Affected_Supplier_IDs','Event_Type','Explanation'):
        c['data'][field]='PROTECTED-SENTINEL'
    assert 'PROTECTED-SENTINEL' not in str(review_support.payload(c['prediction'],c['data'],c['suppliers'],'jev-1.13.0'))
    c['prediction']['assessments'][0]['p_risk']=.1
    with pytest.raises(ValueError):review_policy.apply(c['prediction'],v)
    c['data']['headline']='Changed source'
    with pytest.raises(ValueError):review_support.payload(c['prediction'],c['data'],c['suppliers'],'jev-1.13.0')


def test_other_supplier_uncertainty_does_not_veto_supported_urgent_one():
    c=cases('jev-1.13.0')[0];r=review_policy.apply(c['prediction'],verified(c));urgent=r['assessments'][0]
    other=deepcopy(urgent);other.update(supplier_id='QA902',needs_review=True,p_link=.4)
    r['assessments'].append(other);r['analysis_status']='review'
    assert review_policy.alarm_decision(urgent)['sound_eligible']
    assert not review_policy.alarm_decision(other)['sound_eligible']
    for state in ('monitoring','resolved','unclear'):
        assert not review_policy.alarm_decision({**urgent,'impact_status':state})['sound_eligible']
