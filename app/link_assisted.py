"""3.0 retrieval/questions, plus declared logistics service; supervised risks only."""
from copy import deepcopy
from app import link_candidate as base
from app.settings import POLICY
VERSION='link-3.1.0-assist'
stage_a=base.stage_a  # Exact shared retrieval; existing valid responses may be reused.
select_candidates=base.select_candidates

def stage_b(article,suppliers,durations,model):
    payload=base.stage_b(article,suppliers,durations,model)
    # No change at all to a payload without logistics candidates.
    for s in suppliers:
        if s['category']!='Logistics':continue
        sid=s['supplier_id']
        payload['questions']['service_scope_'+sid]={'type':'noul','instructions':f"For {sid} in state.suppliers: does its explicitly catalogued logistics SERVICE match the reported affected route AND transport mode? Use material as declared service scope, not the company's city as the route. Sea freight is not rail freight. An unknown route is not a match. This is potential service exposure, never a confirmed shipment or company damage. Do not use conditional risk as proof of scope."}
    return payload

def normalize(article,suppliers,a,b,durations):
    adapted=deepcopy(b) if b else None
    if adapted:
        bb=adapted['answers']
        for s in suppliers:
            sid=s['supplier_id']
            if 'service_scope_'+sid not in bb:continue
            exposure=max(min(bb['area_'+sid]['noul'],bb['operation_'+sid]['noul']),bb['service_scope_'+sid]['noul'])
            bb['area_'+sid]={'type':'noul','noul':exposure};bb['operation_'+sid]={'type':'noul','noul':1.0}
    result=base.normalize(article,suppliers,a,adapted,durations)
    result['question_version']=VERSION
    for assessment in result['assessments']:
        if assessment['is_risk']!='Y':continue
        assessment['needs_review']=True
        assessment['review_reasons']=sorted(set(assessment['review_reasons']+['assisted_risk_confirmation_required']))
        result['review_reasons']=sorted(set(result['review_reasons']+['assisted_risk_confirmation_required:'+assessment['supplier_id']]))
        result['review_details'].append({'code':'assisted_risk_confirmation_required','field':'supervised_risk','supplier_id':assessment['supplier_id'],'relevance':'risk','requires_review':True,'value':None,'threshold':None})
    if result['review_reasons']:result['analysis_status']='review'
    return result
