"""Fixed geography-only check. Existing training/synthetic inputs; no Excel walk.

--execute enables paid calls; --retrospective is a single already inspected case,
only after completing development, never a new independent validation.
"""
import argparse,json,time,hashlib
from pathlib import Path
from sqlalchemy import select,func
from sqlalchemy.engine import make_url
from app.db import Session,engine
from app.models import Article,Batch,Supplier,RequestCache,ApiCall,Grant,GrantArticle,ConsumptionBudget
from app.settings import ROOT,settings,POLICY
from app.importer import digest
from app.analysis import normalize
from app.duration import durations
from app.jev import JevClient,ProviderError,validate_response
from app.stable_geography import stage_a,stage_b,annotate,VERSION
from reference.jev_requests import stage_a as old_a,stage_b as old_b
from app.schemas import NormalizedAnalysis
from app.evaluation import metrics

BUDGET='stable-geography-20261018'
PATH=ROOT/'reports/private/stable-geography-results.json'
FILES=['app/stable_geography.py','app/analysis.py','app/duration.py','app/geography.py','config/geography.json','reference/jev_requests.py','reference/scoring.py','config/risk_policy.json','app/jev.py']

def save(r):PATH.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--retrospective',action='store_true');args=p.parse_args()
 hashes={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
 freeze=ROOT/'reports/geo-candidate-freeze.json'
 if freeze.exists():assert json.loads(freeze.read_text())['files']==hashes,'Frozen inputs changed'
 else:freeze.write_text(json.dumps({'profile':VERSION,'risk_urgency_questions':'byte-identical to1.0.0','files':hashes,'maximum_requests_including_retries':438},indent=2)+'\n')
 if not args.execute:print(json.dumps({'prepared':True,'maximum_requests':438,'executed':False}));return
 assert make_url(str(engine.url)).database=='radar_link_development'
 settings.jev_budget_limits_enabled=True
 train=json.load(open(ROOT/'reports/private/link-training-comparison.json'))
 syn=json.load(open(ROOT/'reports/private/link-synthetic-results.json'))
 report=json.loads(PATH.read_text()) if PATH.exists() else {'files':hashes,'results':{},'errors':[],'maximum_requests':438}
 assert report['files']==hashes
 if args.retrospective:
  assert report.get('development_complete')
  historical=json.load(open(ROOT/'reports/private/link-retrospective-comparison.json'))
  target=next((k,v) for k,v in historical['results'].items() if k.startswith('1.0.0:') and v['news_id']=='N044')
  cases=[{'group':'retrospective','source_id':target[0].split(':',1)[1],'name':'N044','reference':target[1]['reference']}]
 else:
  cases=[{'group':'training','source_id':k.split(':',1)[1],'name':v['news_id'],'reference':v['reference']} for k,v in train['results'].items() if k.startswith('1.0.0:')]
  assert len(cases)==30
  cases += [{'group':'synthetic','source_id':v['prediction']['article_id'],'name':k,'expected':v['expected']} for k,v in syn['cases'].items()]
 with Session() as db:
  suppliers=[s.data for s in db.scalars(select(Supplier).order_by(Supplier.id))];assert len(suppliers)==40
  ch=digest(suppliers);assert report.get('catalog_hash',ch)==ch;report['catalog_hash']=ch
  report.setdefault('global_calls_before',db.scalar(select(func.count()).select_from(ApiCall)))
  if not db.get(ConsumptionBudget,BUDGET):db.add(ConsumptionBudget(id=BUDGET,request_limit=438))
  grant=BUDGET+(':retro' if args.retrospective else ':dev')
  if not db.get(Grant,grant):db.add(Grant(id=grant,split='validation' if args.retrospective else 'training',article_limit=len(cases),used=0,budget_id=BUDGET))
  bh=digest({'check':BUDGET,'retro':args.retrospective,'files':hashes})
  batch=db.scalar(select(Batch).where(Batch.file_hash==bh))
  if not batch:batch=Batch(file_hash=bh,filename='QA_GEOGRAPHY_RETRO' if args.retrospective else 'QA_GEOGRAPHY_TRAINING_SYNTHETIC',split='validation' if args.retrospective else 'training',count=len(cases));db.add(batch);db.flush()
  for i,c in enumerate(cases):
   origin=BUDGET+':'+c['group']+':'+c['name'];article=db.scalar(select(Article).where(Article.origin_key==origin))
   if not article:
    original=db.get(Article,c['source_id']);assert original is not None
    article=Article(origin_key=origin,batch_id=batch.id,context='exercise',row_order=i,news_id=original.news_id,data=original.data,content_hash=original.content_hash);db.add(article);db.flush()
    db.add(GrantArticle(article_id=article.id,grant_id=grant));db.get(Grant,grant).used+=1
   c['article_id']=article.id
  db.commit();save(report)
  try:
   for c in cases:
    article=db.get(Article,c['article_id'])
    for profile in ([VERSION] if args.retrospective else ['1.0.0',VERSION]):
     key=c['group']+':'+c['name']+':'+profile
     if key in report['results']:continue
     client=JevClient(db,article.id,run_key=BUDGET+':'+profile);reused=[]
     def ask(payload,stage):
      # Reuse only the same effective payload; duration changes invalidate B.
      old_run='link-evaluation:training:1.0.0' if c['group']=='training' and profile=='1.0.0' else None
      if old_run:
       old_key=digest({'request':digest({'payload':payload,'questions':POLICY['question_version']}),'run_key':old_run})
       cached=db.get(RequestCache,old_key)
       if cached:reused.append(stage);return validate_response(payload,cached.response)
      return client.ask(payload,stage,deadline)
     deadline=time.monotonic()+60
     ba,bb=(stage_a,stage_b) if profile==VERSION else (old_a,old_b)
     a=ask(ba(article.data,suppliers,settings.jev_model),'a')
     selected=[s for s in suppliers if a['answers']['linked_'+s['supplier_id']]['noul']>=POLICY['thresholds']['review_low']]
     ds=durations(article.data);b=ask(bb(article.data,selected,ds,settings.jev_model),'b') if selected else None
     result=normalize(article,suppliers,a,b,ds)
     if profile==VERSION:annotate(result,article,suppliers)
     NormalizedAnalysis.model_validate(result)
     report['results'][key]={'group':c['group'],'case':c['name'],'reference':c.get('reference'),'expected':c.get('expected'),'prediction':result,'raw_a':a,'raw_b':b,'new_requests':client.network_requests,'cached_stages':reused+client.cached_stages}
     save(report);print(json.dumps({'case':c['name'],'group':c['group'],'profile':profile,'new_requests':client.network_requests,'cache':reused+client.cached_stages}),flush=True)
   if not args.retrospective:report['development_complete']=True
  except ProviderError as exc:
   report['errors'].append({'code':exc.code});print(json.dumps({'stopped':exc.code}),flush=True);raise
  finally:
   calls=db.scalars(select(ApiCall).where(ApiCall.budget_id==BUDGET)).all();report['requests']=len(calls);report['reserved_requests']=db.get(ConsumptionBudget,BUDGET).requests_used
   assert report['requests']<=438 and report['reserved_requests']<=438
   report['global_calls_after']=db.scalar(select(func.count()).select_from(ApiCall))
   report['calls']=[{'stage':c.stage,'attempt':c.attempt,'seconds':c.duration,'model':c.model,'status':c.status,'usage':c.usage} for c in calls]
   report['training_metrics']={profile:metrics([(r['reference'],r['prediction']) for r in report['results'].values() if r['group']=='training' and r['prediction']['question_version']==profile]) for profile in ['1.0.0',VERSION]}
   save(report)
 print(json.dumps({'completed':report.get('development_complete',False),'requests':report['requests'],'training':report['training_metrics']}),flush=True)
if __name__=='__main__':main()
