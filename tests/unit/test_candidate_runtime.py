"""Candidate runtime and non-destructive generations; synthetic isolated PG only."""
from copy import deepcopy
from types import SimpleNamespace
import time
import pytest
from sqlalchemy import select,func
from sqlalchemy.engine import make_url
from app.db import engine,Base,Session
from app.models import Supplier,Incident,Alert,Draft,RequestCache
from app.payload_cache import PayloadCacheClient
from app.importer import digest
from app.settings import POLICY
from scripts.review_scenarios import cases
from tests.helpers import synthetic


def test_exact_payload_cache_survives_run_keys_without_repeating_call(monkeypatch):
    class DB:
        def __init__(self):self.rows={};self.commits=0
        def get(self,model,key):return self.rows.get(key)
        def merge(self,row):self.rows[row.id]=row
        def commit(self):self.commits+=1
    db=DB();seen=[]
    def ask(self,payload,stage,deadline):
        seen.append(payload);self.network_requests+=1
        return {'model':payload['model'],'answers':{'q':{'type':'noul','noul':.9}},'usage':{'input_tokens':1}}
    monkeypatch.setattr('app.jev.JevClient.ask',ask)
    pa={'model':'jev-1.13.0','state':{'text':'MOCK source'},'questions':{'q':{'type':'noul','instructions':'MOCK proposition'}}}
    one=PayloadCacheClient(db,'mock',run_key='one');one.ask(pa,'a',time.monotonic()+10)
    two=PayloadCacheClient(db,'mock',run_key='two');two.ask(pa,'a',time.monotonic()+10)
    assert len(seen)==1 and two.network_requests==0 and two.cached_stages==['a']
    for changed in ({**pa,'model':'MOCK-model'},{**pa,'state':{'text':'MOCK changed source'}}):
        PayloadCacheClient(db,'mock',run_key='three').ask(changed,'a',time.monotonic()+10)
    assert len(seen)==3
    # A named legacy run is reusable only when the complete effective payload matches.
    key=digest({'payload':pa,'questions':POLICY['question_version']});entry=db.rows.pop(key)
    db.rows[digest({'request':key,'run_key':'old'})]=entry
    old=PayloadCacheClient(db,'mock',reuse_runs=('old',));old.ask(pa,'a',time.monotonic()+10)
    assert len(seen)==3 and old.reuse_details[0]['source']=='old'


@pytest.mark.skipif(make_url(str(engine.url)).database!='radar_test',reason='Requires isolated radar_test')
def test_generations_keep_drafts_history_and_do_not_invent_recovery_or_reopen_manual():
    from app.reanalysis import retire_effects
    from app.incidents import reconcile
    from app.views import current,suppliers_view
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    c=cases('jev-1.13.0')[0]
    with Session() as db:
        db.add(Supplier(id='QA901',data=c['suppliers'][0]));db.commit()
        article=synthetic(db,c['data']['headline'],c['data']['summary'])
        result=deepcopy(c['prediction']);result['article_id']=article.id
        result['analysis_profile']='MOCK-old';result['assessments'][0]['needs_review']=False
        result['assessments'][0]['review_reasons']=[]
        reconcile(db,article,result);db.commit();inc=db.scalar(select(Incident));old_priority=inc.priority
        draft=Draft(supplier_id='QA901',incident_id=inc.id,kind='supplier',text='MOCK edited buyer draft',context_hash='old')
        db.add(draft);db.commit();did=draft.id
        # Scheduling/failure does not retire anything. Publication of a new N does.
        article.generation=1;article.state='error';db.commit()
        assert inc.priority==old_priority and current(inc)['generation']==0
        no=deepcopy(result);no['is_risk']='N';no['urgent']='N';no['affected_supplier_ids']=[];no['assessments']=[]
        retire_effects(db,article,no);reconcile(db,article,no);db.commit()
        assert inc.state=='superseded' and inc.priority==0 and current(inc)=={}
        assert db.get(Draft,did).text=='MOCK edited buyer draft'
        assert all(h['superseded'] for h in inc.history)
        assert all(a.data['state']=='superseded' and not a.data['sound_eligible'] for a in db.scalars(select(Alert)))
        assert suppliers_view(db,'exercise','batch:'+article.batch_id)[0]['incident_count']==0
        # Explicit same-source new generation can replace old inference without deleting it.
        article.generation=2;new=deepcopy(result);new['analysis_profile']='MOCK-candidate'
        retire_effects(db,article,new);reconcile(db,article,new);db.commit()
        assert inc.state=='active' and len(inc.history)==2
        assert current(inc)['generation']==2 and current(inc)['analysis_profile']=='MOCK-candidate'
        assert db.scalar(select(func.count()).select_from(Alert))==2
        assert db.get(Draft,did).text=='MOCK edited buyer draft'
        # Duplicate delivery creates no second alert, then explicit manual closure wins.
        reconcile(db,article,new);db.commit();assert len(inc.history)==2
        inc.state='resolved';inc.priority=0;inc.history=[*inc.history,{'manual':True,'at':'2099-01-01T00:00:00+00:00'}];db.commit()
        article.generation=3;retire_effects(db,article,new);reconcile(db,article,new);db.commit()
        assert inc.state=='resolved' and inc.priority==0

