from copy import deepcopy
import time,json
from types import SimpleNamespace
import httpx,pytest
from sqlalchemy import select,func
from sqlalchemy.engine import make_url
from pydantic import SecretStr
from app.enrichment import EditorialParser
from app.jev_transport import partition,encoded_size,BoundedFanoutClient
from app.jev import ProviderError,validate_response,safe_http_diagnostic
from app.jev_audit import CapturingClient
from app.models import RequestCache
from app.importer import digest
from app.settings import POLICY
from tests.helpers import answer


def test_editorial_container_does_not_collect_ticker_or_many_related_cards():
    body='MOCK main article: a transport route faces a limited capacity reduction. '*8
    preview='MOCK unrelated preview about a different company. '*3
    html='<main><div class="ad-box"><p>MOCK ticker should not become article evidence.</p></div><article><p>'+body+'</p></article>'
    html+=''.join('<article><div class="entry-content"><h3>MOCK related title</h3><p>'+preview+'</p></div></article>' for _ in range(20))+'</main>'
    p=EditorialParser();p.feed(html);text,method=p.extract()
    assert text==body.strip() and 'preview'not in text and 'ticker'not in text
    assert method=='editorial_article_container'
    # A proper body inside a primary article wins over navigation, without
    # combining it with another article's same-named entry-content container.
    p=EditorialParser();p.feed('<main><article><div class="entry-content"><p>'+body+'</p></div></article><article><div class="entry-content"><p>'+preview+'</p></div></article></main>')
    assert p.extract()[0]==body.strip()


def test_paywall_and_jsonld_and_plain_editorial_body_remain_distinct():
    text='MOCK verified public editorial source. '*12
    p=EditorialParser();p.feed('<script type="application/ld+json">'+json.dumps({'@type':'NewsArticle','isAccessibleForFree':False,'articleBody':text})+'</script><article><p>'+text+'</p></article>')
    assert p.extract()==('', 'restricted') and p.restricted
    p=EditorialParser();p.feed('<main><div class="entry-content"><p>'+text+'</p></div><nav><p>MOCK irrelevant navigation</p></nav></main>')
    assert p.extract()[0]==text.strip()


def test_partition_preserves_complete_state_each_question_and_all40_identities():
    state={'article':{'headline':'MOCK','summary':'MOCK '+('source '*80)},'suppliers':[{'supplier_id':f'S{i:03}'} for i in range(1,41)]}
    p={'model':'jev-1.13.0','state':state,'questions':{f'q_{i}':{'type':'noul','instructions':f'MOCK proposition{i} '+('question '*80)} for i in range(18)}}
    before=deepcopy(p);budget=encoded_size({**p,'questions':{'q_0':p['questions']['q_0']}})+100
    parts=partition(p,budget)
    assert len(parts)>1 and p==before
    assert all(part['state']==state and encoded_size(part)<=budget for part in parts)
    keys=[k for part in parts for k in part['questions']]
    assert len(set(keys))==len(keys) and {k:v for part in parts for k,v in part['questions'].items()}==p['questions']
    with pytest.raises(ProviderError,match='JEV_QUESTION_CONTEXT_LOCAL'):partition(p,200)
    bad={**p,'questions':{'q':{'type':'choice','instructions':'MOCK','criteria':{str(i):str(i)for i in range(256)}}}}
    with pytest.raises(ProviderError,match='JEV_CHOICE_LIMIT_LOCAL'):partition(bad)


