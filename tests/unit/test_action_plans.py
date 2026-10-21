"""Suggested action plans and Claude drafting. MOCK provider only: no network or API key."""
import json
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4
import pytest
from sqlalchemy import select
from sqlalchemy.engine import make_url
from app import llm
from app.action_plans import choose_actions, numbers_not_in_facts, summarize, sync_plan, view, enqueue_for_article, template_summary
from app.db import Base, Session, engine
from app.models import ActionPlan, Article, Analysis, Batch, Incident, Job, Supplier

def facts(**kw):
 base={'incidente':{'id':'I1','revision':1,'tipo_evento':'fire_incident','estado':'active','urgente':True,'prioridad':72.5,'banda':'high','fecha_evento':'2026-10-02','titular':'Fire at plant','duracion_dias':40,'duracion_es_minima':False,'pendiente_de_revision':False,'decision_humana':False},
  'vinculo':{'exposicion':'reported','p_vinculo':0.9,'por_confirmar':False},
  'proveedor':{'id':'S001','nombre':'Alpha','ciudad':'Ningbo','pais':'China','categoria':'API','material':'API X','fuente_unica':True,'criticidad':'High'},
  'stock':{'margen_dias':21,'plazo_reposicion_dias':45,'fecha_rotura_si_continua':'2026-10-23'},
  'productos':['Product A'],'alternativo':{'id':'S002','nombre':'Beta','ciudad':'Lyon','pais':'France','afectado':False}}
 for k,v in kw.items():base[k]={**base[k],**v} if isinstance(v,dict) else v
 return base

def codes(f):
 return [a['code'] for a in choose_actions(f)]

def test_urgent_single_source_gets_today_actions_and_escalation():
 acts=choose_actions(facts());c=[a['code'] for a in acts]
 assert c==['contact_supplier','shift_to_alternate','increase_safety_stock','start_dual_sourcing','escalate_planning']
 assert {a['code']:a['deadline'] for a in acts}['contact_supplier']=='hoy'
 assert {a['code']:a['deadline'] for a in acts}['start_dual_sourcing']=='esta_semana'

def test_non_urgent_logistics_monitors_without_stock_action():
 f=facts(incidente={'urgente':False,'banda':'medium','duracion_dias':None},proveedor={'categoria':'Logistics','fuente_unica':False},stock={'margen_dias':'no aplica','fecha_rotura_si_continua':None},alternativo=None)
 assert codes(f)==['monitor','contact_supplier','reroute_logistics']

def test_unconfirmed_exposure_asks_to_verify_and_template_says_so():
 f=facts(vinculo={'exposicion':'potential','por_confirmar':True});acts=choose_actions(f)
 assert 'verify_link' in [a['code'] for a in acts]
 assert 'podría estar afectado' in template_summary(f,acts)
 assert 'verify_link' in codes(facts(vinculo={'p_vinculo':0.55}))
 assert 'shift_to_alternate' not in codes(facts(alternativo={'afectado':True}))

def test_number_guard_rejects_invented_figures_and_accepts_facts():
 f=facts()
 assert numbers_not_in_facts('Prioridad 72,5 de 100; margen de 21 días; rotura el 23 de octubre de 2026.',f)==[]
 assert numbers_not_in_facts('Pedir 500 unidades en 3 días.',f)==['500','3']
 assert numbers_not_in_facts('Proveedor S001 afectado.',f)==[]

def plan_like(f=None):
 f=f or facts()
 return SimpleNamespace(facts=f,actions=choose_actions(f),summary_source='template',summary_llm=None,summary_error=None,llm=None)

GOOD=('Alpha, en Ningbo, sufre un incendio desde el 2 de octubre de 2026 con prioridad 72,5 de 100 y urgencia. Con 21 días de margen '
 'de stock, la rotura llegaría el 23 de octubre de 2026 si la parada continúa. Hoy hay que pedir al proveedor el impacto y la fecha de '
 'recuperación, preparar el cambio de volumen a Beta, adelantar pedidos y avisar a planificación; esta semana conviene iniciar la '
 'cualificación de una segunda fuente porque es fuente única de criticidad alta.')

