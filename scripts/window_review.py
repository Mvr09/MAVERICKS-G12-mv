"""Hypothesis: relationship-specific exclusion resolves overly broad topic doubt."""
import argparse,json,time,hashlib
from copy import deepcopy
from sqlalchemy import select
from sqlalchemy.engine import make_url
from app.db import Session,engine
from app.models import Article,Supplier
from app.settings import settings
from app.jev import JevClient,validate_response
from app.review_policy import binding
from app import candidate_review as candidate,review_support,review_facts
from scripts.review_scenarios import cases
from scripts.check_link_candidate import report_metrics
from scripts.evaluate_review_policy import invariant,summarize
from scripts.window_common import ROOT,check_time,clone,save,accounting
RUN='night-relational-review-01'
REPORT=ROOT/'reports/private/window-review.json'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    old=json.loads((ROOT/'reports/private/review-facts-development.json').read_text());assert old['complete']
    freeze={'run':RUN,'review':candidate.VERSION,'questions':candidate.EXCLUSION_VERSION,
        'hypothesis':'An article can describe real normal activity unrelated to this supplier. Verify a different actual subject relative to catalog, not an abstract non-operational label. Require positive support, source passage and low final identity/link; retain unknown compatible routes and ambiguous scope.',
        'cases':42,'max_attempts':90,'predictions_frozen':True,
        'adoption':['More correct automatic cases, no added automatic error','Known omissions still reviewed','Positive named identities retained','Unknown route/partial-risk-negative/ambiguous-urgency still reviewed'],
        'hashes':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ('app/candidate_review.py','config/risk_policy.json')}}
    fp=ROOT/'reports/window-review-freeze.json'
    if fp.exists():assert json.loads(fp.read_text())==freeze
    else:save(fp,freeze)
    if not args.execute:print(json.dumps(freeze));return
    assert make_url(str(engine.url)).database=='radar_link_development';settings.jev_budget_limits_enabled=True
    r=json.loads(REPORT.read_text()) if REPORT.exists() else {'results':{},'run':RUN,'hypothesis':freeze['hypothesis']}
    controls={c['case']:c for c in cases(settings.jev_model)}
    with Session() as db:
        suppliers=[s.data for s in db.scalars(select(Supplier).order_by(Supplier.id))]
        try:
            for i,(key,row) in enumerate(old['results'].items()):
                if key in r['results']:continue
                check_time();source=db.get(Article,row['before']['article_id']);ss=controls[row['case']]['suppliers'] if row['group']=='controlled_policy' else suppliers
                art=clone(db,RUN,key,source.data,i,42);before=deepcopy(row['before']);before['article_id']=art.id
                support=deepcopy(row['verification']);facts=deepcopy(row['facts'])
                if support:
                    p=review_support.payload(before,art.data,ss,settings.jev_model);assert p==row['effective_payload'];validate_response(p,support['response']);support['binding']=binding(before)
                if facts:
                    p=review_facts.payload(before,art.data,ss,settings.jev_model);assert p==row['facts_payload'];validate_response(p,facts['response']);facts['binding']=binding(before)
                result=candidate.apply(before,support,facts);extra=None;p=None;client=None
                if result['analysis_status']=='review':
                    p=candidate.exclusion_payload(result,art.data,ss,settings.jev_model)
                    if p['questions']:
                        client=JevClient(db,art.id,run_key=RUN);answer=client.ask(p,'relational_exclusion',time.monotonic()+60)
                        extra={'binding':binding(before),'version':candidate.EXCLUSION_VERSION,'response':answer}
                        result=candidate.apply(before,support,facts,extra)
                invariant(before,result)
                r['results'][key]={'group':row['group'],'case':row['case'],'reference':row.get('reference'),
                    'before':before,'prior':row['prediction'],'prediction':result,'support':support,'facts':facts,'exclusion':extra,'effective_payload':p,
                    'source_analysis_id':source.id,'exact_payloads_reused':bool(support or facts),'new_requests':client.network_requests if client else 0}
                save(REPORT,r);print(json.dumps({'completed':len(r['results']),'requests':r['results'][key]['new_requests']}),flush=True)
            r['complete']=True
        finally:
            r.update(accounting(db,RUN));rows=[v for v in r['results'].values() if v['group']=='training']
            r['metrics']={'prior':report_metrics([{**v,'prediction':v['prior']} for v in rows]),'candidate':report_metrics(rows)};r['causes']=summarize(rows);save(REPORT,r);assert r['requests']<=90
    print(json.dumps({'complete':r.get('complete',False),'requests':r['requests'],'metrics':r['metrics']}))
if __name__=='__main__':main()
