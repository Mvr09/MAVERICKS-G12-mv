"""Synthetic operational decisions on isolated Postgres; no datasets or network."""
from copy import deepcopy
from uuid import uuid4
import json
import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.engine import make_url
from app.db import Base,Session,engine
from app.models import Article,Supplier,Analysis,Incident,Alert,EvaluationLabel,HumanDecision,Batch
from app.human_review import DecisionInput,ReviewConflict,save,view,effective_result
from app.incident_work import WorkInput,save as save_work,view as work_view
from app.incidents import reconcile
from scripts.review_scenarios import cases
pytestmark=pytest.mark.skipif(make_url(str(engine.url)).database!='radar_test',reason='Isolated synthetic DB only')

@pytest.fixture
def setup():
 Base.metadata.create_all(engine)
 with Session() as db:
  case=cases('jev-1.13.0')[0];sid='QA-OPS-'+str(uuid4());s={**case['suppliers'][0],'supplier_id':sid};db.add(Supplier(id=sid,data=s))
  batch=Batch(file_hash=str(uuid4()),split='training',filename='MOCK_OPERATIONS',count=1);db.add(batch);db.flush()
  a=Article(batch_id=batch.id,origin_key='MOCK-OPS-'+str(uuid4()),context='exercise',news_id='MOCK-OPS',data={**case['data'],'published_date':'2026-10-19T12:00:00+00:00'},content_hash='synthetic',state='review');db.add(a);db.flush()
  result=deepcopy(case['prediction']);result.update(article_id=a.id,analysis_status='review',affected_supplier_ids=[sid]);result['assessments']=[{**result['assessments'][0],'supplier_id':sid,'p_link':.9,'p_risk':.9,'p_urgent':.9,'is_risk':'Y','urgent':'Y','needs_review':True,'priority':50,'priority_band':'high','impact_status':'active'}]
  analysis=Analysis(article_id=a.id,generation=0,request_hash=str(uuid4()),result=result,raw={},duration=0,cached=True);db.add(analysis);db.add(EvaluationLabel(article_id=a.id,data={'sentinel':'not-training-feedback'}));db.flush();reconcile(db,a,result);db.flush()
  yield db,a,analysis,sid
  db.rollback()

def body(a,analysis,sid,**kw):
 return DecisionInput(supplier_id=sid,generation=a.generation,source_version=a.version,analysis_id=analysis.id,source_hash=a.content_hash,association='confirmed',risk='Y',urgent='N',severity=6,impact_status='monitoring',case_scope_confirmed=True,note='Confirmación sintética razonada',evidence='MOCK supplier confirms a limited impact, no immediate delivery threat.',evidence_source='MOCK-source',**kw)

def test_human_review_is_append_only_does_not_relabel_model_or_export(setup):
 db,a,analysis,sid=setup;original=json.dumps(analysis.result,sort_keys=True);r=save(db,a.id,body(a,analysis,sid));db.flush()
 assert json.dumps(analysis.result,sort_keys=True)==original
 assert db.get(EvaluationLabel,a.id).data=={'sentinel':'not-training-feedback'}
 assert view(db,a)['state']=='resolved'
 assert effective_result(db,a,analysis.result)['assessments'][0]['urgent']=='N'
 alerts=db.scalars(select(Alert).join(Incident).where(Incident.supplier_id==sid)).all();assert all(not x.data['sound_eligible']for x in alerts)
 inc=db.scalar(select(Incident).where(Incident.supplier_id==sid));assert any(h.get('human_review_id')==r.id for h in inc.history)
 assert 'Confirmación sintética' not in str(inc.history) # Notes stay private.
 from app.drafts import make_draft
 assert 'MOCK-source'in make_draft(db,db.get(Supplier,sid),inc,'supplier')
 with pytest.raises(ReviewConflict):save(db,a.id,body(a,analysis,sid))
 a.generation+=1;db.flush();assert view(db,a)['history'][0]['obsolete']
 assert effective_result(db,a,analysis.result)['assessments'][0]['urgent']=='Y'

