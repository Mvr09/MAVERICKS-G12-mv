"""Bounded development, 30 training + 8 synthetics only. No held-out evaluation.
Stored baseline uses same duration parser. Exact cache reuse, persistent counters.
"""
import argparse, hashlib, json, time
from sqlalchemy import select, func
from sqlalchemy.engine import make_url
from app.settings import ROOT, settings
from app.db import Session, engine
from app.models import Supplier, Article, Batch, Grant, GrantArticle, ConsumptionBudget, ApiCall, RequestCache
from app.importer import digest
from app.jev import JevClient, ProviderError, validate_response
from app import link_assisted as candidate
from app.duration import durations
from app.schemas import NormalizedAnalysis
from app.evaluation import metrics

BUDGET='link-4-development-20261018'
REPORT=ROOT/'reports/private/link-3-1-development.json'
FILES=['app/link_assisted.py','app/link_compact_candidate.py','app/link_service_candidate.py','app/link_candidate.py','app/link_questions.py','app/link_analysis.py','app/duration.py','app/geography.py','config/geography.json','config/risk_policy.json','reference/jev_requests.py','reference/scoring.py']

def report_metrics(rows):
    pairs=[(r['reference'],r['prediction']) for r in rows if r.get('reference')]
    automatic=[p for p in pairs if p[1]['analysis_status']=='done']
    def exact(p):
        y,r=p
        return y['Is_Risk']==r['is_risk'] and y['Urgent']==r['urgent'] and {s.strip() for s in (y.get('Affected_Supplier_IDs') or '').split(';') if s.strip()}==set(r['affected_supplier_ids'])
    return {**metrics(pairs),'includes_review_predictions':True,'automatic_coverage':len(automatic)/len(pairs) if pairs else None,
            'automatic':metrics(automatic) if automatic else None,'automatic_joint_errors':sum(not exact(p) for p in automatic),
            'automatic_joint_error_rate':sum(not exact(p) for p in automatic)/len(automatic) if automatic else None}

