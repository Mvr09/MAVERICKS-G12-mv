"""Dedicated DB and synthetic catalog only; never imports a challenge workbook."""
import json
import pytest
import httpx
from sqlalchemy import select,func
from sqlalchemy.engine import make_url
from pydantic import SecretStr
from app.db import engine,Base,Session
from app.models import Supplier,Analysis,ApiCall
from app.analysis import process_article
from app.settings import settings
from tests.helpers import synthetic,answer
from tests.unit.test_support_contract import SUPPLIER


@pytest.mark.skipif(make_url(str(engine.url)).database!='radar_test',reason='Requires explicit isolated radar_test database')
def test_dispatch_original_decisions_and_parser_version_cache(monkeypatch):
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    monkeypatch.setattr(settings,'typesafe_api_key',SecretStr('MOCK-CREDENTIAL'))
    with Session() as db:
        db.add_all(Supplier(id=f'S{i:03}',data=dict(SUPPLIER,supplier_id=f'S{i:03}')) for i in range(1,41));db.commit()
        article=synthetic(db,'MOCK positive regional development','MOCK no threat for two days.')
        seen=[]
        def fetch(req):
            payload=json.loads(req.content);seen.append(payload)
            return httpx.Response(200,json=answer(payload,linked=('S024',),risk=.02,urgent=.02))
        transport=httpx.MockTransport(fetch)
        legacy=process_article(db,article.id,transport,profile='1.0.0')
        assert legacy['affected_supplier_ids']==['S024'] and legacy['is_risk']==legacy['urgent']=='N'
        assert len(seen)==2
        process_article(db,article.id,transport,profile='1.0.0');assert len(seen)==2
        monkeypatch.setattr('app.analysis.DURATION_VERSION','MOCK-next-parser')
        process_article(db,article.id,transport,profile='1.0.0')
        assert db.scalar(select(func.count()).select_from(Analysis))==2
        assert len(seen)==2  # Effective HTTP payload unchanged, so reuse stage cache.
        geo=process_article(db,article.id,transport,profile='geo-1.0.1',publish=False)
        assert geo['question_version']=='geo-1.0.1'
        assert (geo['affected_supplier_ids'],geo['is_risk'],geo['urgent'])==(['S024'],'N','N')
        assert len(seen)==4
        assert seen[0]['questions']==seen[2]['questions']
        assert seen[1]['questions']==seen[3]['questions']
        assert 'geography' in seen[2]['state']['suppliers'][0]
        assert db.scalar(select(func.count()).select_from(ApiCall))==4
