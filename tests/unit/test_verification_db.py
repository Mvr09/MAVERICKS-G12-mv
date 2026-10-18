import pytest
from sqlalchemy import select,func
from sqlalchemy.engine import make_url
from fastapi.testclient import TestClient
from app.db import Session,engine,get_db,Base
from app.models import Article,Supplier,Analysis,Draft,ApiCall
from app.main import app
from app.auth import presenter
from app.importer import digest
from tests.unit.test_support_contract import SUPPLIER
pytestmark=pytest.mark.skipif(make_url(str(engine.url)).database!='radar_test',reason='Explicit synthetic test DB only')


def test_verification_persists_source_without_incident_or_classifier_override(monkeypatch):
    Base.metadata.create_all(engine)
    with Session() as db:
        supplier=db.get(Supplier,'S024')
        if not supplier:db.add(Supplier(id='S024',data=dict(SUPPLIER,supplier_id='S024')))
        data={'news_id':'MOCK-INQUIRY','headline':'MOCK ocean delay','summary':'MOCK source facts.','source':'MOCK RSS','published_date':'2026-10-18'}
        a=Article(origin_key='MOCK-INQUIRY',context='rss',news_id='MOCK-INQUIRY',data=data,content_hash=digest(data),state='review');db.add(a);db.flush()
        result={'analysis_status':'review','question_version':'MOCK','is_risk':'N','evidence':[{'id':'e1','field':'headline','start':0,'end':len(data['headline']),'text':data['headline']}]}
        db.add(Analysis(article_id=a.id,generation=0,request_hash='MOCK-INQUIRY',result=result,raw={},duration=0));db.commit()
        before=db.scalar(select(func.count()).select_from(ApiCall))
        app.dependency_overrides[get_db]=lambda: db
        app.dependency_overrides[presenter]=lambda: object()
        payload={'article_id':a.id,'supplier_id':'S024','generation':0,'version':1,'evidence_ids':['e1'],'note':'Confirmar modo y ruta sin suponer exposición','acknowledged':True}
        try:
            with TestClient(app) as client:
                assert client.post('/api/verification-drafts',json={**payload,'generation':1}).status_code==409
                assert client.post('/api/verification-drafts',json={**payload,'acknowledged':False}).status_code==422
                assert client.post('/api/verification-drafts',json={**payload,'evidence_ids':['invented']}).status_code==409
                response=client.post('/api/verification-drafts',json=payload);assert response.status_code==201
                did=response.json()['id'];row=db.get(Draft,did)
                assert row.incident_id is None and row.article_id==a.id and row.evidence_snapshot['evidence']==result['evidence']
                assert client.get('/api/articles/'+a.id+'/drafts').json()[0]['id']==did
                assert client.patch('/api/drafts/'+did,json={'text':response.json()['text']+'\nMOCK edit'}).status_code==200
                assert client.get('/api/drafts/'+did).json()['text'].endswith('MOCK edit')
                assert db.scalar(select(func.count()).select_from(ApiCall))==before
                assert db.scalar(select(Analysis.result).where(Analysis.article_id==a.id))==result
        finally:
            app.dependency_overrides.pop(get_db,None);app.dependency_overrides.pop(presenter,None)
    with Session() as db:assert db.get(Draft,did).evidence_snapshot['generation']==0


def test_targeted_rss_enqueue_does_not_consume_another_article(monkeypatch):
    from app.queue import enqueue_rss_analysis
    from app.models import Job
    with Session() as db:
        data={'headline':'MOCK pending','summary':'MOCK','source':'MOCK','published_date':'2026-10-18'}
        aa=[Article(origin_key='MOCK-TARGET-'+str(i),context='rss',news_id='MOCK-TARGET-'+str(i),data=data,content_hash=digest(data),state='pending') for i in [1,2]]
        db.add_all(aa);db.flush();selected=[]
        monkeypatch.setattr('app.queue.reserve',lambda db,a,*args,**kw: selected.append(a.id) or True)
        jobs=enqueue_rss_analysis(db,limit=1,article_ids=[aa[1].id]);assert len(jobs)==1 and selected==[aa[1].id]
        assert db.get(Job,jobs[0]).payload['article_id']==aa[1].id
        db.rollback()
