import json
from types import SimpleNamespace
import pytest,httpx
from sqlalchemy import select,func
from sqlalchemy.engine import make_url
from pydantic import SecretStr
from app.db import Base,Session,engine
from app.models import *
from app.campaigns import prepare,start,process,report,aggregate
from tests.helpers import answer
from tests.unit.test_support_contract import SUPPLIER
pytestmark=pytest.mark.skipif(make_url(str(engine.url)).database!='radar_test',reason='Explicit isolated DB')

def payload():
 return {'name':'MOCK campaign '+uid(),'suppliers':[dict(SUPPLIER,supplier_id=f'S{i:03}') for i in range(1,41)],'manifest':{'MOCK':True},'inputs':[{'split':'training','data':{'news_id':'QA001','headline':'MOCK positive update','summary':'MOCK no interruption.','source':'MOCK','published_date':'2026-10-19T00:00:00+00:00','language':'en'},'reference':{'Is_Risk':'N','Urgent':'N','Affected_Supplier_IDs':''}}]}

def test_new_campaign_isolation_and_resume(monkeypatch):
 Base.metadata.create_all(engine)
 monkeypatch.setattr('app.settings.settings.typesafe_api_key',SecretStr('MOCK'))
 with Session() as db:
  before={m.__tablename__:db.scalar(select(func.count()).select_from(m)) for m in (Article,Analysis,Alert,Incident,HumanDecision,EvaluationLabel)}
  body=payload();c=prepare(db,body);cid=c.id
  assert db.scalar(select(func.count()).select_from(CampaignRun).where(CampaignRun.campaign_id==cid))==2
  assert c.state=='prepared' and not c.started_at
  start(db,cid)
  row=db.scalar(select(CampaignRun).where(CampaignRun.campaign_id==cid,CampaignRun.profile=='1.0.0'))
  seen=[]
  def fetch(request):
   data=json.loads(request.content);seen.append(data)
   assert 'Is_Risk' not in json.dumps(data) and 'Affected_Supplier_IDs' not in json.dumps(data)
   return httpx.Response(200,json=answer(data,linked=(),risk=.02,urgent=.02))
  t=httpx.MockTransport(fetch)
  out=process(db,row.id,t);assert out.state in ('done','review');n=len(seen);assert n==1
  process(db,row.id,t);assert len(seen)==n
  c2=prepare(db,payload());start(db,c2.id);r2=db.scalar(select(CampaignRun).where(CampaignRun.campaign_id==c2.id,CampaignRun.profile=='1.0.0'));process(db,r2.id,t);assert len(seen)==2 # identical text, fresh campaign, no old cache
  assert before=={m.__tablename__:db.scalar(select(func.count()).select_from(m)) for m in (Article,Analysis,Alert,Incident,HumanDecision,EvaluationLabel)}
  x=report(db,cid);assert x['aggregate']['1.0.0']['completed']==1
  assert db.get(CampaignRun,row.id).audit['new_requests']==1


def test_null_failures_not_negative_and_no_labels_for_test():
 rows=[SimpleNamespace(state='error',result={'is_risk':None,'urgent':None},reference=None,audit={},started_at=None,completed_at=None)]
 x=aggregate(rows);assert x['errors']==1 and x['completed']==0 and x['quality'] is None and x['automatic_rate']==0
 with Session() as db:
  body=payload();body['inputs'][0]['split']='test'
  with pytest.raises(ValueError):prepare(db,body)
  db.rollback()
  body=payload();body['inputs'][0]['data']['Is_Risk']='Y'
  with pytest.raises(ValueError):prepare(db,body)


def test_unauthenticated_campaigns_are_private():
 from fastapi.testclient import TestClient
 from app.main import app
 with TestClient(app) as c:
  assert c.get('/api/campaigns').status_code==401
  assert c.get('/api/campaigns/any/export').status_code==401

def test_fanout_campaign_does_not_read_or_write_global_cache(monkeypatch):
 from app.jev_transport import BoundedFanoutClient,CONFIG
 from app.jev_audit import CapturingClient
 from app.importer import digest
 from app.settings import POLICY
 import time
 class DB:
  def __init__(self):self.rows={}
  def get(self,m,k):return self.rows.get(k)
  def merge(self,r):self.rows[r.id]=r
  def commit(self):pass
 class Client:
  def __init__(self):self.db=DB();self.run_key='campaign:QA-new';self.isolated_cache=True;self.called=0
  def ask(self,p,stage,deadline):self.called+=1;return answer(p,linked=())
 p={'model':'jev-1.13.0','state':{'article':'MOCK'},'questions':{f'q{i}':{'type':'noul','instructions':'MOCK '+('text '*100)} for i in range(4)}}
 client=Client();key=digest({'payload':p,'questions':POLICY['question_version']});old=answer(p,linked=());old['usage']={'MOCKhistorical':1};client.db.rows[key]=RequestCache(id=key,response=old)
 monkeypatch.setitem(CONFIG,'request_json_budget_bytes',900)
 wrapped=BoundedFanoutClient(CapturingClient(client));result=wrapped.ask(p,'a',time.monotonic()+10)
 assert client.called>1 and wrapped.transport_records[0]['mode']=='partitioned'
 assert client.db.rows[key].response==old
 assert digest({'request':key,'run_key':client.run_key}) in client.db.rows

def test_authentication_failure_pauses_and_remains_null(monkeypatch):
 Base.metadata.create_all(engine);monkeypatch.setattr('app.settings.settings.typesafe_api_key',SecretStr('MOCK'))
 with Session() as db:
  c=prepare(db,payload());start(db,c.id);r=db.scalar(select(CampaignRun).where(CampaignRun.campaign_id==c.id,CampaignRun.profile=='1.0.0'))
  seen=[]
  def fetch(req):seen.append(1);return httpx.Response(401,json={'error':{'code':'invalid_api_key'}})
  process(db,r.id,httpx.MockTransport(fetch));assert len(seen)==1
  assert r.state=='error' and r.result['is_risk'] is None and r.result['urgent'] is None
  assert db.get(EvaluationCampaign,c.id).state=='paused'
  with pytest.raises(ValueError):start(db,c.id)
  assert len(seen)==1
