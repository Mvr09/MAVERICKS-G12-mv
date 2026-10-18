"""Same4.0 propositions, one shared catalog context instead of per-question copies."""
from app import link_service_candidate as base
VERSION='link-4.0.1-dev'
select_candidates=base.select_candidates

def compact(payload):
    payload['state']['association_protocol']['version']=VERSION
    for key,q in payload['questions'].items():
        value=q.get('instructions')
        if isinstance(value,dict) and 'question' in value:
            sid=key.rsplit('_',1)[-1]
            q['instructions']=f"For supplier {sid} in state.suppliers, using its catalog and geography: "+value['question']
    return payload

def stage_a(article,suppliers,model):return compact(base.stage_a(article,suppliers,model))
def stage_b(article,suppliers,durations,model):return compact(base.stage_b(article,suppliers,durations,model))
def normalize(article,suppliers,a,b,durations):
    result=base.normalize(article,suppliers,a,b,durations)
    result['question_version']=VERSION
    return result
