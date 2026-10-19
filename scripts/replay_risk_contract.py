"""Offline serialization regression for a rejected trial; no outbound client."""
import json,time,hashlib
from sqlalchemy import select,func
from sqlalchemy.engine import make_url
from app.db import Session,engine
from app.models import Supplier,Article,ApiCall
from app.settings import settings
from app.importer import digest
from app import candidate_matching
from app.duration import durations
from scripts.replay_transport import CacheOnly
from scripts import risk_engine_current
from scripts.evaluate_review_policy import invariant
from scripts.window_common import ROOT,save


def main():
 assert make_url(str(engine.url)).database=='radar_link_development'
 r=json.loads((ROOT/'reports/private/window-risk-current.json').read_text());assert r['complete'] and len(r['results'])==60
 with Session() as db:
  before=db.scalar(select(func.count()).select_from(ApiCall));ss=[s.data for s in db.scalars(select(Supplier).order_by(Supplier.id))];stages=0
  for row in r['results'].values():
   expected=row['prediction'];art=db.get(Article,expected['article_id']);raw=row['raw'];cache=CacheOnly(db)
   cache.reuse_runs+=('night-risk-focus-01','night-risk-current-02')
   pa=candidate_matching.stage_a(art.data,ss,settings.jev_model);assert digest(pa)==raw['_request_payload_hashes']['a']
   selected=candidate_matching.select_candidates(art.data,ss,raw['a']);pb=candidate_matching.stage_b(art.data,selected,durations(art.data),settings.jev_model)
   assert (digest(pb) if selected else None)==raw['_request_payload_hashes']['b']
   actual,_=risk_engine_current.run(cache,art,ss,time.monotonic()+60,cached_a=raw['a'],cached_b=raw['b'])
   invariant(expected,actual);assert actual['analysis_status']==expected['analysis_status'];assert actual['review_reasons']==expected['review_reasons'];stages+=len(cache.cached_stages)
  after=db.scalar(select(func.count()).select_from(ApiCall));assert before==after
 report={'cases':60,'new_requests':0,'cached_stages':stages,'counter_before':before,'counter_after':after,'predictions_priorities_and_review_unchanged':True,'correction':'Use existing factual_basis_check resolution enum for the hypothetical resolved impact path; supported by strict schema unit test. No such resolution was activated in the recorded trial. Not a classifier improvement, not adopted.', 'post_run_source_hash':hashlib.sha256((ROOT/'app/candidate_review_focus.py').read_bytes()).hexdigest(),'pre_run_source_hash':r['protocol']['files']['app/candidate_review_focus.py']}
 save(ROOT/'reports/risk-contract-replay.json',report);print(json.dumps(report))
if __name__=='__main__':main()
