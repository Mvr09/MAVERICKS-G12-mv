"""Frozen three-way comparison; no held-out challenge files are read."""
import argparse,json,time
from sqlalchemy import select
from sqlalchemy.engine import make_url
from app.db import Session,engine
from app.models import Supplier,Analysis
from app.settings import settings,POLICY
from app.importer import digest
from app.jev import ProviderError
from scripts.record_experiment_failure import record_failure
from app.payload_cache import PayloadCacheClient
from app import candidate_engine,link_candidate,review_support,review_facts,review_policy
from app.analysis import normalize
from app.duration import durations
from reference.jev_requests import stage_a,stage_b
from scripts.window_common import ROOT,save,clone,check_time,accounting
from scripts.window_sample import PATH,freeze
from scripts.check_link_candidate import report_metrics
RUN='night-final-controls-01';REPORT=ROOT/'reports/private/window-final-evaluation.json'


def previous(client,art,suppliers,deadline):
    aa=client.ask(link_candidate.stage_a(art.data,suppliers,settings.jev_model),'previous_a',deadline)
    selected=link_candidate.select_candidates(art.data,suppliers,aa);ds=durations(art.data)
    bb=client.ask(link_candidate.stage_b(art.data,selected,ds,settings.jev_model),'previous_b',deadline) if selected else None
    base=link_candidate.normalize(art,suppliers,aa,bb,ds);raw={'a':aa,'b':bb};p=review_facts.apply(base)
    support=facts=None
    if p['analysis_status']=='review':
        pc=review_support.payload(base,art.data,suppliers,settings.jev_model)
        if pc['questions']:
            raw['support']=client.ask(pc,'previous_support',deadline)
            support={'binding':review_policy.binding(base),'version':review_support.VERIFIER_VERSION,'response':raw['support']};p=review_facts.apply(base,support)
    if p['analysis_status']=='review':
        pd=review_facts.payload(base,art.data,suppliers,settings.jev_model)
        if pd['questions']:
            raw['facts']=client.ask(pd,'previous_facts',deadline)
            facts={'binding':review_policy.binding(base),'version':review_facts.QUESTIONS,'response':raw['facts']};p=review_facts.apply(base,support,facts)
    return p,raw


def baseline(client,art,suppliers,deadline):
    aa=client.ask(stage_a(art.data,suppliers,settings.jev_model),'baseline_a',deadline)
    selected=[s for s in suppliers if aa['answers']['linked_'+s['supplier_id']]['noul']>=POLICY['thresholds']['review_low']]
    ds=durations(art.data);bb=client.ask(stage_b(art.data,selected,ds,settings.jev_model),'baseline_b',deadline) if selected else None
    return normalize(art,suppliers,aa,bb,ds),{'a':aa,'b':bb}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');args=ap.parse_args();protocol=freeze()
    if not args.execute:print(json.dumps(protocol));return
    assert make_url(str(engine.url)).database=='radar_link_development';settings.jev_budget_limits_enabled=True
    sample=json.loads(PATH.read_text());r=json.loads(REPORT.read_text()) if REPORT.exists() else {'run':RUN,'sample_hash':protocol['sample_hash'],'results':{},'versions':candidate_engine.VERSIONS}
    assert r['sample_hash']==protocol['sample_hash']
    profiles={'baseline':baseline,'prior':previous,'candidate':candidate_engine.run}
    with Session() as db:
        ss=[s.data for s in db.scalars(select(Supplier).order_by(Supplier.id))];assert len(ss)==40
        try:
            for i,c in enumerate(sample['cases']):
                for name,fn in profiles.items():
                    key=c['case']+':'+name
                    if key in r['results']:continue
                    check_time();art=clone(db,RUN,key,c['data'],i*3+list(profiles).index(name),72)
                    client=PayloadCacheClient(db,art.id,run_key=RUN);start=time.monotonic()
                    result,raw=fn(client,art,ss,start+60);elapsed=time.monotonic()-start
                    db.add(Analysis(article_id=art.id,generation=0,request_hash=digest([RUN,key]),result=result,raw=raw,duration=elapsed,cached=client.network_requests==0));art.state=result['analysis_status'];db.commit()
                    r['results'][key]={'case':c['case'],'group':'controlled_final','reference':c['reference'],'reference_reason':c['reasoned_reference'],
                        'expected_review':c['expected_review'],'sound_must_be_false':c['sound_must_be_false'],'prediction':result,'raw':raw,'profile':name,
                        'seconds':elapsed,'new_requests':client.network_requests,'cache_stages':client.cached_stages,'cache_reuse':client.reuse_details}
                    save(REPORT,r);print(json.dumps({'completed':len(r['results']),'profile':name,'requests':client.network_requests,'review':result['analysis_status']=='review'}),flush=True)
            r['complete']=True
        except ProviderError as exc:
            record_failure(db,art,run=RUN,code=exc.code,profile={"baseline":"1.0.0","prior":"link-3.0.0-dev","candidate":candidate_engine.VERSIONS["questions"]}[name],model=settings.jev_model,seconds=time.monotonic()-start)
            r.setdefault('failures',{})[key]={'error':exc.code,'article_id':art.id,'status':'error','risk':None,'urgent':None}
            raise
        finally:
            r.update(accounting(db,RUN));r['metrics']={name:report_metrics([v for v in r['results'].values() if v['profile']==name]) for name in profiles};save(REPORT,r);assert r['requests']<=720
    print(json.dumps({'complete':r.get('complete',False),'requests':r['requests'],'retries':r['retries'],'metrics':r['metrics']}))
if __name__=='__main__':main()