@pytest.mark.skipif(make_url(str(engine.url)).database!='radar_test',reason='Requires isolated radar_test')
def test_candidate_pipeline_explicit_versions_cache_and_legacy_separation(monkeypatch):
    import json,httpx
    from pydantic import SecretStr
    from app.analysis import process_article
    from app.models import Analysis,ApiCall
    from app.settings import settings
    from tests.helpers import answer
    from tests.unit.test_support_contract import SUPPLIER
    from app.candidate_engine import PROFILE,VERSIONS
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    monkeypatch.setattr(settings,'typesafe_api_key',SecretStr('MOCK-ONLY'))
    with Session() as db:
        db.add_all(Supplier(id=f'S{i:03}',data=dict(SUPPLIER,supplier_id=f'S{i:03}')) for i in range(1,41));db.commit()
        article=synthetic(db,'MOCK S024 expands capacity','MOCK positive improvement; supplies continue.')
        article.data={**article.data,**{k:'PROTECTED-PAYLOAD-SENTINEL' for k in ('Is_Risk','Urgent','Affected_Supplier_IDs','Event_Type','Explanation')}};db.commit()
        seen=[]
        def fetch(req):
            p=json.loads(req.content);seen.append(p);r=answer(p,linked=('S024',),risk=.02,urgent=.02)
            for k,q in p['questions'].items():
                a=r['answers'][k];sid=k.rsplit('_',1)[-1]
                if q['type']=='noul':
                    if k.startswith(('candidate_','identity_','area_','operation_','joint_exposure_')):a['noul']=.95 if sid=='S024' else .02
                    elif k.startswith(('inclusion_support_','exclusion_support_','risk_support_')):a['noul']=.96
                elif q['type']=='choice':
                    value='positive' if k.startswith('impact_state_') or k=='event_state' else 'none' if k.startswith(('link_evidence_','duration_')) else 'no_adverse_effect' if k.startswith('impact_scope_') else 'e1' if k.startswith('evidence_') else next(iter(q['criteria']))
                    if value not in q['criteria']:value=next(iter(q['criteria']))
                    a['choice']=value;a['probabilities']={x:float(x==value) for x in q['criteria']}
            return httpx.Response(200,json=r)
        transport=httpx.MockTransport(fetch)
        result=process_article(db,article.id,transport,profile=PROFILE)
        assert result['analysis_status']!='error' and result['analysis_profile']==PROFILE
        assert result['analysis_versions']['review']==VERSIONS['review']
        assert result['is_risk']==result['urgent']=='N' and result['affected_supplier_ids']==['S024']
        n=len(seen);process_article(db,article.id,transport,profile=PROFILE);assert len(seen)==n
        stored=db.scalar(select(Analysis));assert stored.raw['_versions']['matching']==VERSIONS['matching']
        assert db.scalar(select(func.count()).select_from(ApiCall))==n
        assert stored.raw['_effective_payloads']['b']==seen[1]
        assert 'PROTECTED-PAYLOAD-SENTINEL' not in json.dumps(seen)
        assert 'MOCK-ONLY' not in json.dumps(stored.raw['_effective_payloads'])
        assert 'joint_exposure_S024' in seen[1]['questions']
        assert 'linked_S024' not in seen[0]['questions']  # broad candidate retrieval is identity/exposure

