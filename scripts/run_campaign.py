"""Explicit local executor, same service/pipeline and durable counters as worker.
No repeated valid entries; no operational ingestion; four concurrent records.
"""
import json,sys,time,os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from sqlalchemy import select
from app.db import Session
from app.models import CampaignRun,EvaluationCampaign,Job
from app.campaigns import prepare,start,process,report

with Session() as db:
 c=prepare(db,json.loads(Path(sys.argv[1]).read_text()));cid=c.id
 Path('.runtime/campaign-local-id').write_text(cid)
 print(json.dumps({'prepared':cid,'freeze':{k:v for k,v in c.freeze.items() if k not in ('inputs','suppliers','materials')}},ensure_ascii=False),flush=True)
 start(db,cid)
 ids=[r.id for r in db.scalars(select(CampaignRun).where(CampaignRun.campaign_id==cid,CampaignRun.state.in_(('queued','running'))).order_by(CampaignRun.input_key,CampaignRun.profile))]

def run(rid):
 with Session() as db:
  r=process(db,rid)
  j=db.scalar(select(Job).where(Job.key=='campaign:'+rid))
  j.state='done' if r.state in ('done','review') else 'error' if r.state=='error' else 'cancelled';j.error=(r.result or {}).get('error');db.commit()
  return {'id':rid,'state':r.state,'error':(r.result or {}).get('error'),'new_requests':r.audit.get('new_requests',0)}
with ThreadPoolExecutor(max_workers=4) as pool:
 for i,f in enumerate(as_completed([pool.submit(run,rid) for rid in ids])):
  result=f.result();print(json.dumps({'completed_executor':i+1,**result}),flush=True)
  if i%8==0:
   with Session() as db:Path('.runtime/new-campaign-local-progress.json').write_text(json.dumps(report(db,cid,'all'),default=str,ensure_ascii=False))
with Session() as db:
 for sample in ('training','validation','test','liveday','labelled','all'):
  Path('.runtime/new-campaign-'+sample+'.json').write_text(json.dumps(report(db,cid,sample),default=str,ensure_ascii=False,indent=2))
 final=report(db,cid,'all',True);Path('.runtime/new-campaign-private-export.json').write_text(json.dumps(final,default=str,ensure_ascii=False))
 print(json.dumps({'finished':cid,'state':final['state'],'progress':final['progress'],'aggregates':final['aggregate']},ensure_ascii=False),flush=True)
