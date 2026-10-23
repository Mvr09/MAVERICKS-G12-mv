"""Exact-origin framing/session contract; synthetic in-memory sessions, no APIs/PG."""
from datetime import timedelta
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from app.main import app
from app.db import get_db
from app.settings import settings
from app.embedding import PRESENTATION_ORIGIN, BASE_CSP, set_session_cookies
from app.models import now
from starlette.responses import Response

BASE='https://mavericks-g12-mv-production.up.railway.app'

class MemorySessions:
    def __init__(self):self.rows={}
    def get(self,model,key):return self.rows.get((model,key))
    def add(self,row):self.rows[(type(row),row.id)]=row
    def commit(self):pass
    def delete(self,row):self.rows.pop((type(row),row.id),None)

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings,'app_base_url',BASE)
    monkeypatch.setattr(settings,'admin_password',SecretStr('MOCK-iframe-password'))
    monkeypatch.setattr(settings,'session_secret',SecretStr('MOCK-session-signing-key-only-tests'))
    db=MemorySessions();app.dependency_overrides[get_db]=lambda:db
    with TestClient(app,base_url=BASE,raise_server_exceptions=False) as c:yield c
    app.dependency_overrides.clear()

def authenticate(client,embedded=True):
    return client.post('/api/session',json={'password':'MOCK-iframe-password'},headers={'Origin':BASE,**({'X-Radar-Embed':'1'} if embedded else {})})

def test_only_navigable_html_permits_exact_presentation_origin(client):
    for path in ['/?context=exercise','/noticias','/proveedores/S003','/ruta-no-existente']:
        r=client.get(path);assert r.status_code==200
        assert 'text/html' in r.headers['content-type']
        assert 'x-frame-options' not in r.headers
        assert len(r.headers.get_list('content-security-policy'))==1
        assert r.headers['content-security-policy']==BASE_CSP.replace("frame-ancestors 'none'",f"frame-ancestors 'self' {PRESENTATION_ORIGIN}")
    for path in ['/api/session','/api/no-such-api','/inputs/private.xlsx']:
        r=client.get(path)
        assert r.headers['x-frame-options']=='DENY'
        assert "frame-ancestors 'none'" in r.headers['content-security-policy']
        assert 'access-control-allow-origin' not in r.headers
    from starlette.responses import RedirectResponse
    from app.embedding import apply_framing_policy
    r=RedirectResponse('/noticias')
    r.headers['X-Frame-Options']='DENY'
    apply_framing_policy(SimpleNamespace(url=SimpleNamespace(path='/entry')),r)
    assert r.status_code==307 and 'x-frame-options' not in r.headers

def test_secure_partitioned_session_and_reload_logout(client):
    r=authenticate(client);assert r.status_code==200
    cookies=r.headers.get_list('set-cookie');assert len(cookies)==2
    for c in cookies:
        assert 'HttpOnly' in c and 'Secure' in c and 'samesite=none' in c.lower() and 'Path=/' in c and 'Domain=' not in c
    embed=next(c for c in cookies if c.startswith('radar_embed_session='))
    assert '; Partitioned' in embed
    # Exercise partitioned cookie alone; regular cookie may be blocked by browser.
    client.cookies.delete('radar_session')
    state=client.get('/api/session').json();assert state['presenter'] is True
    assert client.get('/api/session').json()['presenter'] is True
    token=state['csrf']
    r=client.delete('/api/session',headers={'Origin':BASE,'X-CSRF-Token':token})
    assert r.status_code==200
    assert any('Partitioned' in c and 'Max-Age=0' in c for c in r.headers.get_list('set-cookie'))
    assert client.get('/api/session').json()['presenter'] is False

def test_embed_permission_does_not_grant_api_cors_or_bypass_csrf(client):
    assert client.post('/api/qa/audio',headers={'Origin':BASE}).status_code==401
    assert authenticate(client).status_code==200
    token=client.get('/api/session').json()['csrf']
    assert client.post('/api/qa/audio',headers={'Origin':BASE}).status_code==403
    assert client.post('/api/qa/audio',headers={'Origin':BASE,'X-CSRF-Token':'WRONG'}).status_code==403
    assert client.post('/api/qa/audio',headers={'Origin':PRESENTATION_ORIGIN,'X-CSRF-Token':token}).status_code==403
    good=client.post('/api/qa/audio',headers={'Origin':BASE,'X-CSRF-Token':token})
    assert good.status_code==202 and good.json()['delay_seconds']==5
    assert client.options('/api/session',headers={'Origin':PRESENTATION_ORIGIN,'Access-Control-Request-Method':'POST'}).headers.get('access-control-allow-origin') is None

def test_login_origin_is_still_same_origin_only(client):
    for origin in [PRESENTATION_ORIGIN,'https://untrusted.example']:
        assert client.post('/api/session',json={'password':'MOCK-iframe-password'},headers={'Origin':origin}).status_code==403
    r=authenticate(client,embedded=False)
    assert len(r.headers.get_list('set-cookie'))==1

def test_http_development_never_sets_insecure_samesite_none(monkeypatch):
    monkeypatch.setattr(settings,'app_base_url','http://localhost:8000')
    r=Response();set_session_cookies(r,'MOCK-signed',embedded=True)
    cookies=r.headers.getlist('set-cookie')
    assert len(cookies)==1 and 'SameSite=lax' in cookies[0] and 'Partitioned' not in cookies[0]