def test_pending_request_and_rejection_have_an_exit(setup):
 db,a,analysis,sid=setup
 pending=save(db,a.id,DecisionInput(supplier_id=sid,generation=0,source_version=1,analysis_id=analysis.id,source_hash=a.content_hash,association='unknown',note='Confirma provincia y ruta; no hay dato verificado'))
 assert view(db,a)['state']=='in_verification'
 inc=db.scalar(select(Incident).where(Incident.supplier_id==sid));assert inc.history[-1]['assessment']['needs_review']
 rejection=DecisionInput(supplier_id=sid,generation=0,source_version=1,analysis_id=analysis.id,source_hash=a.content_hash,previous_id=pending.id,association='rejected',note='Ruta distinta confirmada por fuente sintética',evidence='MOCK: the named service uses a different corridor.',evidence_source='MOCK-source')
 save(db,a.id,rejection);db.flush();assert view(db,a)['state']=='resolved';assert inc.state=='superseded'
 assert effective_result(db,a,analysis.result)['affected_supplier_ids']==[]
 assert len(view(db,a)['history'])==2

def test_workflow_is_not_recovery_and_saved_context_survives(setup):
 db,a,analysis,sid=setup;inc=db.scalar(select(Incident).where(Incident.supplier_id==sid));save_work(db,inc.id,WorkInput(status='verifying',action='Confirmar entregas y ruta',note='Consulta preparada sin envío externo'));w=work_view(db,inc);save_work(db,inc.id,WorkInput(previous_id=w['current']['id'],status='done',action='Confirmar entregas y ruta',note='Llamada sintética completada; seguir monitorizando'));assert inc.state=='active';assert len(work_view(db,inc)['history'])==2
 with pytest.raises(ReviewConflict):save_work(db,inc.id,WorkInput(status='pending',action='Intento desactualizado',note='No sobrescribir otra acción'))

def test_closed_incident_is_not_reopened_by_human_reclassification(setup):
 db,a,analysis,sid=setup;inc=db.scalar(select(Incident).where(Incident.supplier_id==sid));inc.state='resolved';inc.priority=0
 save(db,a.id,body(a,analysis,sid));assert inc.state=='resolved'and inc.priority==0

def test_stale_analysis_and_unsubstantiated_decisions_are_rejected(setup):
 db,a,analysis,sid=setup;a.version=2
 with pytest.raises(ReviewConflict):save(db,a.id,body(a,analysis,sid).model_copy(update={'source_version':1}))
 with pytest.raises(ValidationError):DecisionInput(supplier_id=sid,generation=0,source_version=1,analysis_id=analysis.id,source_hash=a.content_hash,association='confirmed',risk='Y',urgent='Y',note='Sin evidencia suficiente')

def test_cleaning_does_not_erase_human_history(setup):
 db,a,analysis,sid=setup;save(db,a.id,body(a,analysis,sid))
 from app.demo import preview
 assert 'decisiones humanas'in preview(db,['batch:'+a.batch_id],mode='delete')['blocked']

def test_review_api_permissions_validation_and_persistent_public_summary(setup):
 from fastapi.testclient import TestClient
 from app.main import app
 from app.db import get_db
 from app.auth import presenter
 db,a,analysis,sid=setup
 def database():yield db
 app.dependency_overrides[get_db]=database
 try:
  with TestClient(app) as client:
   assert client.get('/api/articles/'+a.id+'/review').status_code==401
   assert client.post('/api/articles/'+a.id+'/review',json=body(a,analysis,sid).model_dump()).status_code==401
   assert client.get('/api/incidents/MOCK/workspace').status_code==401
   assert client.post('/api/incidents/MOCK/workspace',json={'status':'pending','action':'Acción sintética','note':'Nota sintética'}).status_code==401
   app.dependency_overrides[presenter]=lambda: True # Explicit mocked presenter, no real session/network.
   payload=body(a,analysis,sid).model_dump();payload['note']='PRIVATE_SENTINEL_NOTE';payload['evidence']='PRIVATE_SENTINEL_EVIDENCE'
   response=client.post('/api/articles/'+a.id+'/review',json=payload);assert response.status_code==201,response.text
   public=client.get('/api/articles/'+a.id);assert public.status_code==200
   assert public.json()['analysis']['urgent']==analysis.result['urgent'] # The original is still public.
   assert public.json()['human_review']['state']=='resolved'
   assert 'PRIVATE_SENTINEL'not in public.text
   assert client.post('/api/articles/'+a.id+'/review',json=payload).status_code==409
 finally:
  app.dependency_overrides.pop(get_db,None);app.dependency_overrides.pop(presenter,None)


