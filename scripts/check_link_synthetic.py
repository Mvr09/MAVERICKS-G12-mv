"""Frozen-profile synthetic QA with real JEV; not an accuracy estimate."""
import json,hashlib
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.engine import make_url
from app.settings import ROOT,settings
from app.db import Session,engine,Base
from app.models import Batch,Article,Grant,GrantArticle,ConsumptionBudget,ApiCall
from app.importer import digest
from app.analysis import process_article
from app.link_questions import VERSION

if make_url(str(engine.url)).database!='radar_link_development':raise SystemExit('Dedicated development DB required')
freeze=json.loads((ROOT/'reports/link-v2-freeze.json').read_text())
for f,h in freeze['files'].items():
 if hashlib.sha256((ROOT/f).read_bytes()).hexdigest()!=h:raise SystemExit('Frozen profile changed')
cases=[
 {'name':'multi_location','headline':'Floods close chemical factories around Ahmedabad and Vadodara','summary':'Chemical, pharmaceutical and mineral salt factories around Ahmedabad and Vadodara have halted production after major floods. Hyderabad is unaffected. Restoration will take weeks.','suppliers':['S002','S006','S014'],'risk':'Y','urgent':'Y'},
 {'name':'alias_irrelevant','headline':'Łódź hosts an international film festival','summary':'The city celebrates a film festival. No industrial or transport interruption is reported.','suppliers':[],'risk':'N','urgent':'N'},
 {'name':'alias_harmless','headline':'Bangalore university opens a mathematics exhibition','summary':'Students attend an exhibition on campus. Local laboratories, industry and transport continue normally.','suppliers':[],'risk':'N','urgent':'N'},
 {'name':'partial_interruption','headline':'Brief power rationing affects Hangzhou factories','summary':'Factories in Hangzhou reduce electricity consumption by 20 percent for two days. Production continues at reduced capacity; no stock has been destroyed.','suppliers':['S024'],'risk':'Y','urgent':'N'},
 {'name':'ambiguous_city','headline':'Factory shutdown in Taizhou, Zhejiang; Jiangsu unaffected','summary':'An industrial shutdown affects chemical factories in Zhejiang Taizhou. The city with the same name in Jiangsu is explicitly unaffected. Individual companies are not named.','require_review':True},
 {'name':'namesake_geography','headline':'Orion Capital funds a movie studio in Basel','summary':'Investment firm Orion Capital has financed a movie studio in Basel. No chemical or pharmaceutical enterprise is involved.','suppliers':[],'risk':'N','urgent':'N'},
]
path=ROOT/'reports/private/link-synthetic-results.json'
report=json.loads(path.read_text()) if path.exists() else {'profile':VERSION,'cases':{},'independent_accuracy_claim':False,'maximum_requests_including_retries':36}
settings.jev_budget_limits_enabled=True
with Session() as db:
 b=db.scalar(select(Batch).where(Batch.file_hash==digest(cases)))
 if not b:
  b=Batch(file_hash=digest(cases),split='training',filename='SINTETICOS_QA',count=len(cases));db.add(b);db.flush()
  for i,c in enumerate(cases):
   data={'news_id':'SYN-GEO-'+str(i+1),'headline':c['headline'],'summary':c['summary'],'source':'SINTÉTICO · QA identificado','published_date':'2026-10-18T00:00:00+00:00','language':'en','context_id':'exercise'}
   db.add(Article(origin_key='synthetic-geo:'+c['name'],batch_id=b.id,context='exercise',row_order=i,news_id=data['news_id'],data=data,content_hash=digest(data)))
  db.flush()
 budget='link-synthetic-20261018'
 if not db.get(ConsumptionBudget,budget):db.add(ConsumptionBudget(id=budget,request_limit=36))
 if not db.get(Grant,budget):db.add(Grant(id=budget,split='training',article_limit=None,used=0,budget_id=budget))
 db.flush();articles=db.scalars(select(Article).where(Article.batch_id==b.id).order_by(Article.row_order)).all()
 for a in articles:
  if not db.get(GrantArticle,a.id):db.add(GrantArticle(article_id=a.id,grant_id=budget))
 db.commit()
 for a,c in zip(articles,cases):
  if c['name'] in report['cases']:continue
  result=process_article(db,a.id,profile=VERSION,publish=False,run_key='synthetic:'+VERSION)
  if result['analysis_status']=='error':raise SystemExit('Provider error: '+result['error'])
  passed=result['analysis_status']=='review' if c.get('require_review') else result['affected_supplier_ids']==c['suppliers'] and result['is_risk']==c['risk'] and result['urgent']==c['urgent']
  report['cases'][c['name']]={'expected':c,'prediction':result,'passed':passed}
  path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
 calls=db.scalars(select(ApiCall).where(ApiCall.budget_id==budget)).all();report['requests']=len(calls)
 report['calls']=[{'stage':c.stage,'attempt':c.attempt,'seconds':c.duration,'model':c.model,'status':c.status,'usage':c.usage} for c in calls]
path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'profile':VERSION,'cases':{k:r['passed'] for k,r in report['cases'].items()},'requests':report['requests'],'independent_accuracy_claim':False}))
