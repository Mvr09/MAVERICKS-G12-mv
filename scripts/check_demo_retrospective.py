"""One frozen retrospective N044 diagnosis. Never development or a new holdout."""
import json,time,hashlib
from pathlib import Path
from datetime import datetime,timezone
from sqlalchemy import select,func
from sqlalchemy.engine import make_url
from app.db import Session,engine
from app.models import Article,Batch,Supplier,Analysis,ConsumptionBudget,Grant,GrantArticle,ApiCall
from app.settings import settings
from app.importer import digest
from app.payload_cache import PayloadCacheClient
from app.jev_transport import BoundedFanoutClient
from app.candidate_engine import run
ROOT=Path(__file__).resolve().parents[1];RUN='demo-selection-retrospective-20261019';P=ROOT/'reports/private/demo-selection-retrospective.json'
def main():
 freeze=json.loads((ROOT/'reports/demo-selection-freeze.json').read_text());assert all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h for f,h in freeze['files'].items());assert make_url(str(engine.url)).database=='radar_link_development'
 if P.exists() and json.loads(P.read_text()).get('complete'):print('Valid stored retrospective reused; no new calls');return
 settings.jev_budget_limits_enabled=True
 with Session()as db:
  source=db.scalar(select(Article).join(Batch,Article.batch_id==Batch.id).where(Article.news_id=='N044',Batch.split=='validation'));assert source is not None
  budget=db.get(ConsumptionBudget,RUN)
  if not budget:db.add(ConsumptionBudget(id=RUN,request_limit=36));db.add(Grant(id=RUN,split='validation',article_limit=1,used=0,budget_id=RUN));db.flush()
  art=db.scalar(select(Article).where(Article.origin_key==RUN))
  if not art:
   batch=Batch(file_hash=digest(RUN),filename='DIAGNOSTICO_RETROSPECTIVO_N044_NO_DESARROLLO',split='validation',count=1);db.add(batch);db.flush()
   art=Article(origin_key=RUN,batch_id=batch.id,context='exercise',row_order=0,news_id='N044',data=dict(source.data),content_hash=source.content_hash);db.add(art);db.flush();db.add(GrantArticle(article_id=art.id,grant_id=RUN));db.get(Grant,RUN).used+=1;db.commit()
  before=db.scalar(select(func.count()).select_from(ApiCall));ss=[s.data for s in db.scalars(select(Supplier).order_by(Supplier.id))];client=BoundedFanoutClient(PayloadCacheClient(db,art.id,run_key=RUN));start=time.monotonic();r={'phase':'retrospective only, already inspected validation; no changes permitted from this result','before_counter':before,'complete':False}
  try:
   result,raw=run(client,art,ss,start+60);db.add(Analysis(article_id=art.id,generation=0,request_hash=digest([RUN,freeze['files']]),result=result,raw=raw,duration=time.monotonic()-start,cached=client.network_requests==0));art.state=result['analysis_status'];db.commit();r.update(complete=True,prediction=result,raw=raw,source_data=source.data)
  except Exception as exc:r['error_type']=type(exc).__name__;raise
  finally:
   calls=db.scalars(select(ApiCall).where(ApiCall.run_key==RUN)).all();r.update(seconds=time.monotonic()-start,after_counter=db.scalar(select(func.count()).select_from(ApiCall)),new_requests=len(calls),cached_stages=client.cached_stages,calls=[{'stage':c.stage,'attempt':c.attempt,'status':c.status,'model':c.model,'usage':c.usage,'duration':c.duration}for c in calls],checked_at=datetime.now(timezone.utc).isoformat());P.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
  print(json.dumps({'complete':r['complete'],'new_requests':r['new_requests'],'risk':result['is_risk'],'urgent':result['urgent'],'suppliers':result['affected_supplier_ids'],'state':result['analysis_status'],'s024':next((a for a in result['assessments']if a['supplier_id']=='S024'),None)},ensure_ascii=False))
if __name__=='__main__':main()
