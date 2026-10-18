"""Presenter-only request diagnostics: no credentials or evaluation labels."""
from sqlalchemy import select
from app.models import Analysis,ApiCall
from app.jev_transport import encoded_size


def view(db,article,include_payloads=False):
    runs=[]
    for a in db.scalars(select(Analysis).where(Analysis.article_id==article.id).order_by(Analysis.created_at.desc())):
        stages=[]
        for stage,p in a.raw.get('_effective_payloads',{}).items():
            stages.append({'stage':stage,'bytes':encoded_size(p),'state_bytes':encoded_size(p['state']),
                'questions':len(p['questions']),'max_question_bytes':max((encoded_size(q) for q in p['questions'].values()),default=0),
                'max_choice_options':max((len(q.get('criteria',{})) for q in p['questions'].values() if q['type']=='choice'),default=0),
                'payload_hash':a.raw.get('_effective_payload_hashes',{}).get(stage)})
        row={'id':a.id,'generation':a.generation,'created_at':a.created_at,'versions':a.result.get('analysis_versions'),
            'status':a.result['analysis_status'],'error':a.result.get('error'),'seconds':a.duration,'new_requests':a.raw.get('_new_requests'),
            'cached_stages':a.raw.get('_cache_stages',[]),'stages':stages,'transport':a.raw.get('_transport',[])}
        if include_payloads:
            row['effective_payloads']=a.raw.get('_effective_payloads',{})
            row['effective_responses']=a.raw.get('_effective_responses',{})
        runs.append(row)
    calls=[{'id':c.id,'stage':c.stage,'run_key':c.run_key,'attempt':c.attempt,'model':c.model,'status':c.status,'seconds':c.duration,
        'budget_id':c.budget_id,'provider_diagnostic':c.usage.get('_provider_error'),'error':c.usage.get('_error'),
        'diagnosed_at':c.usage.get('_diagnosed_at'),'usage':{k:v for k,v in c.usage.items() if k in ('input_tokens','output_tokens','total_tokens')}}
        for c in db.scalars(select(ApiCall).where(ApiCall.article_id==article.id).order_by(ApiCall.created_at))]
    return {'article_id':article.id,'generation':article.generation,'runs':runs,'calls':calls}
