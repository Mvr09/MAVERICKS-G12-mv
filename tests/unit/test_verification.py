from types import SimpleNamespace
from copy import deepcopy
import pytest
from app.verification import prepare
from tests.unit.test_support_contract import SUPPLIER


def sample():
    text='Container services face delays.'
    article=SimpleNamespace(id='MOCK',context='rss',generation=0,version=1,data={'headline':text,'summary':'','source':'MOCK RSS','published_date':'2026-10-18','url':'https://example.org/news'})
    supplier=SimpleNamespace(id=SUPPLIER['supplier_id'],data=SUPPLIER)
    result={'analysis_status':'review','question_version':'MOCK','evidence':[{'id':'e1','field':'headline','start':0,'end':len(text),'text':text}],'is_risk':'N'}
    return article,supplier,result


def test_inquiry_preserves_literal_fact_and_uncertainty_without_changing_model():
    a,s,r=sample();original=deepcopy(r)
    text,snapshot,key=prepare(a,s,r,['e1'],'Confirmar si utiliza este servicio')
    assert r==original and r['analysis_status']=='review'
    assert snapshot['evidence'][0]['text'] in text and snapshot['exposure_status']=='potential_unconfirmed'
    assert 'No se ha confirmado afectación individual' in text and 'no valida la clasificación' in text
    assert snapshot['buyer_hypothesis']=='Confirmar si utiliza este servicio' and key


@pytest.mark.parametrize('kind',['forged','pending','span'])
def test_inquiry_rejects_missing_analysis_or_invalid_source(kind):
    a,s,r=sample();ids=['e1']
    if kind=='forged':ids=['invented']
    if kind=='pending':r['analysis_status']='error'
    if kind=='span':r['evidence'][0]['text']='INVENTED'
    with pytest.raises(ValueError):prepare(a,s,r,ids,'Confirmar exposición')


def test_inquiry_endpoints_deny_anonymous():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        assert client.post('/api/verification-drafts',json={}).status_code==401
        assert client.get('/api/articles/MOCK/drafts').status_code==401
        assert client.get('/api/drafts/MOCK').status_code==401
        assert client.get('/api/model/candidates').status_code==401
