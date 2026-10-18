from types import SimpleNamespace
from copy import deepcopy
from app import link_candidate as c
from reference.jev_requests import stage_b, clean_article
from tests.unit.test_support_contract import SUPPLIER
from tests.helpers import answer

ARTICLE={'headline':'Factories reduce production in Hangzhou for two days.','summary':'Partial regional power restrictions.','Is_Risk':'SECRET_LABEL','Urgent':'SECRET_LABEL'}

def test_original_risk_and_urgency_and_no_label_leakage():
    p=c.stage_b(ARTICLE,[SUPPLIER],[], 'MOCK')
    old=stage_b(ARTICLE,[SUPPLIER],[],'MOCK')
    for field in ('risk','urgent'):
        assert p['questions'][field+'_'+SUPPLIER['supplier_id']]==old['questions'][field+'_'+SUPPLIER['supplier_id']]
    assert 'SECRET_LABEL' not in str(p)
    assert 'exclusion_support_'+SUPPLIER['supplier_id'] in p['questions']
    assert 'association_support_'+SUPPLIER['supplier_id'] not in p['questions']
    assert clean_article(ARTICLE)==p['state']['article']

def test_final_b_can_recover_low_initial_candidate_without_risk_creating_link():
    s=SUPPLIER;sid=s['supplier_id'];aa=answer(c.stage_a(ARTICLE,[s],'MOCK'))
    aa['answers']['candidate_'+sid]['noul']=.1
    b=answer(c.stage_b(ARTICLE,[s],[],'MOCK'),risk=.9,urgent=.1)
    for key,value in {'identity':.01,'area':.9,'operation':.9,'inclusion_support':.9,'exclusion_support':.05}.items():b['answers'][key+'_'+sid]['noul']=value
    art=SimpleNamespace(id='MOCK',news_id='MOCK',context='exercise',data=ARTICLE)
    result=c.normalize(art,[s],aa,b,[])
    assert result['affected_supplier_ids']==[sid] and result['is_risk']=='Y'
    assert result['urgent']=='N'
    b['answers']['operation_'+sid]['noul']=.1
    excluded=c.normalize(art,[s],aa,b,[])
    assert excluded['affected_supplier_ids']==[] and excluded['is_risk']=='N'
    assert excluded['analysis_status']=='review' # Low inclusion is not a supported exclusion.
    b['answers']['exclusion_support_'+sid]['noul']=.9
    supported=c.normalize(art,[s],aa,b,[])
    assert 'association_support_insufficient' not in supported['assessments'][0]['review_reasons']
