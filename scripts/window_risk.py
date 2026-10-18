"""One source-risk hypothesis, training and already-inspected controls only."""
import argparse,json,time,hashlib
from sqlalchemy import select
from sqlalchemy.engine import make_url
from app.db import Session,engine
from app.models import Article,Supplier,Analysis
from app.settings import settings
from app.payload_cache import PayloadCacheClient
from app.jev_transport import BoundedFanoutClient
from app import candidate_risk,candidate_matching
from scripts import risk_engine_trial as candidate_engine
from app.importer import digest
from scripts.window_common import ROOT,check_time,clone,save,accounting
from scripts.check_link_candidate import report_metrics
RUN='night-risk-focus-01';REPORT=ROOT/'reports/private/window-risk-focus.json'


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');args=ap.parse_args()
 source=json.loads((ROOT/'reports/private/window-matching-potential.json').read_text())
 final=json.loads((ROOT/'reports/private/window-final-evaluation.json').read_text())
 rows={key:{**v,'old':v['prediction']} for key,v in source['results'].items()}
 rows.update({'controlled:'+v['case']:{**v,'group':'inspected_controls_development','old':v['prediction']} for v in final['results'].values() if v['profile']=='candidate'})
 protocol={'run':RUN,'hypothesis':'Independently linked partial output/delivery loss and adverse strategic instability are threats before stockout/urgency. A focused factual stage omits business buffers, cannot create links, lower thresholds, or modify urgency. Only strongly factual positive corrections are applied; other review remains.',
  'sample':'30training+6synthetics+24previously inspected controlled cases, all development', 'risk_version':candidate_risk.VERSION,'questions':candidate_risk.QUESTIONS,'matching':candidate_matching.VERSION,'review':candidate_engine.VERSIONS['review'],'max_attempts':240,
  'targets':{k:candidate_risk.eligible(v['old']) for k,v in rows.items() if candidate_risk.eligible(v['old'])},
  'adoption':['No new risk FP/FN or urgent FP/FN on development','All supplier predictions invariant','No new automatic joint errors','Concrete correctly automated risk or reduced omission','Unknown province/route and false links still reviewed','Fresh pre-referenced controlled sample before final selectable adoption; default unchanged'],
  'files':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ('app/candidate_risk.py','app/candidate_engine.py','app/candidate_matching.py','app/candidate_review.py','config/risk_policy.json')}}
 fp=ROOT/'reports/window-risk-freeze.json'
 if fp.exists():assert json.loads(fp.read_text())==protocol
 else:save(fp,protocol)
 if not args.execute:print(json.dumps(protocol));return
 assert make_url(str(engine.url)).database=='radar_link_development';settings.jev_budget_limits_enabled=True
 r=json.loads(REPORT.read_text()) if REPORT.exists() else {'run':RUN,'results':{},'protocol':protocol}
 with Session() as db:
  ss=[s.data for s in db.scalars(select(Supplier).order_by(Supplier.id))];assert len(ss)==40
  try:
   for i,(key,row) in enumerate(rows.items()):
    if key in r['results']:continue
    check_time();used=accounting(db,RUN)['requests'];assert used<=240-36
    old=row['old'];origin=db.get(Article,old['article_id']);art=clone(db,RUN,key,origin.data,i,len(rows));rawold=row['raw']
    client=BoundedFanoutClient(PayloadCacheClient(db,art.id,run_key=RUN,reuse_runs=('night-potential-scope-02','night-final-controls-01')))
    start=time.monotonic();prediction,raw=candidate_engine.run(client,art,ss,start+60,cached_a=rawold['a'],cached_b=rawold['b'],risk_focus=True)
    elapsed=time.monotonic()-start
    db.add(Analysis(article_id=art.id,generation=0,request_hash=digest([RUN,key]),result=prediction,raw=raw,duration=elapsed,cached=client.network_requests==0));art.state=prediction['analysis_status'];db.commit()
    r['results'][key]={'group':row['group'],'case':row['case'],'reference':row.get('reference'),'expected':row.get('expected'),'old':old,'prediction':prediction,'raw':raw,'seconds':elapsed,'new_requests':client.network_requests,'cached_stages':client.cached_stages}
    save(REPORT,r);print(json.dumps({'completed':len(r['results']),'case':key,'new_requests':client.network_requests,'risk':prediction['is_risk'],'review':prediction['analysis_status'],'changes':raw.get('_risk_projection',[])}),flush=True)
   r['complete']=True
  finally:
   r.update(accounting(db,RUN));r['metrics']={g:{name:report_metrics([{**v,'prediction':v[name]} for v in r['results'].values() if v['group']==g]) for name in ('old','prediction')} for g in set(v['group'] for v in r['results'].values())};save(REPORT,r);assert r['requests']<=240
 print(json.dumps({'complete':r.get('complete',False),'requests':r['requests'],'metrics':r['metrics']}))
if __name__=='__main__':main()
