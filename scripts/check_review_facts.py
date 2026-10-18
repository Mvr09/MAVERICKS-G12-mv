"""Second registered hypothesis: verify factual basis, not quoted buyer advice.
Reuses ALL first-experiment valid support; shared budget never reset.
"""
import argparse,hashlib,json,time
from pathlib import Path
from sqlalchemy import select,func
from sqlalchemy.engine import make_url
from app import review_facts as candidate, review_policy
from app.db import Session,engine
from app.models import Article,Supplier,ApiCall,ConsumptionBudget
from app.settings import settings
from app.jev import JevClient,ProviderError
from app.schemas import NormalizedAnalysis
from scripts.review_scenarios import cases
from scripts.check_review_support import BUDGET
from scripts.check_link_candidate import report_metrics
from scripts.evaluate_review_policy import invariant,summarize
ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'reports/private/review-facts-development.json'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    previous=json.loads((ROOT/'reports/private/review-support-development.json').read_text());assert previous['complete']
    files=['app/review_policy.py','app/review_support.py','app/review_facts.py','scripts/review_scenarios.py','config/risk_policy.json']
    hashes={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}
    protocol={'policy_version':candidate.VERSION,'questions':candidate.QUESTIONS,'files':hashes,
        'hypothesis':'Replace demands for literal buyer advice/exclusion with explicit source factual basis: serious active stoppage versus limited/slow threat; clearly non-operational subject plus low final identity/exposure. Preserve uncertainty and original decisions.',
        'source_cases':42,'maximum_initial_requests':35,'shared_budget_total_including_first_trial_and_retries':126,
        'reuse':'All35valid support responses plus original A/B; never re-ask a valid response',
        'guards':['No changes to probabilities/classification/priority','Increase correct automatic coverage without adding automatic errors','Retain known training omissions and controlled missing-route/partial-risk-negative/ambiguous-urgency review','Clearly urgent supported case audible despite secondary score warning','No held-out data; no default change']}
    freeze=ROOT/'reports/review-facts-freeze.json'
    if freeze.exists():assert json.loads(freeze.read_text())==protocol,'Frozen factual candidate changed'
    else:freeze.write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n')
    if not args.execute:print(json.dumps(protocol));return
    assert make_url(str(engine.url)).database=='radar_link_development';settings.jev_budget_limits_enabled=True
    r=json.loads(REPORT.read_text()) if REPORT.exists() else {'files':hashes,'results':{},'errors':[]}
    assert r['files']==hashes
    def save():REPORT.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    controlled={c['case']:c for c in cases(settings.jev_model)}
    with Session() as db:
        ss=[s.data for s in db.scalars(select(Supplier).order_by(Supplier.id))]
        r.setdefault('global_calls_before',db.scalar(select(func.count()).select_from(ApiCall)))
        try:
            for key,row in previous['results'].items():
                if key in r['results']:continue
                old=row['before'];support=row['verification'];p=candidate.apply(old,support);facts=None;effective=None;client=None
                if p['analysis_status']=='review':
                    art=db.get(Article,old['article_id']);suppliers=controlled[row['case']]['suppliers'] if row['group']=='controlled_policy' else ss
                    effective=candidate.payload(old,art.data,suppliers,settings.jev_model)
                    if effective['questions']:
                        client=JevClient(db,art.id,run_key=BUDGET+':'+candidate.QUESTIONS)
                        answer=client.ask(effective,'review_facts',time.monotonic()+60)
                        facts={'binding':review_policy.binding(old),'version':candidate.QUESTIONS,'response':answer}
                        p=candidate.apply(old,support,facts)
                invariant(old,p);NormalizedAnalysis.model_validate(p)
                r['results'][key]={**row,'prediction':p,'facts':facts,'facts_payload':effective,'facts_new_requests':client.network_requests if client else 0,'facts_cache_stages':client.cached_stages if client else []}
                save();print(json.dumps({'completed':len(r['results']),'total':42,'new_requests':r['results'][key]['facts_new_requests']}),flush=True)
            r['complete']=True
        except ProviderError as e:r['errors'].append({'code':e.code});save();raise
        finally:
            calls=db.scalars(select(ApiCall).where(ApiCall.budget_id==BUDGET)).all()
            r['requests_shared']=len(calls);r['requests_this_trial']=sum(c.stage=='review_facts' for c in calls)
            r['calls']=[{'stage':c.stage,'attempt':c.attempt,'seconds':c.duration,'model':c.model,'status':c.status,'usage':c.usage} for c in calls]
            r['global_calls_after']=db.scalar(select(func.count()).select_from(ApiCall));r['reserved_requests']=db.get(ConsumptionBudget,BUDGET).requests_used
            rows=[v for v in r['results'].values() if v['group']=='training'];r['metrics']={'before':report_metrics([{**v,'prediction':v['before']} for v in rows]),'after':report_metrics(rows)};r['causes_after']=summarize(rows);save()
            assert r['requests_shared']<=126 and r['reserved_requests']<=126
    print(json.dumps({'complete':r.get('complete',False),'requests_shared':r['requests_shared'],'requests_trial':r['requests_this_trial'],'metrics':r['metrics']}))
if __name__=='__main__':main()
