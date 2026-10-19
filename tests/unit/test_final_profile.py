"""Final handoff: frozen components, read-only metrics and cache isolation. Synthetic only."""
import time, uuid
from datetime import datetime,timedelta,timezone
import pytest
from sqlalchemy.engine import make_url
from app.profiles import DEFAULT_PROFILE, CANDIDATE_PROFILE, profile_snapshot, FINAL_COMPONENTS
from app.main import AnalysisSelection, ManualRssAnalysis, PendingSelection
from app.queue import analysis_payload
from types import SimpleNamespace


def test_all_new_entry_defaults_and_explicit_rollback_are_consistent():
    assert DEFAULT_PROFILE==CANDIDATE_PROFILE
    assert profile_snapshot(DEFAULT_PROFILE)==FINAL_COMPONENTS
    assert AnalysisSelection().analysis_profile==ManualRssAnalysis(limit=1).analysis_profile==DEFAULT_PROFILE
    assert PendingSelection(request_id=uuid.uuid4(),article_ids=['MOCK'],context='rss').analysis_profile==DEFAULT_PROFILE
    for context in ('exercise','rss'):
        job=analysis_payload(SimpleNamespace(id='MOCK',generation=0,context=context))
        assert job['analysis_profile']==DEFAULT_PROFILE and job['profile_snapshot']==FINAL_COMPONENTS
        old=analysis_payload(SimpleNamespace(id='MOCK',generation=0,context=context),'1.0.0')
        assert old['analysis_profile']=='1.0.0' and old['profile_snapshot']['profile']=='1.0.0'
    assert AnalysisSelection(analysis_profile='1.0.0').analysis_profile=='1.0.0'


def test_effective_payload_cache_is_namespaced_by_full_profile(monkeypatch):
    from app.payload_cache import PayloadCacheClient
    class DB:
        def __init__(self):self.rows={}
        def get(self,m,key):return self.rows.get(key)
        def merge(self,row):self.rows[row.id]=row
        def commit(self):pass
    db=DB();seen=[]
    def ask(self,payload,stage,deadline):
        seen.append(self.cache_namespace)
        return {'model':payload['model'],'answers':{'q':{'type':'noul','noul':.9}},'usage':{'input_tokens':1}}
    monkeypatch.setattr('app.jev.JevClient.ask',ask)
    p={'model':'jev-1.13.0','state':{'text':'MOCK'},'questions':{'q':{'type':'noul','instructions':'MOCK'}}}
    for ns in ('legacy','final','final','final-changed'):
        PayloadCacheClient(db,'MOCK',cache_namespace=ns).ask(p,'a',time.monotonic()+10)
    assert seen==['legacy','final','final-changed']


@pytest.mark.skipif(make_url(str(__import__('app.db',fromlist=['engine']).engine.url)).database!='radar_test',reason='Synthetic test DB only')
def test_final_report_recalculates_counts_keeps_review_and_separates_time():
    from app.db import Base,engine,Session
    from app.models import EvaluationCampaign,CampaignRun
    from app.final_model import FINAL,report
    Base.metadata.create_all(engine)
    with Session() as db:
        begin=datetime(2026,10,19,tzinfo=timezone.utc)
        c=EvaluationCampaign(id=FINAL['campaign_id'],name='MOCK known campaign',state='complete',freeze={
          'hash':FINAL['freeze_hash'],'versions':{CANDIDATE_PROFILE:FINAL_COMPONENTS},'created_commit':'MOCK','infrastructure':{'service':'MOCK local','python':'3.12'}},started_at=begin,completed_at=begin+timedelta(seconds=20))
        db.add(c);db.flush()
        for i in range(5):
            ref={'Is_Risk':'Y' if i!=2 else 'N','Urgent':'N','Affected_Supplier_IDs':f'S00{i+1}' if i!=2 else ''}
            result={'is_risk':ref['Is_Risk'],'urgent':'N','affected_supplier_ids':[('S004' if i==3 else f'S00{i+1}')] if i!=2 else []}
            if i==3:result['affected_supplier_ids']=['S099']
            state='error' if i==4 else 'review' if i==0 else 'done'
            db.add(CampaignRun(campaign_id=c.id,profile=CANDIDATE_PROFILE,input_key=f'MOCK-{i}',split='training' if i<3 else 'validation',source={'news_id':f'MOCK{i}'},reference=ref,state=state,result=result if state!='error' else {'is_risk':None},started_at=begin+timedelta(seconds=i*2),completed_at=begin+timedelta(seconds=i*2+3),audit={'queued_at':begin.isoformat(),'new_requests':2,'_cache_stages':[],'calls':[{'status':200,'usage':{'input_tokens':10,'output_tokens':2}}]}))
        db.flush()
        try:
            r=report(db,'labelled');q=r['quality']
            assert q['total']==5 and q['completed']==4 and q['errors']==1
            assert q['quality']['suppliers']['tp']==2 and q['quality']['suppliers']['fp']==q['quality']['suppliers']['fn']==1
            assert q['quality']['suppliers']['f1']==pytest.approx(2/3)
            assert q['quality']['n']==4 and q['review']==1
            assert r['performance']['fresh']['mean']==3 and r['performance']['fresh']['n']==4
            assert r['performance']['tokens_reported']['mean']==12
            assert report(db,'training')['quality']['quality']['n']==3
            assert report(db,'validation')['quality']['errors']==1
            # Endpoint DTO never returns per-item references/payloads.
            assert 'reference' not in r and 'rows' not in r
        finally:db.rollback()


def test_queued_auxiliary_comparisons_preserve_legacy_and_new_snapshot(monkeypatch):
    from app.comparison import process_comparison
    recorded=[]
    def process(db, aid, **kw):
        recorded.append(kw)
        return {'analysis_status':'done','is_risk':'N','urgent':'N','affected_supplier_ids':[], 'event_type':'none','review_reasons':[],'assessments':[]}
    monkeypatch.setattr('app.analysis.process_article',process)
    class DB:
        def __init__(self,payload):
            self.row=SimpleNamespace(state='queued',article_id='MOCK',ballots=[],summary={})
            self.job=SimpleNamespace(payload=payload)
        def get(self,*a):return self.row
        def scalar(self,*a):return self.job
        def commit(self):pass
    for payload,expected in [({},'1.0.0'),({'analysis_profile':DEFAULT_PROFILE,'profile_snapshot':FINAL_COMPONENTS},DEFAULT_PROFILE)]:
        recorded.clear();r=process_comparison(DB(payload),'MOCK')
        assert r.state=='done' and len(recorded)==3
        assert all(k['profile']==expected and k['publish'] is False for k in recorded)
        assert all(k['profile_snapshot']==payload.get('profile_snapshot') for k in recorded)
    recorded.clear();db=DB({'analysis_profile':DEFAULT_PROFILE,'profile_snapshot':{'model':'WRONG-MOCK'}})
    assert process_comparison(db,'MOCK').state=='error' and not recorded
