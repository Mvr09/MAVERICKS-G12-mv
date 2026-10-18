"""Explicit training-only experiment. Resumable private results; never adjusts prompts.

Run against dedicated radar_link_development, never production. No protected
labels are printed or sent to JEV. Profiles/risk policy are hashed before calls.
"""
import argparse,json,time,hashlib
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from datetime import datetime,timezone
from sqlalchemy import select,func
from sqlalchemy.engine import make_url
from app.settings import settings,ROOT
from app.db import engine,Base,Session
from app.models import Article,Batch,EvaluationLabel,ApiCall,Grant,GrantArticle,ConsumptionBudget
from app.cli import seed
from app.importer import import_excel
from app.analysis import process_article
from app.evaluation import metrics
from app.link_questions import VERSION

parser=argparse.ArgumentParser()
parser.add_argument('--execute',action='store_true')
parser.add_argument('--new-iteration',action='store_true')
parser.add_argument('--article-limit',type=int)
parser.add_argument('--acknowledge-diagnosed-errors',action='store_true')
parser.add_argument('--historical-baseline')
parser.add_argument('--phase',choices=['training','retrospective'],default='training')
args=parser.parse_args()
if make_url(str(engine.url)).database!='radar_link_development':raise SystemExit('Dedicated database radar_link_development required')
if args.phase=='retrospective':
    freeze=ROOT/'reports/link-v2-freeze.json'
    if not freeze.exists():raise SystemExit('Freeze training version before retrospective comparison')
    for filename,digest in json.loads(freeze.read_text())['files'].items():
        if hashlib.sha256((ROOT/filename).read_bytes()).hexdigest()!=digest:raise SystemExit('Frozen candidate changed')
Base.metadata.create_all(engine)
private=ROOT/'reports/private';private.mkdir(exist_ok=True,parents=True)
name='supplier_training.xlsx' if args.phase=='training' else 'supplier_validation.xlsx'
filename=private/('link-'+args.phase+'-comparison.json')
report=json.loads(filename.read_text()) if filename.exists() else {'phase':args.phase,'started_at':datetime.now(timezone.utc).isoformat(),'results':{},'maximum_requests_including_retries':360 if args.phase=='training' else 120}
current_files={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ['reference/jev_requests.py','config/risk_policy.json','app/link_questions.py','app/link_analysis.py','app/geography.py','config/geography.json']}
if report.get('files') and report['files'] != current_files and report['results']:
    if not args.new_iteration:raise SystemExit('Experiment files changed: archive results explicitly before another iteration')
    report.setdefault('archived_iterations',[]).append({'files':report['files'],'results':{k:v for k,v in report['results'].items() if not k.startswith('1.0.0:')}})
    report['results']={k:v for k,v in report['results'].items() if k.startswith('1.0.0:')}
report['files']=current_files
if args.acknowledge_diagnosed_errors:
    failed={k:v for k,v in report['results'].items() if v['prediction']['analysis_status']=='error'}
    report.setdefault('failed_attempts',[]).append(failed)
    report['results']={k:v for k,v in report['results'].items() if k not in failed}
ack_at=datetime.now(timezone.utc).isoformat() if args.acknowledge_diagnosed_errors else None
# Each process run uses a bounded experiment budget, independently of the demo's
# user-authorized unlimited manual operation. Existing experiment usage persists.
settings.jev_budget_limits_enabled=True
with Session() as db:
    seed(db)
    batch,_=import_excel(db,(ROOT/'inputs'/name).read_bytes(),name)
    bid=batch.id
    budget_id='link-v2-'+args.phase+'-20261018'
    grant_id=budget_id+'-grant'
    if not db.get(ConsumptionBudget,budget_id):db.add(ConsumptionBudget(id=budget_id,request_limit=report['maximum_requests_including_retries']))
    if not db.get(Grant,grant_id):db.add(Grant(id=grant_id,split=batch.split,article_limit=None,used=0,budget_id=budget_id))
    db.flush()
    articles=db.scalars(select(Article).where(Article.batch_id==bid).order_by(Article.row_order)).all()
    ids=[a.id for a in articles]
    if args.article_limit is not None:ids=ids[:args.article_limit]
    for a in articles:
        old=db.get(GrantArticle,a.id)
        if not old:db.add(GrantArticle(article_id=a.id,grant_id=grant_id))
        elif old.grant_id!=grant_id:raise SystemExit('Unexpected grant; refuse to overwrite accounting')
    db.commit()
