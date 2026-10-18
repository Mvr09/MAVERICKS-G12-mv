from copy import deepcopy
from types import SimpleNamespace
from app import candidate_matching as c, link_candidate
from tests.helpers import answer
from tests.unit.test_support_contract import SUPPLIER


def test_retrieval_reused_and_joint_scope_not_derived_from_risk_or_separate_marginals():
    s=dict(SUPPLIER,supplier_id='QA901');data={'headline':'Hangzhou factories reduce output','summary':'A regional restriction applies for two days.'}
    assert c.stage_a(data,[s],'MOCK')==link_candidate.stage_a(data,[s],'MOCK')
    pa=c.stage_a(data,[s],'MOCK');pb=c.stage_b(data,[s],[],'MOCK');aa=answer(pa);bb=answer(pb,risk=.95,urgent=.1)
    for field,value in {'identity':.02,'area':.99,'operation':.99,'joint_exposure':.1,'inclusion_support':.9,'exclusion_support':.9}.items():bb['answers'][field+'_QA901']['noul']=value
    bb['answers']['link_evidence_QA901']['choice']='e1'
    original=deepcopy(bb);art=SimpleNamespace(id='MOCK',news_id='MOCK',context='exercise',data=data)
    r=c.normalize(art,[s],aa,bb,[])
    assert r['affected_supplier_ids']==[] and bb==original
    bb['answers']['joint_exposure_QA901']['noul']=.9
    r=c.normalize(art,[s],aa,bb,[])
    assert r['affected_supplier_ids']==['QA901']
    assert r['is_risk']=='Y'


def test_rss_full_text_taxonomy_and_labels_are_separate():
    data={'headline':'Forest fire','summary':'Reported hazard.','full_text':'Vegetation fire blocked a road.',
        'Is_Risk':'FORBIDDEN','Urgent':'FORBIDDEN','Explanation':'FORBIDDEN'}
    pa=c.stage_a(data,[SUPPLIER],'MOCK','rss');pb=c.stage_b(data,[SUPPLIER],[],'MOCK','rss')
    assert pa['state']['article']['full_text']==data['full_text']
    assert 'wildfire'in pa['questions']['event_type']['criteria']
    assert 'FORBIDDEN'not in str(pa)+str(pb)
    assert any(e['field']=='full_text' for e in pb['state']['evidence_spans'])