def save(r): REPORT.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');args=p.parse_args()
    baseline=json.loads((ROOT/'reports/private/stable-geography-results.json').read_text())
    cases=[v for k,v in baseline['results'].items() if k.endswith(':1.0.0') and v['group'] in ('training','synthetic')]
    assert len(cases)==36 and sum(c['group']=='training' for c in cases)==30
    for name,headline,summary,sid in [
        ('sea_route_only','Asia-Europe ocean container services diverted','Ocean container services between Asia and Europe are diverted around Africa, adding fourteen days to delivery. Rail services continue normally.','S032'),
        ('rail_route_only','Asia-Europe rail corridor suspended','Asia to Europe rail freight services are suspended for three days after track damage. Ocean container services continue normally.','S033')]:
        cases.append({'group':'synthetic','case':name,'reference':None,'expected':{'name':name,'suppliers':[sid],'risk':'Y','urgent':None},'synthetic_data':{'news_id':'SYN-SERVICE-'+name,'headline':headline,'summary':summary,'source':'SINTÉTICO · QA servicio','published_date':'2026-10-18T00:00:00+00:00','language':'en','context_id':'exercise'}})
    hashes={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
    freeze=ROOT/'reports/link-3-1-freeze.json'
    protocol={'version':candidate.VERSION,'files':hashes,'training':30,'synthetic':8,'maximum_requests':228,
      'hypothesis':'3.0 unchanged A/risk/urgency/support; add logistics-only declared service OR site exposure; require supervised confirmation for positive risks.',
      'promotion_guards':['Compare missing High/single-source separately; no new automatic risky false associations/urgencies','Route/mode controls and ambiguous geography must remain honest','Balance restored corridor, relevant FN, false links and review workload against2.2 and3.0; no promotion on F1 alone','Automatic positive risk support must be demonstrated before automation promotion; retrospective development evidence is not independent held-out accuracy'],
      'held_out':'validation retrospective, LiveDay already used, remaining test untouched; no holdout in this run'}
    if freeze.exists(): assert json.loads(freeze.read_text())==protocol,'Frozen candidate changed'
    else: freeze.write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n')
    if not args.execute: print(json.dumps({'prepared':True,'cases':38,'max_requests':228}));return
    assert make_url(str(engine.url)).database=='radar_link_development'
    settings.jev_budget_limits_enabled=True
    r=json.loads(REPORT.read_text()) if REPORT.exists() else {'files':hashes,'results':{},'errors':[],'maximum_requests':228}
    assert r['files']==hashes
    with Session() as db:
        suppliers=[s.data for s in db.scalars(select(Supplier).order_by(Supplier.id))];assert len(suppliers)==40
        assert r.get('catalog_hash',digest(suppliers))==digest(suppliers);r['catalog_hash']=digest(suppliers)
        r.setdefault('global_calls_before',db.scalar(select(func.count()).select_from(ApiCall)))
        if not db.get(ConsumptionBudget,BUDGET): db.add(ConsumptionBudget(id=BUDGET,request_limit=228))
        if not db.get(Grant,BUDGET+':narrow'): db.add(Grant(id=BUDGET+':narrow',split='training',article_limit=38,used=0,budget_id=BUDGET))
        bh=digest(protocol);batch=db.scalar(select(Batch).where(Batch.file_hash==bh))
        if not batch: batch=Batch(file_hash=bh,filename='QA_LINK4_COMPACT_TRAINING_SYNTHETIC',split='training',count=38);db.add(batch);db.flush()
        for i,c in enumerate(cases):
            key=c['group']+':'+c['case'];origin=BUDGET+':narrow:'+key;article=db.scalar(select(Article).where(Article.origin_key==origin))
            if not article:
                source=db.get(Article,c['prediction']['article_id']) if 'prediction' in c else None
                data=c.get('synthetic_data') or source.data
                article=Article(origin_key=origin,batch_id=batch.id,context='exercise',row_order=i,news_id=data['news_id'],data=data,content_hash=digest(data));db.add(article);db.flush()
                db.add(GrantArticle(article_id=article.id,grant_id=BUDGET+':narrow'));db.get(Grant,BUDGET+':narrow').used+=1
            c['candidate_article_id']=article.id
        db.commit();save(r)
        try:
            for c in cases:
                key=c['group']+':'+c['case']
                if key in r['results']: continue
                art=db.get(Article,c['candidate_article_id']);deadline=time.monotonic()+60
                client=JevClient(db,art.id,run_key=BUDGET+':'+candidate.VERSION)
                reused=[]
                def ask(payload,stage):
                    old_key=digest({'request':digest({'payload':payload,'questions':'1.0.0'}),'run_key':'link-3-development-20261018:link-3.0.0-dev'})
                    cached=db.get(RequestCache,old_key)
                    if cached:reused.append(stage);return validate_response(payload,cached.response)
                    return client.ask(payload,stage,deadline)
                a=ask(candidate.stage_a(art.data,suppliers,settings.jev_model),'a')
                selected=candidate.select_candidates(art.data,suppliers,a);ds=durations(art.data)
                b=ask(candidate.stage_b(art.data,selected,ds,settings.jev_model),'b') if selected else None
                result=candidate.normalize(art,suppliers,a,b,ds);NormalizedAnalysis.model_validate(result)
                r['results'][key]={'group':c['group'],'case':c['case'],'reference':c.get('reference'),'expected':c.get('expected'),'prediction':result,'baseline':c.get('prediction'),'raw_a':a,'raw_b':b,'cached_stages':reused+client.cached_stages,'new_requests':client.network_requests}
                save(r);print(json.dumps({'completed':len(r['results']),'total':38,'new_requests':client.network_requests}),flush=True)
            r['complete']=True
        except ProviderError as e:
            r['errors'].append({'code':e.code});print(json.dumps({'stopped':e.code}),flush=True);raise
        finally:
            calls=db.scalars(select(ApiCall).where(ApiCall.budget_id==BUDGET)).all()
            r['previous_protocol_requests']=sum(c.run_key!=BUDGET+':'+candidate.VERSION for c in calls)
            r['requests_this_profile']=sum(c.run_key==BUDGET+':'+candidate.VERSION for c in calls)
            r['requests']=len(calls);r['reserved_requests']=db.get(ConsumptionBudget,BUDGET).requests_used
            r['global_calls_after']=db.scalar(select(func.count()).select_from(ApiCall))
            r['calls']=[{'stage':c.stage,'attempt':c.attempt,'seconds':c.duration,'model':c.model,'status':c.status,'usage':c.usage} for c in calls]
            rows=[v for v in r['results'].values() if v['group']=='training']
            r['metrics']={'baseline':report_metrics([{**v,'prediction':v['baseline']} for v in rows]),'candidate':report_metrics(rows)}
            save(r);assert r['requests']<=228 and r['reserved_requests']<=228
    print(json.dumps({'complete':r.get('complete',False),'requests':r['requests'],'metrics':r['metrics']}),flush=True)
if __name__=='__main__': main()
