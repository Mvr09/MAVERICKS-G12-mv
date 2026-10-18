"""Targeted support verification; cached 3.0 predictions never re-requested.

Thirty stored training + six stored synthetic + six controlled policy scenarios.
Only cases needing review invoke verification. Max42 initial/126 total attempts.
"""
import argparse, hashlib, json, time
from pathlib import Path
from copy import deepcopy
from sqlalchemy import select, func
from sqlalchemy.engine import make_url
from app.db import Session, engine
from app.models import Article, Batch, Supplier, Grant, GrantArticle, ConsumptionBudget, ApiCall
from app.settings import settings
from app.importer import digest
from app.jev import JevClient, ProviderError
from app.schemas import NormalizedAnalysis
from app import review_policy, review_support
from scripts.review_scenarios import cases as controlled_cases
from scripts.check_link_candidate import report_metrics
from scripts.evaluate_review_policy import invariant, summarize

ROOT=Path(__file__).resolve().parents[1]
BUDGET='review-support-1-development-20261018'
REPORT=ROOT/'reports/private/review-support-development.json'
FILES=['app/review_policy.py','app/review_support.py','scripts/review_scenarios.py',
    'app/link_candidate.py','app/link_questions.py','app/link_analysis.py','config/risk_policy.json']


def main():
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');args=p.parse_args()
    source=json.loads((ROOT/'reports/private/link-3-development.json').read_text())
    stored=list(source['results'].values());assert len(stored)==36
    assert all(v['group']in ('training','synthetic') for v in stored)
    hashes={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
    protocol={'version':review_policy.VERSION,'support_questions':review_policy.VERIFIER_VERSION,
        'files':hashes,'training':30,'stored_synthetic':6,'controlled_policy':6,
        'initial_requests_max':42,'attempts_including_retries_max':126,
        'hypothesis':'Explicit conditional-risk and polarity-specific exclusion support can replace redundant support blockers while preserving genuine missing scope, risk/urgency ambiguity and negative-decision uncertainty. Urgent action is independent of secondary priority uncertainty.',
        'promotion_guards':['Strictly more automatic correct cases with no added automatic joint errors',
            'All risk/urgency/supplier decisions and priority scores unchanged',
            'Known training omissions retain review, not reclassified as correct',
            'Controlled partial false-negative/unknown-route/ambiguous-urgency stay reviewed',
            'Controlled well-supported urgent case becomes automatic and audible with priority warning',
            'No claim of independent held-out accuracy; default1.0 stays reproducible'],
        'held_out':'No validation/test/LiveDay/answer key; only stored training and synthetics'}
    freeze=ROOT/'reports/review-support-freeze.json'
    if freeze.exists():assert json.loads(freeze.read_text())==protocol,'Frozen policy or questions changed'
    else:freeze.write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n')
    if not args.execute:print(json.dumps(protocol));return
    assert make_url(str(engine.url)).database=='radar_link_development'
    settings.jev_budget_limits_enabled=True
    r=json.loads(REPORT.read_text()) if REPORT.exists() else {'files':hashes,'results':{},'errors':[]}
    assert r['files']==hashes
    def save():REPORT.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    with Session() as db:
        suppliers=[s.data for s in db.scalars(select(Supplier).order_by(Supplier.id))];assert len(suppliers)==40
        all_cases=[]
        for row in stored:
            src=db.get(Article,row['prediction']['article_id']);assert src is not None
            all_cases.append({**row,'data':src.data,'suppliers':suppliers})
        all_cases.extend(controlled_cases(settings.jev_model))
        r.setdefault('global_calls_before',db.scalar(select(func.count()).select_from(ApiCall)))
        if not db.get(ConsumptionBudget,BUDGET):db.add(ConsumptionBudget(id=BUDGET,request_limit=126))
        if not db.get(Grant,BUDGET):db.add(Grant(id=BUDGET,split='training',article_limit=42,used=0,budget_id=BUDGET))
        bh=digest(protocol);batch=db.scalar(select(Batch).where(Batch.file_hash==bh))
        if not batch:batch=Batch(file_hash=bh,filename='QA_REVIEW_SUPPORT_TRAINING_SYNTHETIC',split='training',count=42);db.add(batch);db.flush()
        try:
            for i,c in enumerate(all_cases):
                key=c['group']+':'+c['case']
                if key in r['results']:continue
                origin=BUDGET+':'+key;art=db.scalar(select(Article).where(Article.origin_key==origin))
                if not art:
                    art=Article(origin_key=origin,batch_id=batch.id,context='exercise',row_order=i,news_id=c['data']['news_id'],data=c['data'],content_hash=digest(c['data']))
                    db.add(art);db.flush();db.add(GrantArticle(article_id=art.id,grant_id=BUDGET));db.get(Grant,BUDGET).used+=1
                db.commit()
                old=deepcopy(c['prediction']);old['article_id']=art.id
                candidate=review_policy.apply(old);verification=None;client=None;effective=None
                if candidate['analysis_status']=='review':
                    effective=review_support.payload(old,c['data'],c['suppliers'],settings.jev_model)
                    if effective['questions']:
                        client=JevClient(db,art.id,run_key=BUDGET+':'+review_policy.VERIFIER_VERSION)
                        response=client.ask(effective,'review_support',time.monotonic()+60)
                        verification=review_support.envelope(old,response);candidate=review_policy.apply(old,verification)
                invariant(old,candidate);NormalizedAnalysis.model_validate(candidate)
                r['results'][key]={'group':c['group'],'case':c['case'],'reference':c.get('reference'),
                    'before':old,'prediction':candidate,'verification':verification,
                    'effective_payload':effective,'expected_review':c.get('expected_review'),
                    'expected_sound':c.get('expected_sound'),'new_requests':client.network_requests if client else 0,
                    'cached_stages':client.cached_stages if client else []}
                save();print(json.dumps({'completed':len(r['results']),'total':42,'new_requests':r['results'][key]['new_requests']}),flush=True)
            r['complete']=True
        except ProviderError as e:
            r['errors'].append({'code':e.code});save();raise
        finally:
            calls=db.scalars(select(ApiCall).where(ApiCall.budget_id==BUDGET)).all()
            r['requests']=len(calls);r['reserved_requests']=db.get(ConsumptionBudget,BUDGET).requests_used
            r['global_calls_after']=db.scalar(select(func.count()).select_from(ApiCall))
            r['calls']=[{'stage':c.stage,'attempt':c.attempt,'seconds':c.duration,'model':c.model,'status':c.status,'usage':c.usage} for c in calls]
            rows=[v for v in r['results'].values() if v['group']=='training']
            r['metrics']={'before':report_metrics([{**v,'prediction':v['before']} for v in rows]),'after':report_metrics(rows)}
            r['causes_after']=summarize(rows);save()
            assert r['requests']<=126 and r['reserved_requests']<=126
    print(json.dumps({'complete':r.get('complete',False),'requests':r['requests'],'metrics':r['metrics']}))
if __name__=='__main__':main()