if args.historical_baseline:
    if args.phase != 'retrospective':raise SystemExit('Historical baseline only valid for retrospective phase')
    historical=json.loads(Path(args.historical_baseline).read_text())
    if historical['split']!='validation' or len(historical['rows'])!=len(ids):raise SystemExit('Historical cohort differs')
    by_news={r['news_id']:r for r in historical['rows']}
    with Session() as db:
        for aid in ids:
            a=db.get(Article,aid);label=db.get(EvaluationLabel,aid).data;old=by_news[a.news_id]
            expected=sorted(s.strip() for s in str(label.get('Affected_Supplier_IDs') or '').split(';') if s.strip())
            if old['reference']['is_risk']!=label['Is_Risk'] or old['reference']['urgent']!=label['Urgent'] or old['reference']['affected_supplier_ids']!=expected:raise SystemExit('Reference mismatch')
            report['results']['1.0.0:'+aid]={'news_id':a.news_id,'reference':label,'prediction':old['prediction']}
    report['baseline_source']='Stored Railway validation predictions, unchanged; no fresh v1 inference'

report['batch_id']=bid

def save():filename.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
def task(aid,profile):
    key=profile+':'+aid
    with Session() as db:
        a=db.get(Article,aid)
        result=process_article(db,aid,profile=profile,publish=False,diagnostic_ack_at=ack_at,run_key='link-evaluation:'+args.phase+':'+profile)
        label=db.get(EvaluationLabel,aid).data
        return key,{'news_id':a.news_id,'reference':label,'prediction':result}
if args.execute:
    for profile in ['1.0.0',VERSION]:
        pending=[aid for aid in ids if profile+':'+aid not in report['results']]
        start=time.monotonic()
        # Provider/client already bounds to four across processes, plus leases.
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures={pool.submit(task,aid,profile):aid for aid in pending}
            for future in as_completed(futures):
                key,row=future.result();report['results'][key]=row;save()
                if row['prediction']['analysis_status']=='error':
                    for other in futures:other.cancel()
                    raise SystemExit('Provider failure '+row['prediction']['error']+'; diagnose before resuming')
        if pending:report.setdefault('elapsed_seconds',{})[profile]=round(report.get('elapsed_seconds',{}).get(profile,0)+time.monotonic()-start,3)
        save()
summary={}
for profile in ['1.0.0',VERSION]:
    subset=[report['results'][profile+':'+aid] for aid in ids if profile+':'+aid in report['results']]
    summary[profile]={'processed':len(subset),'metrics':metrics([(r['reference'],r['prediction']) for r in subset]) if subset else None}
with Session() as db:
    calls=db.scalars(select(ApiCall).where(ApiCall.budget_id==budget_id)).all()
    report['calls']=[{'article_id':c.article_id,'stage':c.stage,'attempt':c.attempt,'seconds':c.duration,'model':c.model,'status':c.status,'usage':c.usage} for c in calls]
    report['requests']=len(calls)
    report['usage']={k:sum(c.usage.get(k,0) for c in calls if isinstance(c.usage.get(k),(int,float))) for k in ['input_tokens','output_tokens','total_tokens']}
report['summary']=summary;report['completed_at']=datetime.now(timezone.utc).isoformat();save()
print(json.dumps({'phase':args.phase,'summary':summary,'requests':report['requests'],'elapsed_seconds':report.get('elapsed_seconds',{}),'new_independent_evaluation':False},ensure_ascii=False))
