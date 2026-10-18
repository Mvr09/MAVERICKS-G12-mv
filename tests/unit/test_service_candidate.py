from copy import deepcopy
from types import SimpleNamespace
from tests.helpers import answer
from tests.unit.test_support_contract import SUPPLIER
from app import link_service_candidate as c


def test_service_scope_can_link_without_site_and_never_uses_risk_as_link():
    s=dict(SUPPLIER,category='Logistics',inventory_days=None,city='Singapore',material='Asia to Europe sea freight');sid=s['supplier_id']
    data={'headline':'Asia Europe sea freight diverted','summary':'Rail unaffected.','Is_Risk':'HIDDEN-LABEL','Explanation':'HIDDEN-LABEL'}
    pa=c.stage_a(data,[s],'MOCK');pb=c.stage_b(data,[s],[],'MOCK')
    assert 'HIDDEN-LABEL' not in str(pa)+str(pb)
    a=answer(pa);b=answer(pb,risk=.9,urgent=.1)
    for field,v in {'identity':.05,'area':.1,'operation':.8,'service_scope':.9,'inclusion_support':.9,'exclusion_support':.2}.items():b['answers'][field+'_'+sid]['noul']=v
    original=deepcopy(b);art=SimpleNamespace(id='MOCK',news_id='MOCK',context='exercise',data=data)
    result=c.normalize(art,[s],a,b,[])
    assert result['affected_supplier_ids']==[sid] and result['is_risk']=='Y' and result['urgent']=='N'
    assert b==original and result['assessments'][0]['p_exposure']==.9
    b['answers']['service_scope_'+sid]['noul']=.1
    result=c.normalize(art,[s],a,b,[])
    assert result['affected_supplier_ids']==[] and result['is_risk']=='N'


def test_compact_keeps_each_proposition_and_catalog_in_single_state():
    from app import link_compact_candidate as compact
    import json
    ss=[dict(SUPPLIER,supplier_id=f'S{i:03}') for i in range(1,12)]
    old=c.stage_b({'headline':'Sea freight delayed','summary':'Route delays.'},ss,[],'MOCK')
    new=compact.stage_b({'headline':'Sea freight delayed','summary':'Route delays.'},ss,[],'MOCK')
    assert len(new['state']['suppliers'])==11
    for key,q in old['questions'].items():
        if isinstance(q.get('instructions'),dict):assert q['instructions']['question'] in new['questions'][key]['instructions']
    assert len(json.dumps(new))<len(json.dumps(old))*.6
