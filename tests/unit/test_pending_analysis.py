"""Synthetic queue visibility only; never loads challenge inputs or calls JEV."""
import json
import uuid
import pytest
from sqlalchemy.engine import make_url
from app.db import Session, engine, Base
from app.models import Article, Job
from app.views import articles_view

pytestmark = pytest.mark.skipif(make_url(str(engine.url)).database != 'radar_test', reason='Isolated synthetic DB only')


def test_pending_list_keeps_active_job_after_reload_without_private_payload():
    Base.metadata.create_all(engine)
    with Session() as db:
        key = 'MOCK-PENDING-' + str(uuid.uuid4())
        a = Article(origin_key=key, context='exercise', news_id=key, content_hash=key,
                    data={'headline':'MOCK pending input','source':'MOCK','summary':'MOCK'}, state='pending')
        db.add(a); db.flush()
        job = Job(key=key, kind='analysis', state='running',
                  payload={'article_id':a.id,'analysis_profile':'1.0.0','private_context':'PRIVATE-MOCK'})
        db.add(job); db.flush()
        try:
            result = next(r for r in articles_view(db,'exercise') if r['id'] == a.id)
            assert result['state'] == 'pending'
            assert result['analysis_job'] == {'id':job.id,'state':'running','analysis_profile':'1.0.0'}
            assert 'PRIVATE-MOCK' not in json.dumps(result, default=str)
            job.state = 'done'; db.flush()
            again = next(r for r in articles_view(db,'exercise') if r['id'] == a.id)
            assert again['analysis_job'] is None
        finally:
            db.rollback()


def test_all_pending_selection_is_durable_idempotent_and_counts_failures(monkeypatch):
    from app.pending_selection import create, view, KIND
    Base.metadata.create_all(engine)
    with Session() as db:
        prefix = 'MOCK-ALL-' + str(uuid.uuid4())
        articles = [Article(origin_key=f'{prefix}-{i}', context='rss', news_id=f'{prefix}-{i}', content_hash=prefix,
                    data={'headline':f'MOCK {i}','source':'MOCK'}, state='pending' if i < 12 else 'done') for i in range(13)]
        db.add_all(articles); db.flush()
        active = Job(key=prefix,kind='analysis',state='running',payload={'article_id':articles[0].id})
        db.add(active); db.flush()
        calls=[]
        def enqueue(db, aid, profile):
            calls.append(aid)
            if aid == articles[3].id:
                raise ValueError('MOCK límite técnico: no reservado')
            job=Job(key=prefix+aid,kind='analysis',payload={'article_id':aid,'analysis_profile':profile},state='queued')
            db.add(job);db.flush();return job
        monkeypatch.setattr('app.pending_selection.enqueue_article',enqueue)
        request_id=uuid.uuid4(); ids=[a.id for a in articles]
        try:
            group=create(db,request_id,ids,'rss','1.0.0')
            assert group['id']==str(request_id) and group['total']==13
            assert group['counts']==dict(done=0,queued=10,running=1,error=1,skipped=1)
            assert group['finished']==2 and len(calls)==11
            manifest=db.get(Job,group['id']);assert manifest.kind==KIND and manifest.state=='done'
            again=create(db,request_id,ids,'rss','1.0.0')
            assert len(calls)==11 and again==group
            for item in group['items']:
                if item['job_id']:db.get(Job,item['job_id']).state='done'
            # Analysed but reviewed is still a completed analysis, never a pending job.
            articles[1].state='review';db.flush();db.expire(manifest)
            final=view(db,db.get(Job,str(request_id)))
            assert final['counts']['done']==11 and final['finished']==13
            assert final['state']=='partial' and final['counts']['error']==1
            assert articles[3].state=='pending' and articles[12].state=='done'
            with pytest.raises(ValueError,match='otra selección'):
                create(db,request_id,ids[:-1],'rss','1.0.0')
        finally:db.rollback()


def test_pending_selection_rejects_duplicates_and_cross_context(monkeypatch):
    from app.pending_selection import create
    Base.metadata.create_all(engine)
    with Session() as db:
        key='MOCK-CONTEXT-'+str(uuid.uuid4())
        a=Article(origin_key=key,context='exercise',news_id=key,content_hash=key,data={},state='pending')
        db.add(a);db.flush()
        monkeypatch.setattr('app.pending_selection.enqueue_article',lambda *args:pytest.fail('Must not enqueue'))
        try:
            with pytest.raises(ValueError,match='repetidas'):create(db,uuid.uuid4(),[a.id,a.id],'exercise','1.0.0')
            with pytest.raises(ValueError,match='único contexto'):create(db,uuid.uuid4(),[a.id],'rss','1.0.0')
        finally:db.rollback()


def test_pending_progress_api_requires_presenter(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import get_db
    Base.metadata.create_all(engine)
    with Session() as db:
        app.dependency_overrides[get_db]=lambda:db
        monkeypatch.setattr('app.main.require_current_worker',lambda db:pytest.fail('Unauthorized request reached worker'))
        try:
            with TestClient(app) as client:
                rid=str(uuid.uuid4())
                assert client.get('/api/analysis/pending/'+rid).status_code==401
                assert client.post('/api/analysis/pending',json={'request_id':rid,'article_ids':['MOCK'],'context':'rss'}).status_code==401
        finally:app.dependency_overrides.pop(get_db,None)
