"""Cache-only regression of stored training/synthetics; outbound HTTP impossible."""
import json,time
from sqlalchemy import select,func
from sqlalchemy.engine import make_url
from app.db import Session,engine
from app.models import Supplier,Article,RequestCache,ApiCall
from app.jev import validate_response
from app.jev_transport import BoundedFanoutClient,VERSION
from app.jev_audit import CapturingClient
from app.importer import digest
from app.settings import POLICY
from app import candidate_engine,candidate_matching
from app.settings import settings
from scripts.window_common import ROOT,save
from scripts.evaluate_review_policy import invariant


class CacheOnly:
    def __init__(self,db):
        self.db=db;self.network_requests=0;self.cached_stages=[];self.reuse_details=[]
        self.run_key='cache-only-replay';self.reuse_runs=('night-joint-scope-01','night-potential-scope-02','night-final-controls-01')
    def ask(self,payload,stage,deadline):
        key=digest({'payload':payload,'questions':POLICY['question_version']})
        for k in [key]+[digest({'request':key,'run_key':r})for r in self.reuse_runs]:
            cache=self.db.get(RequestCache,k)
            if cache:
                self.cached_stages.append(stage);return validate_response(payload,cache.response)
        raise AssertionError('Missing valid stored payload for '+stage+'; no outbound request allowed')


def main():
    assert make_url(str(engine.url)).database=='radar_link_development'
    development=json.loads((ROOT/'reports/private/window-matching-potential.json').read_text());controls=json.loads((ROOT/'reports/private/window-final-evaluation.json').read_text())
    rows=list(development['results'].values())+[v for v in controls['results'].values()if v['profile']=='candidate'];assert len(rows)==60
    with Session() as db:
        before=db.scalar(select(func.count()).select_from(ApiCall));ss=[s.data for s in db.scalars(select(Supplier).order_by(Supplier.id))];reused=0
        for row in rows:
            expected=row['prediction'];art=db.get(Article,expected['article_id']);cache=CacheOnly(db);client=BoundedFanoutClient(CapturingClient(cache))
            pa=candidate_matching.stage_a(art.data,ss,settings.jev_model,art.context)
            assert row['raw']['_request_payload_hashes']['a']==digest(pa)
            result,raw=candidate_engine.run(client,art,ss,time.monotonic()+60,cached_a=row['raw']['a'])
            invariant(expected,result)
            assert expected['analysis_status']==result['analysis_status']
            assert [a['needs_review']for a in expected['assessments']]==[a['needs_review']for a in result['assessments']]
            reused+=len(cache.cached_stages)
        after=db.scalar(select(func.count()).select_from(ApiCall));assert before==after
    report={'transport':VERSION,'cases':60,'training':30,'existing_synthetics':6,'fresh_controlled':24,'new_requests':0,'cached_stages':reused,'retrieval_responses_reused_after_effective_payload_hash_check':60,'counter_before':before,'counter_after':after,'predictions_priorities_and_review_unchanged':True,'limits':'Replays valid whole-request caches. New outbound partitioning separately conserves full state/questions by tests; no new independent classifier evaluation, no held-out challenge input.'}
    save(ROOT/'reports/transport-cache-replay.json',report);print(json.dumps(report))
if __name__=='__main__':main()