@pytest.mark.skipif(make_url(str(engine.url)).database!='radar_test',reason='Requires isolated radar_test')
def test_presenter_opt_in_queue_and_mixed_batch_guard(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import presenter
    from app.db import get_db
    from app.models import Job,Analysis,ApiCall
    from app.reanalysis import enqueue_article
    from app.queue import enqueue_batch
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with Session() as db:
        article=synthetic(db,'MOCK opt-in','MOCK no paid request')
        monkeypatch.setattr('app.main.require_current_worker',lambda db:None)
        monkeypatch.setattr('app.queue.reserve',lambda *a,**kw:True)
        app.dependency_overrides[get_db]=lambda:db
        try:
            with TestClient(app) as client:
                url='/api/articles/'+article.id+'/analyze'
                assert client.post(url,json={'analysis_profile':'radar-1.0.0-candidate'}).status_code==401
                assert client.get('/api/model/operational-candidate').status_code==401
                app.dependency_overrides[presenter]=lambda:object()
                assert client.post(url,json={'analysis_profile':'unknown'}).status_code==422
                response=client.post(url,json={'analysis_profile':'radar-1.0.0-candidate'});assert response.status_code==202
                j=db.get(Job,response.json()['job_ids'][0]);assert j.payload['analysis_profile']=='radar-1.0.0-candidate'
                assert response.json()['maximum_requests']==36 and article.generation==0
                assert client.post(url,json={'analysis_profile':'radar-1.0.0-candidate'}).status_code==409
                assert db.scalar(select(func.count()).select_from(ApiCall))==0
                assert client.get('/api/model/operational-candidate').status_code==200
            j.state='done';article.state='done'
            db.add(Analysis(article_id=article.id,generation=0,request_hash='MOCK-OLD-PROFILE',result={'analysis_status':'done','question_version':'1.0.0'},raw={},duration=0));db.commit()
            with pytest.raises(ValueError,match='otro perfil'):enqueue_batch(db,article.batch_id,'radar-1.0.0-candidate')
            j2=enqueue_article(db,article.id,'radar-1.0.0-candidate');assert article.generation==1 and j2.payload['generation']==1
        finally:
            app.dependency_overrides.pop(get_db,None);app.dependency_overrides.pop(presenter,None)


@pytest.mark.skipif(make_url(str(engine.url)).database!='radar_test',reason='Requires isolated radar_test')
def test_failed_replacement_publication_rolls_back_effects(monkeypatch):
    from app.analysis import process_article
    from app.incidents import reconcile
    from app.views import current
    from tests.unit.test_support_contract import SUPPLIER
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    c=cases('jev-1.13.0')[0]
    with Session() as db:
        db.add_all(Supplier(id=f'S{i:03}',data=dict(SUPPLIER,supplier_id=f'S{i:03}')) for i in range(1,41))
        db.add(Supplier(id='QA901',data=c['suppliers'][0]));db.commit()
        article=synthetic(db,c['data']['headline'],c['data']['summary']);result=deepcopy(c['prediction']);result['article_id']=article.id
        reconcile(db,article,result);db.commit();inc=db.scalar(select(Incident));old=deepcopy(inc.history)
        # Pipeline requires precisely40 identities. Reuse a real synthetic ID for
        # the incident after dropping a redundant synthetic catalog row.
        db.delete(db.get(Supplier,'S040'));article.generation=1;db.commit()
        monkeypatch.setattr('app.candidate_engine.run',lambda *a,**kw:(deepcopy(result),{}))
        def fail(*args):raise ValueError('MOCK failed replacement')
        monkeypatch.setattr('app.incidents.reconcile',fail)
        out=process_article(db,article.id,profile='radar-1.0.0-candidate')
        db.refresh(inc)
        assert out['analysis_status']=='error' and inc.history==old and inc.state=='active'
        assert current(inc)['generation']==0


@pytest.mark.skipif(make_url(str(engine.url)).database!='radar_test',reason='Requires isolated radar_test')
def test_rss_technical_daily_quota_remains_when_local_money_limits_disabled(monkeypatch):
    from app.models import Article,RssDailyUsage
    from app.queue import reserve
    from app.settings import settings,RSS
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    monkeypatch.setattr(settings,'jev_budget_limits_enabled',False)
    with Session() as db:
        db.add_all(RssDailyUsage(id='MOCK-DAY-'+str(i)) for i in range(RSS['daily_analysis_budget']));db.commit()
        data={'headline':'MOCK RSS','summary':'MOCK technical quota','published_date':'2026-10-18'}
        article=Article(origin_key='MOCK-QUOTA',context='rss',news_id='MOCK-QUOTA',data=data,content_hash=digest(data));db.add(article);db.flush()
        assert reserve(db,article,'rss',manual_rss=True) is False

@pytest.mark.skipif(make_url(str(engine.url)).database!='radar_test',reason='Requires isolated radar_test')
def test_supplier_view_distinguishes_no_link_doubt_and_superseded_from_recovery():
    from app.views import suppliers_view
    from app.models import Analysis
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    c=cases('jev-1.13.0')[0]
    with Session() as db:
        db.add(Supplier(id='QA901',data=c['suppliers'][0]));db.commit()
        article=synthetic(db,c['data']['headline'],c['data']['summary'])
        assert suppliers_view(db)[0]['status']=='pending'
        result={**deepcopy(c['prediction']),'article_id':article.id,'analysis_status':'done','is_risk':'N','urgent':'N','affected_supplier_ids':[],'assessments':[],'review_details':[],'review_reasons':[]}
        analysis=Analysis(article_id=article.id,generation=0,request_hash='MOCK-VIEW',result=result,raw={},duration=0);db.add(analysis);article.state='done';db.commit()
        s=suppliers_view(db)[0];assert s['status']=='unlinked' and s['priority'] is None and not s['needs_review']
        uncertain=deepcopy(c['prediction']['assessments'][0]);uncertain.update(p_link=.4,needs_review=True)
        analysis.result={**result,'analysis_status':'review','assessments':[uncertain],'review_details':[{'supplier_id':'QA901','code':'link_ambiguous','relevance':'association','requires_review':True}]};db.commit()
        s=suppliers_view(db)[0];assert s['status']=='review' and s['needs_review']
        analysis.result=result
        db.add(Incident(context='exercise',supplier_id='QA901',event_type='fire_incident',signature='MOCK-SUPERSEDED',state='superseded',priority=0,historical_priority=70,event_date=article.data['published_date'],history=[{'article_id':article.id,'superseded':True,'assessment':uncertain}]))
        db.commit();s=suppliers_view(db)[0]
        assert s['status']=='superseded' and s['incident_count']==0 and 'recuperado' not in s['reason'].lower()

@pytest.mark.skipif(make_url(str(engine.url)).database!='radar_test',reason='Requires isolated radar_test')
def test_job_progress_uses_its_generation_while_metrics_keep_consumption_history():
    from app.models import Analysis,ApiCall,Job
    from app.main import job,batches
    from app.model_metrics import model_metrics
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    c=cases('jev-1.13.0')[0]
    with Session() as db:
        article=synthetic(db,c['data']['headline'],c['data']['summary']);article.generation=1;article.state='done'
        result={**deepcopy(c['prediction']),'article_id':article.id,'analysis_versions':{'review':'review-1.2.0'},'analysis_profile':'radar-1.0.0-candidate','question_version':'link-3.3.0'}
        db.add(Analysis(article_id=article.id,generation=1,request_hash='MOCK-GEN-METRICS',result=result,raw={},duration=.1))
        for key,stage in [('','a'),('','b'),('','candidate_support'),(article.id+':generation:1','a'),(article.id+':generation:1','b')]:
            db.add(ApiCall(article_id=article.id,run_key=key,stage=stage,attempt=1,model='jev-1.13.0',status=200,usage={'input_tokens':1},duration=.01))
        j=Job(key='analysis:'+article.id+':g1',kind='analysis',state='running',payload={'article_id':article.id,'generation':1,'analysis_profile':'radar-1.0.0-candidate'});db.add(j);db.commit()
        progress=job(j.id,db);assert progress['network_requests']==2 and progress['last_completed_step']=='Exposición, riesgo y urgencia'
        from app.main import article as article_detail
        assert article_detail(article.id,db)['analysis_job']['id']==j.id
        metrics=model_metrics(db,'exercise');assert metrics['execution']['requests']==5
        assert metrics['execution']['versions'][0]['review']=='review-1.2.0'
        rows=batches(db);assert not rows[0]['mixed_profiles'] and rows[0]['analysis_profiles'][0]['questions']=='link-3.3.0'
