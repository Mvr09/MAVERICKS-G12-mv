from types import SimpleNamespace
from tests.helpers import answer
from tests.unit.test_support_contract import SUPPLIER
from app import link_assisted as candidate,link_candidate as base
from reference.scoring import decisions

def test_only_logistics_adds_scope_original_questions_and_risk_only_stays_separate():
    data={'headline':'Ocean services delayed','summary':'Rail unaffected.','Urgent':'HIDDEN-LABEL'}
    assert candidate.stage_a(data,[SUPPLIER],'MOCK')==base.stage_a(data,[SUPPLIER],'MOCK')
    assert candidate.stage_b(data,[SUPPLIER],[],'MOCK')==base.stage_b(data,[SUPPLIER],[],'MOCK')
    s=dict(SUPPLIER,category='Logistics',inventory_days=None,material='Asia to Europe sea freight');sid=s['supplier_id']
    old=base.stage_b(data,[s],[],'MOCK');new=candidate.stage_b(data,[s],[],'MOCK')
    assert all(new['questions'][key]==q for key,q in old['questions'].items())
    assert set(new['questions'])-set(old['questions'])=={'service_scope_'+sid}
    assert 'HIDDEN-LABEL' not in str(new)
    a=answer(candidate.stage_a(data,[s],'MOCK'));b=answer(new,risk=.9,urgent=.95)
    for field,value in {'identity':.05,'area':.1,'operation':.9,'service_scope':.9,'inclusion_support':.9,'risk_support':.9}.items():b['answers'][field+'_'+sid]['noul']=value
    result=candidate.normalize(SimpleNamespace(id='MOCK',news_id='MOCK',context='exercise',data=data),[s],a,b,[])
    assert result['affected_supplier_ids']==[sid] and result['is_risk']=='Y' and result['analysis_status']=='review'
    x=result['assessments'][0];assert x['needs_review'] and not decisions(p_link=x['p_link'],p_risk=x['p_risk'],p_urgent=x['p_urgent'],impact_status=x['impact_status'],needs_review=x['needs_review'])['sound_eligible']
    # Normalization must preserve the actual provider response for diagnosis.
    assert b['answers']['area_'+sid]['noul']==.1
    b['answers']['service_scope_'+sid]['noul']=.1
    unrelated=candidate.normalize(SimpleNamespace(id='MOCK',news_id='MOCK',context='exercise',data=data),[s],a,b,[])
    assert unrelated['affected_supplier_ids']==[]