@pytest.fixture
def fake():
 def use(responder):
  p=llm.FakeProvider(responder);llm.set_provider(p);return p
 yield use
 llm.set_provider(None)

def test_claude_summary_is_used_only_when_it_respects_the_facts(fake):
 p=fake(lambda s,u:json.dumps({'texto':GOOD}));plan=summarize(None,plan_like())
 assert plan.summary_source=='llm' and plan.summary_llm==GOOD and plan.llm['model']=='fake-model'
 assert 'S001' not in p.calls[0][1] and '<<<DATOS>>>' in p.calls[0][1]  # ids stay out of the prompt
 fake(lambda s,u:json.dumps({'texto':GOOD+' Comprar 800 unidades.'}));plan=summarize(None,plan_like())
 assert plan.summary_source=='template' and '800' in plan.summary_error

def test_any_claude_failure_keeps_the_template(fake):
 def boom(s,u):raise llm.LLMError('rate_limit','Límite de uso de Anthropic alcanzado.')
 fake(boom);plan=summarize(None,plan_like());assert plan.summary_source=='template' and 'Límite' in plan.summary_error
 fake(lambda s,u:'not json');assert summarize(None,plan_like()).summary_source=='template'
 llm.set_provider(None)
 from app.settings import settings
 old=settings.anthropic_api_key
 try:
  settings.anthropic_api_key=type(old)('')
  plan=summarize(None,plan_like());assert plan.summary_source=='template' and 'no está configurado' in plan.summary_error
 finally:settings.anthropic_api_key=old

def provider_with(response=None,error=None):
 import anthropic
 seen={}
 def create(**kw):
  seen.update(kw)
  if error:raise error
  return response
 p=object.__new__(llm.AnthropicProvider);p.model='claude-sonnet-5-5';p.effort='low';p.max_tokens=4000;p._anthropic=anthropic
 p.client=SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create)))
 return p,seen

def test_anthropic_request_uses_structured_output_and_default_fallback():
 usage=SimpleNamespace(input_tokens=900,output_tokens=120)
 ok=SimpleNamespace(stop_reason='end_turn',content=[SimpleNamespace(type='text',text='{"texto":"hola"}')],usage=usage,model='claude-sonnet-5-5')
 p,seen=provider_with(ok);text,meta=p.complete('sys','user',llm.TEXT_SCHEMA)
 assert text=='{"texto":"hola"}' and meta['input_tokens']==900
 assert seen['model']=='claude-sonnet-5-5' and seen['fallbacks']=='default' and seen['betas']==[llm.FALLBACK_BETA]
 assert seen['output_config']=={'effort':'low','format':{'type':'json_schema','schema':llm.TEXT_SCHEMA}}
 refused=SimpleNamespace(stop_reason='refusal',stop_details=SimpleNamespace(category='cyber'),content=[],usage=usage,model='x')
 p,_=provider_with(refused)
 with pytest.raises(llm.LLMError) as e:p.complete('s','u',llm.TEXT_SCHEMA)
 assert e.value.code=='refusal'

def test_anthropic_errors_map_to_codes_without_leaking_bodies():
 import anthropic,httpx2
 req=httpx2.Request('POST','https://api.anthropic.com/v1/messages')
 p,_=provider_with(error=anthropic.APIConnectionError(request=req))
 with pytest.raises(llm.LLMError) as e:p.complete('s','u',llm.TEXT_SCHEMA)
 assert e.value.code=='unavailable'

