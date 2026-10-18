"""Evaluate joint final exposure and partial-disruption risk on development only."""
import argparse,json,time,hashlib
from sqlalchemy import select
from sqlalchemy.engine import make_url
from app.db import Session,engine
from app.models import Article,Supplier,Analysis
from app.settings import settings
from app.jev import JevClient
from app import candidate_engine,candidate_matching,link_candidate
from app.importer import digest
from scripts.window_common import ROOT,check_time,clone,save,accounting
from scripts.check_link_candidate import report_metrics
RUN='night-joint-scope-01';REPORT=ROOT/'reports/private/window-matching.json'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    source=json.loads((ROOT/'reports/private/link-3-development.json').read_text());assert source['complete']
    old_review=json.loads((ROOT/'reports/private/window-review.json').read_text())
    protocol={'run':RUN,'versions':candidate_engine.VERSIONS,'cases':'30training+6existing synthetics','max_attempts':432,
        'hypothesis':'Joint final exposure distinguishes actual affected location/activity or declared route from coincident city/sector; reduced capacity remains risk even when stock covers it. Keep identity and urgency independent, review1.1-derived targeted checks, unchanged thresholds and formula.',
        'changed_predictions_expected':True,'retrieval':'Exact3.0A reused and validated; compact new B and conditional factual support are evaluated together, not a causal claim for one question.',
        'adoption':['Operationally better supplier FN/FP balance, not F1 alone','No new automatic erroneous risk/urgency/associations','Regional partial reduction riskY/nonurgent','Unknown province/route remain reviewed','Positive named supplier retains identity/riskN'],
        'files':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ('app/candidate_matching.py','app/candidate_review.py','app/candidate_engine.py','config/risk_policy.json')}}
    fp=ROOT/'reports/window-matching-freeze.json'
    if fp.exists():assert json.loads(fp.read_text())==protocol
    else:save(fp,protocol)
    if not args.execute:print(json.dumps(protocol));return
    assert make_url(str(engine.url)).database=='radar_link_development';settings.jev_budget_limits_enabled=True
    r=json.loads(REPORT.read_text()) if REPORT.exists() else {'run':RUN,'results':{},'versions':candidate_engine.VERSIONS}
    with Session() as db:
        ss=[s.data for s in db.scalars(select(Supplier).order_by(Supplier.id))];assert len(ss)==40
        try:
            for i,(key,row) in enumerate(source['results'].items()):
                if key in r['results']:continue
                check_time();source_article=db.get(Article,row['prediction']['article_id']);art=clone(db,RUN,key,source_article.data,i,36)
                pa=candidate_matching.stage_a(art.data,ss,settings.jev_model)
                assert pa==link_candidate.stage_a(source_article.data,ss,settings.jev_model)
                client=JevClient(db,art.id,run_key=RUN);start=time.monotonic()
                result,raw=candidate_engine.run(client,art,ss,start+60,cached_a=row['raw_a'])
                elapsed=time.monotonic()-start
                db.add(Analysis(article_id=art.id,generation=0,request_hash=digest([RUN,key]),result=result,raw=raw,duration=elapsed,cached=False));art.state=result['analysis_status'];db.commit()
                r['results'][key]={'group':row['group'],'case':row['case'],'reference':row.get('reference'),'expected':row.get('expected'),
                    'baseline':row['baseline'],'prior':old_review['results'][key]['prediction'],'prediction':result,'raw':raw,
                    'seconds':elapsed,'new_requests':client.network_requests,'cached_stages':client.cached_stages,'retrieval_reused':True}
                save(REPORT,r);print(json.dumps({'completed':len(r['results']),'requests':client.network_requests,'state':result['analysis_status']}),flush=True)
            r['complete']=True
        finally:
            r.update(accounting(db,RUN));rows=[v for v in r['results'].values() if v['group']=='training']
            r['metrics']={name:report_metrics([{**v,'prediction':v[name]} for v in rows]) for name in ('baseline','prior','prediction')};save(REPORT,r);assert r['requests']<=432
    print(json.dumps({'complete':r.get('complete',False),'requests':r['requests'],'metrics':r['metrics']}))
if __name__=='__main__':main()