def test_partition_audit_merge_and_whole_response_cache_never_repeat_valid_parts(monkeypatch):
    import app.jev_transport as module
    class DB:
        def __init__(self):self.rows={}
        def get(self,model,key):return self.rows.get(key)
        def merge(self,row):self.rows[row.id]=row
        def commit(self):pass
    class Client:
        def __init__(self):self.db=DB();self.run_key='MOCK-run';self.network_requests=0;self.cached_stages=[];self.reuse_runs=()
        def ask(self,p,stage,deadline):
            key=digest({'payload':p,'questions':POLICY['question_version']});cached=self.db.get(RequestCache,key)
            if cached:self.cached_stages.append(stage);return validate_response(p,cached.response)
            assert encoded_size(p)<=module.CONFIG['request_json_budget_bytes']
            self.network_requests+=1;r=answer(p);self.db.merge(RequestCache(id=key,response=r));return r
    p={'model':'jev-1.13.0','state':{'article':'MOCK source'},'questions':{f'question{i}':{'type':'noul','instructions':'MOCK '+('body '*100)} for i in range(9)}}
    monkeypatch.setitem(module.CONFIG,'request_json_budget_bytes',1000)
    inner=Client();audit=CapturingClient(inner);client=BoundedFanoutClient(audit)
    r=client.ask(p,'b',time.monotonic()+10)
    assert r['answers']==answer(p)['answers'] and inner.network_requests>1
    assert all(q['state']==p['state'] for q in audit.payloads.values())
    assert len(audit.responses)==inner.network_requests
    assert client.transport_records[-1]['mode']=='partitioned'
    n=inner.network_requests;client.ask(p,'b',time.monotonic()+10);assert inner.network_requests==n
    assert client.transport_records[-1]['mode']=='cached_complete'
    assert client.transport_records[-1]['origin_transport']['version']==module.VERSION
    assert 'Authorization'not in str(audit.audit())


def test_provider_diagnostic_only_persists_allowlisted_machine_values():
    assert safe_http_diagnostic(httpx.Response(400,json={'error':'max_tokens_exceeded'}))=={'code':'max_tokens_exceeded'}
    assert safe_http_diagnostic(httpx.Response(400,json={'error':{'type':'invalid_request','message':'MOCK-SECRET'}}))=={'code':'invalid_request'}
    assert 'MOCK-SECRET'not in str(safe_http_diagnostic(httpx.Response(400,json={'error':'MOCK-SECRET','message':'MOCK-SECRET'})))


@pytest.mark.skipif(make_url(__import__('app.db',fromlist=['engine']).engine.url).database!='radar_test',reason='Requires isolated radar_test')
def test_durable_article_attempt_cap_survives_client_recreation(monkeypatch):
    from app.db import Base,Session,engine
    from app.models import ApiCall
    from app.jev import JevClient
    from app.settings import settings
    from tests.helpers import synthetic
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    monkeypatch.setattr(settings,'typesafe_api_key',SecretStr('MOCK-CREDENTIAL'))
    requests=[]
    def fetch(req):
        p=json.loads(req.content);requests.append(p);return httpx.Response(200,json=answer(p))
    with Session() as db:
        a=synthetic(db,'MOCK cap','MOCK cap source')
        p={'model':'jev-1.13.0','state':'MOCK','questions':{'q':{'type':'noul','instructions':'MOCK first'}}}
        client=JevClient(db,a.id,run_key='MOCK-cap',transport=httpx.MockTransport(fetch),request_ceiling=1)
        client.ask(p,'a',time.monotonic()+10);assert len(requests)==1
        client=JevClient(db,a.id,run_key='MOCK-cap',transport=httpx.MockTransport(fetch),request_ceiling=1)
        client.ask(p,'a',time.monotonic()+10);assert len(requests)==1  # valid cache allowed
        p2={**p,'state':'MOCK different source'}
        with pytest.raises(ProviderError,match='ARTICLE_REQUEST_LIMIT'):client.ask(p2,'b',time.monotonic()+10)
        assert len(requests)==1 and db.scalar(select(func.count()).select_from(ApiCall))==1