def test_triage_geography_is_only_retrieval_and_unknown_city_stays_unknown():
 from app.relevance import hints
 from app.geography import location
 ss=[{'supplier_id':'QA-GEO','name':'MOCK Leaflets','country':'China','city':'Hangzhou'},{'supplier_id':'QA-UNKNOWN','name':'MOCK Ambiguous','country':'China','city':'Taizhou'}]
 r=hints('Zhejiang power maintenance','MOCK controlled regional event, no named company.',json.dumps(ss))
 assert r['level']=='geography'and'no asociación'in r['limitation']
 assert any(s['supplier_id']=='QA-GEO'for s in r['suppliers'])
 assert location(ss[1])['status']=='ambiguous'
 assert hints('Namibia wildfire','No operations connected in source.',json.dumps(ss))['level']=='none'

def test_partial_supplier_resolution_does_not_close_global_doubt(setup):
 db,a,analysis,sid=setup
 analysis.result={**analysis.result,'review_details':[{'code':'global_scope_unknown','relevance':'risk','requires_review':True,'supplier_id':None}]}
 save(db,a.id,body(a,analysis,sid).model_copy(update={'case_scope_confirmed':False}));assert view(db,a)['general_pending']and view(db,a)['state']=='in_verification'

def test_rejection_keeps_other_article_evidence_and_priority(setup):
 db,a,analysis,sid=setup;inc=db.scalar(select(Incident).where(Incident.supplier_id==sid));other=deepcopy(inc.history[0]);other['article_id']='MOCK-OTHER';other['assessment']['priority']=73;inc.history=[*inc.history,other]
 save(db,a.id,DecisionInput(supplier_id=sid,generation=0,source_version=1,analysis_id=analysis.id,source_hash=a.content_hash,association='rejected',evidence='MOCK route explicitly differs.',evidence_source='MOCK reference',note='Only this source was excluded; other event evidence remains'))
 assert inc.state!='superseded'and inc.priority==73
 assert any(h['article_id']=='MOCK-OTHER'and not h.get('superseded')for h in inc.history)


def test_content_hash_change_rejects_a_stale_human_form(setup):
 db,a,analysis,sid=setup;payload=body(a,analysis,sid);a.content_hash='MOCK-updated-source'
 with pytest.raises(ReviewConflict):save(db,a.id,payload)

def test_rss_batch_bounds_are_explicit_and_not_periodic():
 from app.main import ManualRssAnalysis
 assert len(ManualRssAnalysis(article_ids=[str(i)for i in range(10)],analysis_profile='radar-1.0.0-candidate').article_ids)==10
 with pytest.raises(ValidationError):ManualRssAnalysis(article_ids=[str(i)for i in range(11)])
 from app.settings import settings
 assert not settings.rss_analysis_enabled

def test_observation_retains_previous_decision_without_new_alert_or_priority(setup):
 db,a,analysis,sid=setup;r=save(db,a.id,body(a,analysis,sid));inc=db.scalar(select(Incident).where(Incident.supplier_id==sid));before=(inc.priority,inc.revision,len(inc.history));count=len(db.scalars(select(Alert).join(Incident).where(Incident.supplier_id==sid)).all())
 note=save(db,a.id,DecisionInput(intent='note',supplier_id=sid,generation=0,source_version=1,source_hash=a.content_hash,analysis_id=analysis.id,previous_id=r.id,association='unknown',note='MOCK nueva observación, sin cambiar el hecho comprobado'))
 assert note.data['risk']=='Y'and note.data['association']=='confirmed'and note.data['entry_kind']=='note'
 assert before==(inc.priority,inc.revision,len(inc.history));assert view(db,a)['state']=='resolved'
 assert count==len(db.scalars(select(Alert).join(Incident).where(Incident.supplier_id==sid)).all())

