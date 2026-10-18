"""QA has no model/portfolio side effects and uses the real eligibility gate."""
from fastapi.testclient import TestClient
from app.main import app
from app.auth import presenter
from app.qa_audio import sample
from reference.scoring import decisions


def test_qa_is_eligible_explicit_and_has_disjoint_ids():
    s=sample()
    assert s['qa'] is True and s['id'] < 0 and abs(s['id']) < 2**53
    assert s['sound_eligible'] == decisions(**s['eligibility_fixture'])['sound_eligible'] is True
    assert s['delay_seconds']==5 and 'QA' in s['title']
    assert not {'article_id','supplier_id','incident_id'} & s.keys()


def test_qa_endpoint_denies_public_access_without_database_connection():
    with TestClient(app) as c:
        assert c.post('/api/qa/audio').status_code==401


def test_authorized_qa_does_not_call_the_provider(monkeypatch):
    monkeypatch.setattr('app.jev.JevClient.ask',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('No JEV in QA')))
    app.dependency_overrides[presenter]=lambda: object()
    try:
        with TestClient(app) as c:
            r=c.post('/api/qa/audio');assert r.status_code==202 and r.json()['sound_eligible']
    finally:app.dependency_overrides.pop(presenter,None)
