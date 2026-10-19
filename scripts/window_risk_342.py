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
from scripts import risk_engine_342 as candidate_engine
from app.importer import digest
from scripts.window_common import ROOT,check_time,clone,save,accounting
from scripts.check_link_candidate import report_metrics
RUN='night-risk-publication-03';REPORT=ROOT/'reports/private/window-risk-publication.json'


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');args=ap.parse_args()
 if REPORT.exists() and json.loads(REPORT.read_text()).get('complete'):
  recorded=json.loads(REPORT.read_text())
  print(json.dumps({'complete':True,'new_requests_this_read':0,'recorded_requests':recorded['requests'],'metrics':recorded['metrics'],'post_run_contract_check':'reports/risk-contract-replay.json'}));return
 source=json.loads((ROOT/'reports/private/window-matching-potential.json').read_text())
 final=json.loads((ROOT/'reports/private/window-final-evaluation.json').read_text())
 rows={key:{**v,'old':v['prediction']} for key,v in source['results'].items()}
 rows.update({'controlled:'+v['case']:{**v,'group':'inspected_controls_development','old':v['prediction']} for v in final['results'].values() if v['profile']=='candidate'})
 protocol={'run':RUN,'hypothesis':'Broaden followup to strongly linked negative risk lacking evidence, not only the gray band. Anchor threat timing at publication and definite upcoming events, not unspecified now. Use actual focused risk probability with original risk/review gates; adverse facts never support no-risk, contradictions remain reviewed. Matching, urgency probability and business formula unchanged. Same-source checks, not external corroboration.',
  'sample':'30training+6synthetics+24previously inspected controlled cases, all development', 'risk_version':candidate_risk.VERSION,'questions':candidate_risk.QUESTIONS,'matching':candidate_matching.VERSION,'review':candidate_engine.VERSIONS['review'],'max_attempts':180,
  'targets':{k:candidate_risk.eligible(v['old']) for k,v in rows.items() if candidate_risk.eligible(v['old'])},
  'adoption':['No additional riskFP or urgentFP/FN; supplier predictions invariant; reduce riskFN or correctly automate more true risks; no newly wrong automatic case','All supplier predictions invariant','No new automatic joint errors','Concrete correctly automated risk or reduced omission','Unknown province/route and false links still reviewed','Before selectable adoption: freeze new18controls14scorable+4unknown; preserve safety, no newly wrong automatic case and improve development riskFN/automatic burden. Default unchanged regardless; no independent RSS accuracy claim.'],
  'files':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ('app/candidate_risk.py','scripts/risk_engine_342.py','app/candidate_matching.py','app/candidate_review.py','app/candidate_review_focus.py','config/risk_policy.json')}}
 fp=ROOT/'reports/window-risk-publication-freeze.json'
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
    check_time();used=accounting(db,RUN)['requests'];assert used<=180-36
    old=row['old'];origin=db.get(Article,old['article_id']);art=clone(db,RUN,key,origin.data,i,len(rows));rawold=row['raw']
    client=BoundedFanoutClient(PayloadCacheClient(db,art.id,run_key=RUN,reuse_runs=('night-potential-scope-02','night-final-controls-01','night-risk-focus-01','night-risk-current-02')))
    start=time.monotonic();prediction,raw=candidate_engine.run(client,art,ss,start+60,cached_a=rawold['a'],cached_b=rawold['b'])
    elapsed=time.monotonic()-start
    db.add(Analysis(article_id=art.id,generation=0,request_hash=digest([RUN,key]),result=prediction,raw=raw,duration=elapsed,cached=client.network_requests==0));art.state=prediction['analysis_status'];db.commit()
    r['results'][key]={'group':row['group'],'case':row['case'],'reference':row.get('reference'),'expected':row.get('expected'),'old':old,'prediction':prediction,'raw':raw,'seconds':elapsed,'new_requests':client.network_requests,'cached_stages':client.cached_stages}
    save(REPORT,r);print(json.dumps({'completed':len(r['results']),'case':key,'new_requests':client.network_requests,'risk':prediction['is_risk'],'review':prediction['analysis_status'],'changes':raw.get('_risk_projection',[])}),flush=True)
   r['complete']=True
  finally:
   r.update(accounting(db,RUN));r['metrics']={g:{name:report_metrics([{**v,'prediction':v[name]} for v in r['results'].values() if v['group']==g]) for name in ('old','prediction')} for g in set(v['group'] for v in r['results'].values())};save(REPORT,r);assert r['requests']<=180
 print(json.dumps({'complete':r.get('complete',False),'requests':r['requests'],'metrics':r['metrics']}))
if __name__=='__main__':main()
