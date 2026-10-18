from copy import deepcopy
from types import SimpleNamespace
from app import candidate_risk as focus, candidate_matching
from tests.unit.test_support_contract import SUPPLIER
from scripts.review_scenarios import cases


def fixture():
 c=cases('jev-1.13.0')[0];base=deepcopy(c['prediction']);a=base['assessments'][0]
 a.update(p_link=.9,p_identity=.9,p_risk=.48,p_urgent=.12,is_risk='N')
 base.update(event_type='leadership_change');base['review_details']=[]
 sid=a['supplier_id'];e=base['evidence'][0]['id']
 def choice(v):return {'type':'choice','choice':v,'confidence':.9}
 answers={'focus_risk_'+sid:{'type':'noul','noul':.9},'focus_support_'+sid:{'type':'noul','noul':.9},'focus_fact_'+sid:choice('strategic_instability'),'focus_scope_'+sid:choice('identified_supplier'),'focus_passage_'+sid:choice(e),'focus_impact_'+sid:choice('monitoring')}
 return c,base,sid,{'model':'jev-1.13.0','answers':answers}


def test_focus_cannot_establish_association_and_whitelist_excludes_gold():
 c,base,sid,r=fixture();article={**c['data'],**{k:'PROTECTED-SENTINEL' for k in ('Is_Risk','Urgent','Affected_Supplier_IDs','Event_Type','Explanation')}}
 p=focus.payload(base,article,c['suppliers'],'jev-1.13.0');assert p['questions'] and 'PROTECTED-SENTINEL' not in str(p)
 for s in p['state']['suppliers']:assert not {'inventory_days','lead_days','criticality','single_source'}&set(s)
 base['review_details']=[{'supplier_id':sid,'requires_review':True,'relevance':'association'}]
 assert focus.eligible(base)==[]
 base['review_details']=[];base['assessments'][0]['p_link']=.6
 assert focus.eligible(base)==[]


def test_projection_uses_actual_risk_not_evidence_probability_and_preserves_raw_other_fields():
 c,base,sid,r=fixture();b={'model':'jev-1.13.0','answers':{'risk_'+sid:{'type':'noul','noul':.48},'urgent_'+sid:{'type':'noul','noul':.12},'identity_'+sid:{'type':'noul','noul':.9}}};before=deepcopy(b)
 out,changes=focus.project(base,b,r)
 assert changes and out['answers']['risk_'+sid]['noul']==.9
 assert b==before and out['answers']['urgent_'+sid]==before['answers']['urgent_'+sid]
 for field,value in [('focus_risk',{'type':'noul','noul':.6}),('focus_scope',{'type':'choice','choice':'unknown','confidence':1}),('focus_fact',{'type':'choice','choice':'positive_or_no_threat','confidence':1}),('focus_passage',{'type':'choice','choice':'none','confidence':1})]:
  bad=deepcopy(r);bad['answers'][field+'_'+sid]=value
  assert focus.project(base,b,bad)==(b,[])