def test_assisted_draft_uses_recipient_language_and_rejects_new_figures(fake):
 from app.drafts import assist_draft
 sup=SimpleNamespace(id='S001',data={'name':'Alpha','country':'China','alternate_id':'S002'})
 alt=SimpleNamespace(id='S002',data={'name':'Beta','country':'Spain'})
 db=SimpleNamespace(get=lambda model,key:alt)
 template='Asunto: Confirmación — API X\n\nNoticia publicada el 2026-10-02. Solicitamos confirmar el impacto. Esta consulta no constituye un pedido.'
 p=fake(lambda s,u:json.dumps({'texto':'Subject: Supply continuity — API X\n\nNews published on 2 October 2026. Please confirm the impact. This is not a purchase order.'}))
 text,writer=assist_draft(db,sup,'supplier',template);assert writer['writer']=='claude' and writer['language']=='en' and 'inglés' in p.calls[0][1]
 _,writer=assist_draft(db,sup,'alternate',template);assert writer['language']=='es'
 fake(lambda s,u:json.dumps({'texto':'Subject: Supply continuity\n\nPlease confirm 5000 kg before 30 November. This is not a purchase order.'}))
 with pytest.raises(llm.LLMError):assist_draft(db,sup,'supplier',template)

needs_db=pytest.mark.skipif(make_url(str(engine.url)).database!='radar_test',reason='Isolated synthetic DB only')

@pytest.fixture
def incident():
 from scripts.review_scenarios import cases
 from app.incidents import reconcile
 Base.metadata.create_all(engine)
 with Session() as db:
  case=cases('jev-1.13.0')[0];sid='QA-PLAN-'+str(uuid4());db.add(Supplier(id=sid,data={**case['suppliers'][0],'supplier_id':sid,'alternate_id':None}))
  batch=Batch(file_hash=str(uuid4()),split='training',filename='MOCK_PLANS',count=1);db.add(batch);db.flush()
  a=Article(batch_id=batch.id,origin_key='MOCK-PLAN-'+str(uuid4()),context='exercise',news_id='MOCK-PLAN',data={**case['data'],'published_date':'2026-10-19T12:00:00+00:00'},content_hash='synthetic',state='done');db.add(a);db.flush()
  result=deepcopy(case['prediction']);result.update(article_id=a.id,analysis_status='done',affected_supplier_ids=[sid])
  result['assessments']=[{**result['assessments'][0],'supplier_id':sid,'p_link':.9,'p_risk':.9,'p_urgent':.9,'is_risk':'Y','urgent':'Y','needs_review':False,'priority':70,'priority_band':'high','impact_status':'active','duration_days':None}]
  db.add(Analysis(article_id=a.id,generation=0,request_hash=str(uuid4()),result=result,raw={},duration=0,cached=True));db.flush();reconcile(db,a,result);db.flush()
  yield db,a,db.scalar(select(Incident).where(Incident.supplier_id==sid))
  db.rollback()

@needs_db
def test_plan_is_per_revision_idempotent_and_never_touches_the_incident(incident,fake):
 db,a,inc=incident;before=(inc.state,inc.priority,inc.revision,json.dumps(inc.history,sort_keys=True,default=str))
 plan=sync_plan(db,inc);assert plan.revision==inc.revision and plan.summary_source=='template'
 assert sync_plan(db,inc).id==plan.id and db.scalar(select(ActionPlan.id).where(ActionPlan.incident_id==inc.id,ActionPlan.id!=plan.id)) is None
 fake(lambda s,u:json.dumps({'texto':'x'}));summarize(db,plan);assert plan.summary_source=='template'
 assert (inc.state,inc.priority,inc.revision,json.dumps(inc.history,sort_keys=True,default=str))==before
 v=view(plan);assert v['actions'][0]['deadline_label'] and 'id' not in v['facts']['proveedor']
 inc.state='resolved';assert sync_plan(db,inc) is None

@needs_db
def test_finished_analysis_enqueues_lowest_priority_plan_job(incident):
 db,a,inc=incident;enqueue_for_article(db,a.id);db.flush()
 job=db.scalar(select(Job).where(Job.key==f'plan:{inc.id}:{inc.revision}'))
 assert job.kind=='action_plan' and job.priority==0 and job.payload=={'incident_id':inc.id,'revision':inc.revision}
