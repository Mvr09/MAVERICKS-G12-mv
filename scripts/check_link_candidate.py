"""Bounded development, 30 training + 6 synthetics only. No held-out evaluation.
Stored baseline uses same duration parser. Exact cache reuse, persistent counters.
"""
import argparse, hashlib, json, time
from sqlalchemy import select, func
from sqlalchemy.engine import make_url
from app.settings import ROOT, settings
from app.db import Session, engine
from app.models import Supplier, Article, Batch, Grant, GrantArticle, ConsumptionBudget, ApiCall
from app.importer import digest
from app.jev import JevClient, ProviderError
from app import link_candidate as candidate
from app.duration import durations
from app.schemas import NormalizedAnalysis
from app.evaluation import metrics

BUDGET='link-3-development-20261018'
REPORT=ROOT/'reports/private/link-3-development.json'
FILES=['app/link_candidate.py','app/link_questions.py','app/link_analysis.py','app/duration.py','app/geography.py','config/geography.json','config/risk_policy.json','reference/jev_requests.py','reference/scoring.py']

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
    hashes={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
    freeze=ROOT/'reports/link-3-freeze.json'
    protocol={'version':candidate.VERSION,'files':hashes,'training':30,'synthetic':6,'maximum_requests':216,
      'hypothesis':'Broad retrieval + independent final scope + separate positive/exclusion support, original risk/urgency.',
      'promotion_guards':['supplier TP increases and FN falls','no added supplier FP','no additional risk FN or urgent FP/FN','synthetic regional multi-location preserved; partial disruption nonurgent; ambiguity reviewed; harmless geography excluded with support','automatic errors do not rise; review reduction alone not success'],
      'held_out':'validation retrospective, LiveDay already used, remaining test untouched; no holdout in this run'}
    if freeze.exists(): assert json.loads(freeze.read_text())==protocol,'Frozen candidate changed'
    else: freeze.write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n')
    if not args.execute: print(json.dumps({'prepared':True,'cases':36,'max_requests':216}));return
    assert make_url(str(engine.url)).database=='radar_link_development'
    settings.jev_budget_limits_enabled=True
    r=json.loads(REPORT.read_text()) if REPORT.exists() else {'files':hashes,'results':{},'errors':[],'maximum_requests':216}
    assert r['files']==hashes
    with Session() as db:
        suppliers=[s.data for s in db.scalars(select(Supplier).order_by(Supplier.id))];assert len(suppliers)==40
        assert r.get('catalog_hash',digest(suppliers))==digest(suppliers);r['catalog_hash']=digest(suppliers)
        r.setdefault('global_calls_before',db.scalar(select(func.count()).select_from(ApiCall)))
        if not db.get(ConsumptionBudget,BUDGET): db.add(ConsumptionBudget(id=BUDGET,request_limit=216))
        if not db.get(Grant,BUDGET): db.add(Grant(id=BUDGET,split='training',article_limit=36,used=0,budget_id=BUDGET))
        bh=digest(protocol);batch=db.scalar(select(Batch).where(Batch.file_hash==bh))
        if not batch: batch=Batch(file_hash=bh,filename='QA_LINK3_TRAINING_SYNTHETIC',split='training',count=36);db.add(batch);db.flush()
        for i,c in enumerate(cases):
            key=c['group']+':'+c['case'];origin=BUDGET+':'+key;article=db.scalar(select(Article).where(Article.origin_key==origin))
            if not article:
                source=db.get(Article,c['prediction']['article_id']);assert source is not None
                article=Article(origin_key=origin,batch_id=batch.id,context='exercise',row_order=i,news_id=source.news_id,data=source.data,content_hash=source.content_hash);db.add(article);db.flush()
                db.add(GrantArticle(article_id=article.id,grant_id=BUDGET));db.get(Grant,BUDGET).used+=1
            c['candidate_article_id']=article.id
        db.commit();save(r)
        try:
            for c in cases:
                key=c['group']+':'+c['case']
                if key in r['results']: continue
                art=db.get(Article,c['candidate_article_id']);deadline=time.monotonic()+60
                client=JevClient(db,art.id,run_key=BUDGET+':'+candidate.VERSION)
                a=client.ask(candidate.stage_a(art.data,suppliers,settings.jev_model),'a',deadline)
                selected=candidate.select_candidates(art.data,suppliers,a);ds=durations(art.data)
                b=client.ask(candidate.stage_b(art.data,selected,ds,settings.jev_model),'b',deadline) if selected else None
                result=candidate.normalize(art,suppliers,a,b,ds);NormalizedAnalysis.model_validate(result)
                r['results'][key]={'group':c['group'],'case':c['case'],'reference':c.get('reference'),'expected':c.get('expected'),'prediction':result,'baseline':c['prediction'],'raw_a':a,'raw_b':b,'cached_stages':client.cached_stages,'new_requests':client.network_requests}
                save(r);print(json.dumps({'completed':len(r['results']),'total':36,'new_requests':client.network_requests}),flush=True)
            r['complete']=True
        except ProviderError as e:
            r['errors'].append({'code':e.code});print(json.dumps({'stopped':e.code}),flush=True);raise
        finally:
            calls=db.scalars(select(ApiCall).where(ApiCall.budget_id==BUDGET)).all()
            r['requests']=len(calls);r['reserved_requests']=db.get(ConsumptionBudget,BUDGET).requests_used
            r['global_calls_after']=db.scalar(select(func.count()).select_from(ApiCall))
            r['calls']=[{'stage':c.stage,'attempt':c.attempt,'seconds':c.duration,'model':c.model,'status':c.status,'usage':c.usage} for c in calls]
            rows=[v for v in r['results'].values() if v['group']=='training']
            r['metrics']={'baseline':report_metrics([{**v,'prediction':v['baseline']} for v in rows]),'candidate':report_metrics(rows)}
            save(r);assert r['requests']<=216 and r['reserved_requests']<=216
    print(json.dumps({'complete':r.get('complete',False),'requests':r['requests'],'metrics':r['metrics']}),flush=True)
if __name__=='__main__': main()
