import json,time
import httpx,pytest
from sqlalchemy import select,func
from app.db import Session
from app.models import Article,Analysis,ApiCall,Incident,Supplier
from app.analysis import process_article,SCHEMA
from app.jev import JevClient,ProviderError,validate_response
from app.importer import export_batch
from app.views import suppliers_view
from tests.helpers import synthetic,answer
from reference.jev_requests import stage_a,stage_b
from reference.scoring import priority
from jsonschema import validate

def test_effective_payload_label_isolation_and_multisupplier():
    payloads=[]
    def handler(request):
        payload=json.loads(request.content);payloads.append(payload)
        text=request.content.decode()
        for forbidden in ('Is_Risk','Affected_Supplier_IDs','Event_Type','Explanation','SENTINEL_PROTECTED_LABEL'):
            assert forbidden not in text
        assert 'Urgent' not in payload['state']['article']
        return httpx.Response(200,json=answer(payload))
    with Session() as db:
        a=synthetic(db);a.data={**a.data,'Is_Risk':'SENTINEL_PROTECTED_LABEL','Urgent':'SENTINEL_PROTECTED_LABEL','Explanation':'SENTINEL_PROTECTED_LABEL'};db.commit()
        result=process_article(db,a.id,httpx.MockTransport(handler))
        validate(result,SCHEMA)
        assert result['affected_supplier_ids']==['S001','S002']
        assert result['is_risk']=='Y';assert len(payloads)==2
        assert len([k for k in payloads[0]['questions'] if k.startswith('linked_')])==40
        assert set(payloads[1]['state']['suppliers'][i]['supplier_id'] for i in (0,1))=={'S001','S002'}
        assert len(db.scalars(select(Incident)).all())==2
        result2=process_article(db,a.id,httpx.MockTransport(handler));assert len(payloads)==2
        data=export_batch(db,a.batch_id)
        from openpyxl import load_workbook
        from io import BytesIO
        rows=list(load_workbook(BytesIO(data)).active.values)
        assert rows[1]==('SYNTHETIC-TEST','Y','Y','S001; S002')

def test_positive_preserves_identity():
    with Session() as db:
        a=synthetic(db,'Synthetic positive supplier news')
        result=process_article(db,a.id,httpx.MockTransport(lambda r:httpx.Response(200,json=answer(json.loads(r.content),linked=('S001',),risk=.01,urgent=.01,impact='positive',event='positive_news'))))
        assert result['affected_supplier_ids']==['S001'];assert result['is_risk']==result['urgent']=='N'
        assert result['assessments'][0]['priority']==0
        assert db.scalar(select(func.count()).select_from(Incident))==0

def test_namesake_has_no_keyword_shortcut():
    with Session() as db:
        a=synthetic(db,'Synthetic namesake sports club in Hyderabad')
        seen=[]
        def handle(r):
            p=json.loads(r.content);seen.append(p);return httpx.Response(200,json=answer(p,linked=(),event='not_relevant',impact='unrelated'))
        result=process_article(db,a.id,httpx.MockTransport(handle))
        assert result['affected_supplier_ids']==[];assert len(seen)==1
        assert len(seen[0]['state']['suppliers'])==40

@pytest.mark.parametrize('status',[400,401,422])
def test_nonretryable_provider_error_blocks_export(status):
    with Session() as db:
        a=synthetic(db);calls=[]
        result=process_article(db,a.id,httpx.MockTransport(lambda r:(calls.append(1) or httpx.Response(status,json={'error':'mock'}))))
        assert len(calls)==1;assert result['is_risk'] is None;assert result['analysis_status']=='error'
        with pytest.raises(ValueError,match='bloqueada'):export_batch(db,a.batch_id)

@pytest.mark.parametrize('status',[429,529,503])
def test_transient_retry_is_bounded(status):
    with Session() as db:
        a=synthetic(db);s=[x.data for x in db.scalars(select(Supplier))]
        payload=stage_a(a.data,s);calls=[]
        def handle(r):
            calls.append(1)
            return httpx.Response(status,headers={'retry-after':'0'}) if len(calls)<3 else httpx.Response(200,json=answer(payload))
        client=JevClient(db,a.id,httpx.MockTransport(handle),sleep=lambda _:None)
        client.ask(payload,'a',time.monotonic()+60)
        assert len(calls)==3
        client.ask(payload,'a',time.monotonic()+60);assert len(calls)==3

@pytest.mark.parametrize('corrupt',['missing','nan','distribution','model'])
def test_contract_errors_are_not_zero(corrupt):
    with Session() as db:
        a=synthetic(db);s=[x.data for x in db.scalars(select(Supplier))];payload=stage_a(a.data,s);data=answer(payload)
        if corrupt=='missing':data['answers'].pop('linked_S001')
        if corrupt=='nan':data['answers']['linked_S001']['noul']=float('nan')
        if corrupt=='distribution':data['answers']['event_type']['probabilities']['fire_incident']=.2
        if corrupt=='model':data['model']='unexpected-model'
        with pytest.raises(ProviderError):validate_response(payload,data)

def test_incident_duplicate_recovery_and_late_old_evidence():
    with Session() as db:
        def process(a,**options):return process_article(db,a.id,httpx.MockTransport(lambda r:httpx.Response(200,json=answer(json.loads(r.content),linked=('S001',),**options))))
        a=synthetic(db);process(a)
        b=synthetic(db,published='2026-10-02T12:00:00+00:00');process(b)
        assert db.scalar(select(func.count()).select_from(Incident))==1
        inc=db.scalar(select(Incident));historical=inc.historical_priority
        recovered=synthetic(db,'Synthetic factory fire resolved for S001','Synthetic factory fire: production restored after the fire.',published='2026-10-03T12:00:00+00:00')
        process(recovered,impact='resolved',event='recovery',risk=.01,urgent=.01)
        db.refresh(inc);assert inc.state=='resolved';assert inc.priority==0;assert inc.historical_priority==historical
        late=synthetic(db,published='2026-10-01T13:00:00+00:00');process(late)
        db.refresh(inc);assert inc.state=='resolved';assert inc.priority==0;assert len(inc.history)==4
        s=next(s for s in suppliers_view(db) if s['supplier_id']=='S001');assert s['priority'] is None;assert s['status']=='resolved'

def test_distinct_events_take_max():
    with Session() as db:
        a=synthetic(db);process_article(db,a.id,httpx.MockTransport(lambda r:httpx.Response(200,json=answer(json.loads(r.content),linked=('S001',)))))
        b=synthetic(db,'Synthetic debt insolvency missed payments','Synthetic financial distress at S001',published='2026-10-02T12:00:00+00:00');process_article(db,b.id,httpx.MockTransport(lambda r:httpx.Response(200,json=answer(json.loads(r.content),linked=('S001',),event='financial_distress'))))
        incidents=db.scalars(select(Incident)).all();assert len(incidents)==2
        s=next(s for s in suppliers_view(db) if s['supplier_id']=='S001');assert s['priority']==max(i.priority for i in incidents)

def test_inventory_absent_zero_and_not_applicable():
    args=dict(is_risk=True,severity=8,criticality='High',single_source='Y',share_category_pct=50,lead_days=30)
    missing=priority(**args,inventory_days=None);zero=priority(**args,inventory_days=0)
    service=priority(**args,inventory_days=None,inventory_applicability='not_applicable')
    assert missing['needs_review'];assert zero['factors']['B']==1;assert not zero['needs_review'];assert 'B' not in service['factors'];assert not service['needs_review']
