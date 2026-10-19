"""Frozen fresh controlled comparison; state/question-preserving fanout for all."""
import argparse,json,time
from sqlalchemy import select
from sqlalchemy.engine import make_url
from app.db import Session,engine
from app.models import Supplier,Analysis
from app.settings import settings
from app.payload_cache import PayloadCacheClient
from app.jev_transport import BoundedFanoutClient
from app.importer import digest
from scripts import candidate_engine_33 as candidate_engine
from scripts import risk_engine_342
from scripts.window_final_evaluation import baseline
from scripts.window_sample_342 import PATH,freeze
from scripts.window_common import ROOT,clone,save,check_time,accounting
from scripts.check_link_candidate import report_metrics
RUN='night-fresh-publication-01';REPORT=ROOT/'reports/private/window-fresh-342.json'


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');args=ap.parse_args();protocol=freeze()
 if not args.execute:print(json.dumps(protocol));return
 assert make_url(str(engine.url)).database=='radar_link_development';settings.jev_budget_limits_enabled=True
 cases=json.loads(PATH.read_text())['cases'];r=json.loads(REPORT.read_text())if REPORT.exists()else{'run':RUN,'protocol':protocol,'results':{},'transport_note':'fanout1.0 preserves full logical baseline/state/questions too; semantic comparison, not unmodified production latency.'}
 assert r['protocol']==protocol
 profiles={'baseline':baseline,'prior_3_3':candidate_engine.run,'candidate_3_4_2':risk_engine_342.run}
 with Session()as db:
  ss=[s.data for s in db.scalars(select(Supplier).order_by(Supplier.id))]
  try:
   for i,c in enumerate(cases):
    for name,fn in profiles.items():
     key=c['case']+':'+name
     if key in r['results']:continue
     check_time();assert accounting(db,RUN)['requests']<=360-36
     art=clone(db,RUN,key,c['data'],i*3+list(profiles).index(name),54)
     client=BoundedFanoutClient(PayloadCacheClient(db,art.id,run_key=RUN));start=time.monotonic()
     result,raw=fn(client,art,ss,start+60);elapsed=time.monotonic()-start
     db.add(Analysis(article_id=art.id,generation=0,request_hash=digest([RUN,key]),result=result,raw=raw,duration=elapsed,cached=client.network_requests==0));art.state=result['analysis_status'];db.commit()
     r['results'][key]={'case':c['case'],'profile':name,'reference':c['reference'],'reference_reason':c['reason'],'must_review':c['must_review'],'prediction':result,'raw':raw,'seconds':elapsed,'new_requests':client.network_requests,'cached_stages':client.cached_stages}
     save(REPORT,r);print(json.dumps({'completed':len(r['results']),'case':c['case'],'profile':name,'new_requests':client.network_requests,'state':result['analysis_status']}),flush=True)
   r['complete']=True
  finally:
   r.update(accounting(db,RUN));r['metrics']={name:report_metrics([v for v in r['results'].values()if v['profile']==name])for name in profiles};save(REPORT,r);assert r['requests']<=360
 print(json.dumps({'complete':r.get('complete',False),'requests':r['requests'],'metrics':r['metrics']}))
if __name__=='__main__':main()
