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
