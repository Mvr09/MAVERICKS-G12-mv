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
 answers={'focus_current_'+sid:{'type':'noul','noul':.9},'focus_risk_'+sid:{'type':'noul','noul':.9},'focus_support_'+sid:{'type':'noul','noul':.9},'focus_fact_'+sid:choice('strategic_instability'),'focus_scope_'+sid:choice('identified_supplier'),'focus_passage_'+sid:choice(e),'focus_impact_'+sid:choice('monitoring')}
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
 for field,value in [('focus_scope',{'type':'choice','choice':'unknown','confidence':1}),('focus_fact',{'type':'choice','choice':'positive_or_no_threat','confidence':1}),('focus_passage',{'type':'choice','choice':'none','confidence':1})]:
  bad=deepcopy(r);bad['answers'][field+'_'+sid]=value
  assert focus.project(base,b,bad)==(b,[])


def test_current_threat_is_not_recovery_and_nonurgent_action_must_be_supported():
 from app import candidate_review_focus as review
 from app.review_policy import binding,VERIFIER_VERSION
 c,base,sid,r=fixture();a=base['assessments'][0]
 a.update(p_risk=.9,p_urgent=.1,is_risk='Y',urgent='N',impact_status='active',review_reasons=['impact_state_confidence_low'])
 base['review_reasons']=['impact_state_confidence_low:'+sid];base['analysis_status']='review'
 base['review_details']=[{'supplier_id':sid,'code':'impact_state_confidence_low','field':'impact_state','relevance':'risk','requires_review':True,'value':.41,'threshold':.6}]
 passage=base['evidence'][0]['id'];support={'binding':binding(base),'version':VERIFIER_VERSION,'response':{'answers':{'urgency_support_'+sid:{'noul':.9},'urgency_passage_'+sid:{'choice':passage}}}}
 out=review.apply(base,support=support,focus=r,changes=[{'supplier_id':sid}]);assert out['analysis_status']=='done' and out['assessments'][0]['urgent']=='N'
 assert out['review_details'][0]['resolution']=='factual_basis_check'
 from app.schemas import NormalizedAnalysis
 NormalizedAnalysis.model_validate(out)
 assert review.apply(base,focus=r,changes=[{'supplier_id':sid}])['analysis_status']=='review'
 bad=deepcopy(r);bad['answers']['focus_current_'+sid]['noul']=.2
 assert review.apply(base,support=support,focus=bad,changes=[{'supplier_id':sid}])['analysis_status']=='review'



def test_focused_probability_is_not_silently_thresholded_at_review_high():
 c,base,sid,r=fixture();b={'model':'jev-1.13.0','answers':{'risk_'+sid:{'type':'noul','noul':.48},'urgent_'+sid:{'type':'noul','noul':.12}}}
 r['answers']['focus_risk_'+sid]['noul']=.58
 out,changes=focus.project(base,b,r)
 assert out['answers']['risk_'+sid]['noul']==.58 and changes
 # Original policy still flags this probability as ambiguous; neither factual
 # support nor a quote authorises automatic clearance of risk uncertainty.
 from app.settings import POLICY
 assert POLICY['thresholds']['review_low'] <= .58 <= POLICY['thresholds']['review_high']
 r['answers']['focus_risk_'+sid]['noul']=.2
 out,changes=focus.project(base,b,r)
 assert out['answers']['risk_'+sid]['noul']==.2 and changes[0]['fact_prediction_conflict']
 # It is not valid to relabel support for an adverse fact as support for no risk.
 assert 'risk_support_'+sid not in out['answers']


def test_supported_negative_outside_gray_band_is_still_eligible_when_decision_evidence_missing():
 c,base,sid,r=fixture();a=base['assessments'][0];a['p_risk']=.2
 base['review_details']=[{'supplier_id':sid,'code':'risk_evidence_insufficient','requires_review':True,'relevance':'risk'}]
 assert focus.eligible(base)==[sid]
 base['review_details']=[]
 assert focus.eligible(base)==[]