def test_declared_corridor_retrieval_distinguishes_modes_without_inventing_shipments():
 from app.relevance import hints
 catalog=json.dumps([{'supplier_id':'MOCK-SEA','name':'MOCK Maritime Operator','material':'Asia to Europe sea freight','country':'Singapore','city':'Singapore'},{'supplier_id':'MOCK-RAIL','name':'MOCK Rail Operator','material':'Asia to Europe rail freight','country':'China','city':"Xi'an"}])
 sea=hints('Asia-Europe container freight spot rates rise','MOCK market pricing only; no shipment mentioned.',catalog)
 assert sea['level']=='service'and {s['supplier_id']for s in sea['suppliers']}=={'MOCK-SEA'}
 rail=hints('Asia-Europe rail freight capacity','MOCK booking market only.',catalog)
 assert {s['supplier_id']for s in rail['suppliers']}=={'MOCK-RAIL'}
 assert hints('Asia-Europe market conference','No transport mode is established.',catalog)['level']=='none'

def test_nonurgent_human_risk_does_not_imply_inactive_impact(setup):
 db,a,analysis,sid=setup;save(db,a.id,body(a,analysis,sid).model_copy(update={'impact_status':'active','urgent':'N'}));inc=db.scalar(select(Incident).where(Incident.supplier_id==sid));assert inc.state=='active'and inc.history[-1]['assessment']['urgent']=='N'

def test_new_human_candidate_is_pending_not_resolved_and_never_invents_probabilities(setup):
 db,a,analysis,sid=setup;extra='QA-NEW-'+str(uuid4());db.add(Supplier(id=extra,data={**db.get(Supplier,sid).data,'supplier_id':extra}));db.flush()
 # No original model candidate/assessment exists for this supplier.
 request=save(db,a.id,DecisionInput(supplier_id=extra,generation=0,source_version=1,source_hash=a.content_hash,analysis_id=analysis.id,association='unknown',note='MOCK confirmar ubicación antes de concluir la exposición'))
 assert extra in view(db,a)['remaining_suppliers']and view(db,a)['state']=='in_verification'
 from app.views import suppliers_view
 selected=next(s for s in suppliers_view(db,'exercise')if s['supplier_id']==extra);assert selected['needs_review']and selected['review_work']
 positive=body(a,analysis,extra,previous_id=request.id);save(db,a.id,positive);inc=db.scalar(select(Incident).where(Incident.supplier_id==extra));assessment=inc.history[-1]['assessment']
 assert all(assessment[k]is None for k in ['p_link','p_risk','p_urgent'])and not assessment['model_probabilities_available']
 assert all(p['supplier_id']!=extra for p in analysis.result['assessments'])


def test_positive_identity_correction_without_risk_is_visible_operationally(setup):
 db,a,analysis,sid=setup;extra='QA-POS-'+str(uuid4());db.add(Supplier(id=extra,data={**db.get(Supplier,sid).data,'supplier_id':extra}));db.flush()
 payload=DecisionInput(supplier_id=extra,generation=0,source_version=1,source_hash=a.content_hash,analysis_id=analysis.id,association='confirmed',risk='N',urgent='N',note='MOCK noticia positiva, proveedor identificado sin amenaza',evidence='MOCK supplier received a sustainability award.',evidence_source='MOCK source')
 save(db,a.id,payload)
 from app.views import suppliers_view
 selected=next(s for s in suppliers_view(db,'exercise')if s['supplier_id']==extra)
 assert selected['priority']==0 and not selected['needs_review']and 'Sin riesgo activo'in selected['reason']
