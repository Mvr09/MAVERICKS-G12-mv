from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from app.main import app
from app.db import Session
from app.models import Supplier,Material,Article,Batch,EvaluationLabel
from app.importer import import_excel

client=TestClient(app)
def test_catalog_and_idempotent_manifest_import():
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(Supplier))==40
        assert db.scalar(select(func.count()).select_from(Material))==20
        products={p for m in db.scalars(select(Material)) for p in m.data['products']}
        assert len(products)==6
        for split,n in [('training',30),('validation',10),('test',20),('liveday',14)]:
            b=db.scalar(select(Batch).where(Batch.split==split));assert b.count==n
        b,d=import_excel(db,Path('inputs/supplier_training.xlsx').read_bytes(),'training.xlsx')
        assert d['idempotent'] is True
        assert db.scalar(select(func.count()).select_from(Article))==74

def test_public_read_and_mutation_denied():
    assert client.get('/readyz').status_code==200
    r=client.get('/api/suppliers');assert r.status_code==200;assert r.json()['total']==40
    r=client.get('/api/suppliers/S001');assert r.json()['products']
    assert client.post('/api/sources/sync').status_code==401
    assert client.post('/api/drafts',json={'supplier_id':'S001','incident_id':'fake','kind':'supplier'}).status_code==401
    assert client.get('/inputs/supplier_training.xlsx').status_code==404
    assert client.get('/.env').status_code==404
    text=client.get('/api/articles').text
    for field in ('Is_Risk','Affected_Supplier_IDs','Explanation','Event_Type'):assert field not in text

def test_session_and_csrf():
    from app.settings import settings
    with TestClient(app) as c:
        r=c.post('/api/session',json={'password':settings.admin_password.get_secret_value()})
        assert r.status_code==200
        assert 'HttpOnly' in r.headers['set-cookie'];assert 'SameSite=lax' in r.headers['set-cookie']
        assert c.get('/api/admin/config').status_code==200
        assert c.delete('/api/session').status_code==403
        assert c.delete('/api/session',headers={'x-csrf-token':r.json()['csrf'],'origin':'https://hostile.invalid'}).status_code==403
        assert c.delete('/api/session',headers={'x-csrf-token':r.json()['csrf']}).status_code==200