def test_enrichment_invalidates_old_extractor_once_and_does_not_refresh_cache_timestamp():
    from app.enrichment import enrich,VERSION
    from app.models import now
    source='MOCK primary body about an explicit operation and its source. '*12
    data={'headline':'MOCK primary operation','summary':'MOCK summary','url':'https://theloadstar.com/mock-source/','full_text':'MOCK OLD TICKER','enrichment':{'checked_at':now().isoformat(),'extractor_version':'old'}}
    article=SimpleNamespace(context='rss',source_id='the_loadstar',data=data)
    calls=[]
    def fetch(req):
        calls.append(req.url.path)
        assert 'authorization'not in req.headers and 'cookie'not in req.headers
        return httpx.Response(200,headers={'content-type':'text/html'},text='User-agent: *\nAllow: /' if req.url.path=='/robots.txt' else '<main><p>MOCK ticker</p><article><p>'+source+'</p></article></main>')
    db=SimpleNamespace(flush=lambda:None)
    enrich(db,article,httpx.MockTransport(fetch),check_dns=False)
    assert article.data['full_text']==source.strip() and article.data['enrichment']['extractor_version']==VERSION
    stamp=article.data['enrichment']['checked_at'];assert len(calls)==2
    enrich(db,article,httpx.MockTransport(fetch),check_dns=False)
    assert len(calls)==2 and article.data['enrichment']['checked_at']==stamp


@pytest.mark.skipif(make_url(__import__('app.db',fromlist=['engine']).engine.url).database!='radar_test',reason='Requires isolated radar_test')
def test_private_audit_and_versioned_recovery_keep_failed_attempt_and_result(monkeypatch):
    from fastapi.testclient import TestClient
    from app.db import Base,Session,engine,get_db
    from app.main import app
    from app.auth import presenter
    from app.models import Job,Analysis,ApiCall
    from tests.helpers import synthetic
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with Session() as db:
        a=synthetic(db,'MOCK failed long request','MOCK valid source');a.state='error'
        job=Job(key='analysis:'+a.id,kind='analysis',state='error',attempts=1,error='JEV_HTTP_400',payload={'article_id':a.id,'generation':0,'analysis_profile':'radar-1.0.0-candidate','analysis_versions':{'matching':'link-3.3.0'}});db.add(job)
        payload={'model':'jev-1.13.0','state':'MOCK PUBLIC SOURCE','questions':{'q':{'type':'noul','instructions':'MOCK'}}}
        result={'analysis_status':'error','error':'JEV_HTTP_400'}
        db.add(Analysis(article_id=a.id,generation=0,request_hash='MOCK-AUDIT-FAIL',result=result,raw={'_effective_payloads':{'b':payload}},duration=.2))
        call=ApiCall(article_id=a.id,run_key='',stage='b',attempt=1,model='jev-1.13.0',status=400,usage={'_error':'JEV_HTTP_400'},duration=.1);db.add(call);db.commit()
        old_job_id=job.id
        app.dependency_overrides[get_db]=lambda:db
        monkeypatch.setattr('app.main.require_current_worker',lambda db:None)
        monkeypatch.setattr('app.queue.reserve',lambda *args,**kw:True)
        try:
            with TestClient(app) as c:
                assert c.get('/api/articles/'+a.id+'/execution?include_payloads=true').status_code==401
                assert c.post('/api/articles/'+a.id+'/diagnose',json={'reason':'MOCK correction'}).status_code==401
                app.dependency_overrides[presenter]=lambda:object()
                summary=c.get('/api/articles/'+a.id+'/execution').json()
                assert summary['runs'][0]['stages'][0]['questions']==1 and 'effective_payloads'not in summary['runs'][0]
                detailed=c.get('/api/articles/'+a.id+'/execution?include_payloads=true').json();assert detailed['runs'][0]['effective_payloads']['b']==payload
                reply=c.post('/api/articles/'+a.id+'/retry',json={'reason':'MOCK context transport fixed and source parsing verified'})
                assert reply.status_code==202 and reply.json()['profile_updated'] and reply.json()['job_id']!=old_job_id
                assert db.get(Job,old_job_id).state=='error' and a.generation==1
                assert db.get(ApiCall,call.id).usage.get('_diagnosed_at')
                assert db.scalar(select(func.count()).select_from(ApiCall))==1
                assert db.scalar(select(func.count()).select_from(Analysis))==1
        finally:
            app.dependency_overrides.pop(get_db,None);app.dependency_overrides.pop(presenter,None)
