"""Frozen comparative campaigns: private references, no operational projections."""
import csv, io, os, time, json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from sqlalchemy import select, text
from app.models import EvaluationCampaign, CampaignRun, ConsumptionBudget, Grant, ApiCall, Job, now
from app.settings import ROOT, settings, POLICY
from app.importer import digest
from app.profiles import CANDIDATE_PROFILE, candidate_versions, maximum_requests
from app.evaluation import metrics, ratio

PROFILES = ('1.0.0', CANDIDATE_PROFILE)
# Product views can change while a campaign runs. Semantic inputs cannot.
SEMANTIC_FILES = ['reference/jev_requests.py','reference/scoring.py','config/risk_policy.json','config/jev_transport.json'] + ['app/'+n+'.py' for n in ('analysis','profiles','duration','geography','stable_geography','link_questions','candidate_engine','candidate_matching','candidate_risk','candidate_review','candidate_review_focus','review_policy','review_support','review_facts','jev','jev_transport','jev_audit')]
SEMANTIC_FILES += ['config/geography.json','app/candidate_refinement.json','app/link_candidate.py','app/link_analysis.py','app/rss_questions.py','app/payload_cache.py']

def versions():
    return {'1.0.0':{'profile':'1.0.0','matching':'1.0.0','questions':'1.0.0','review':'legacy-review-1.0.0','policy':POLICY['version'],'duration':__import__('app.duration',fromlist=['VERSION']).VERSION,'geography':'original catalog only','model':settings.jev_model},CANDIDATE_PROFILE:{**candidate_versions(),'policy':POLICY['version'],'model':settings.jev_model}}

def semantic_hashes():
    import hashlib
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SEMANTIC_FILES}

def prepare(db, payload):
    inputs=payload['inputs'];suppliers=payload['suppliers']
    if not 1<=len(inputs)<=200 or len(suppliers)!=40:raise ValueError('Se requieren entradas explícitas y las40 identidades originales.')
    if len({s['supplier_id'] for s in suppliers})!=40:raise ValueError('Catálogo repetido')
    if len({(x['split'],x['data']['news_id']) for x in inputs})!=len(inputs):raise ValueError('Identidades de noticia repetidas')
    allowed={'news_id','published_date','source','headline','summary','language','context_id'}
    for x in inputs:
        if x['split'] not in ('training','validation','test','liveday'):raise ValueError('Muestra desconocida')
        if set(x['data'])-allowed:raise ValueError('Contexto de inferencia no permitido')
        if x['split'] in ('test','liveday') and x.get('reference') is not None:raise ValueError('Sin etiquetas para test/LiveDay')
        ref=x.get('reference')
        if x['split'] in ('training','validation') and (not ref or any(ref.get(k) not in ('Y','N') for k in ('Is_Risk','Urgent'))):raise ValueError('Referencia conocida incompleta')
    freeze={'inputs':inputs,'suppliers':suppliers,'materials':payload.get('materials',[]),'manifest':payload['manifest'],'versions':versions(),'semantic_hashes':semantic_hashes(),'model':settings.jev_model,'original_baseline':True,'cache_policy':'new campaign-scoped inference; resume only same record/stage','references_scope':'evaluation only; training and validation already inspected, not independent','concurrency':4,'order':'original row order; interleaved profiles A then B per input','expected_complete_analyses':len(inputs)*2,'request_estimate':{'baseline_initial_range':[len(inputs),len(inputs)*2],'candidate_initial_minimum':sum(len(__import__('app.jev_transport',fromlist=['partition']).partition(__import__('app.candidate_matching',fromlist=['stage_a']).stage_a(x['data'],suppliers,settings.jev_model,'exercise'))) for x in inputs),'candidate_conditional_stages':'B, pre_support, risk_focus/current_threat, support and followup, independently partitioned as required','max_http_attempts_including_retries':len(inputs)*(6+maximum_requests(CANDIDATE_PROFILE)),'max_attempts_per_http_stage':3,'article_deadline_seconds':60},'created_commit':os.getenv('RAILWAY_GIT_COMMIT_SHA','local'),'infrastructure':{'service':'Railway worker','python':__import__('platform').python_version(),'region':os.getenv('RAILWAY_REPLICA_REGION','not reported')}}
    freeze['hash']=digest(freeze)
    existing=db.scalar(select(EvaluationCampaign).where(EvaluationCampaign.name==payload['name']))
    if existing:
        if digest({k:existing.freeze[k] for k in ('inputs','suppliers','manifest')}) != digest({k:freeze[k] for k in ('inputs','suppliers','manifest')}):raise ValueError('Nombre existente con otras entradas')
        return existing
    c=EvaluationCampaign(name=payload['name'],freeze=freeze);db.add(c);db.flush()
    for i,x in enumerate(inputs):
        for profile in PROFILES:
            db.add(CampaignRun(campaign_id=c.id,profile=profile,input_key=f'{i:03}:{x["data"]["news_id"]}',split=x['split'],source=x['data'],reference=x.get('reference'),state='prepared',audit={}))
    db.commit();return c

def start(db,cid):
    c=db.scalar(select(EvaluationCampaign).where(EvaluationCampaign.id==cid).with_for_update())
    if not c:raise ValueError('Campaña no encontrada')
    if c.freeze['semantic_hashes']!=semantic_hashes() or c.freeze['versions']!=versions():raise ValueError('La versión congelada cambió; requiere otra campaña')
    if c.state=='complete':return c
    if c.state=='paused':raise ValueError('Campaña pausada: diagnosticar fallo de autenticación/contrato antes de reanudar')
    gid='campaign:'+c.id
    if not db.get(ConsumptionBudget,gid):
        db.add(ConsumptionBudget(id=gid,request_limit=c.freeze['request_estimate']['max_http_attempts_including_retries']))
        db.flush();db.add(Grant(id=gid,split='campaign',article_limit=None,budget_id=gid))
    db.flush()
    from app.queue import enqueue
    for r in db.scalars(select(CampaignRun).where(CampaignRun.campaign_id==cid).order_by(CampaignRun.input_key,CampaignRun.profile)):
        if r.state not in ('prepared','queued','running'):continue
        job=enqueue(db,'campaign:'+r.id,'campaign',{'campaign_id':cid,'run_id':r.id},2)
        if job.state=='cancelled':job.state='queued';job.attempts=0;job.error=None
        r.audit={**r.audit,'queued_at':r.audit.get('queued_at',now().isoformat())}
        r.state='queued'
    c.started_at=c.started_at or now();c.state='running';db.commit();return c

def process(db,rid,transport=None):
    # Serialise this record across lease recovery, including cache writes/commits.
    from app.db import engine
    lock=engine.connect().execution_options(isolation_level='AUTOCOMMIT')
    lock.execute(text('SELECT pg_advisory_lock(72648,hashtext(:id))'),{'id':rid})
    try:return _process(db,rid,transport)
    finally:
        lock.execute(text('SELECT pg_advisory_unlock(72648,hashtext(:id))'),{'id':rid});lock.close()

def _process(db,rid,transport=None):
    r=db.get(CampaignRun,rid);c=db.get(EvaluationCampaign,r.campaign_id)
    if r.state in ('done','review','error'):return r
    if c.state=='paused':return r
    if c.freeze['semantic_hashes']!=semantic_hashes() or c.freeze['versions']!=versions():
        r.state='error';r.result={'analysis_status':'error','is_risk':None,'urgent':None,'affected_supplier_ids':[],'error':'FROZEN_PROFILE_CHANGED'};r.completed_at=now();c.state='paused';db.commit();return r
    r.started_at=r.started_at or now();r.state='running';db.commit()
    article=SimpleNamespace(id=r.id,news_id=r.source['news_id'],context='exercise',data=r.source,generation=0,version=1,batch_id=None)
    audit={};begin=time.monotonic()
    from app.analysis import process_article
    try:
        result=process_article(db,r.id,transport=transport,run_key='campaign:'+r.id,publish=False,profile=r.profile,campaign_article=article,campaign_suppliers=c.freeze['suppliers'],campaign_grant='campaign:'+c.id,campaign_audit=audit)
    except Exception as exc:
        # Persist a null decision; never convert an exception into N.
        result={'article_id':r.id,'news_id':r.source['news_id'],'analysis_status':'error','is_risk':None,'urgent':None,'affected_supplier_ids':[],'assessments':[],'error':getattr(exc,'code','CAMPAIGN_INTERNAL_ERROR')}
    r=db.get(CampaignRun,rid);c=db.get(EvaluationCampaign,r.campaign_id)
    calls=db.scalars(select(ApiCall).where(ApiCall.run_key=='campaign:'+rid).order_by(ApiCall.created_at)).all()
    r.result=result;r.state=result['analysis_status'];r.completed_at=now()
    r.audit={**r.audit,**audit,'wall_seconds':time.monotonic()-begin,'runtime_commit':os.getenv('RAILWAY_GIT_COMMIT_SHA','local'),'new_requests':len(calls),'retries':sum(x.attempt>1 for x in calls),'usage':{k:sum(x.usage.get(k,0) for x in calls if isinstance(x.usage.get(k),(float,int))) for k in ('input_tokens','output_tokens','total_tokens')},'calls':[{'id':x.id,'stage':x.stage,'attempt':x.attempt,'status':x.status,'seconds':x.duration,'model':x.model,'at':x.created_at.isoformat(),'usage':x.usage} for x in calls]}
    error=result.get('error') or ''
    if any(x in error for x in ('401','403','400','422','CONTRACT','MODEL_MISMATCH','FROZEN_PROFILE')):c.state='paused'
    db.flush()
    pending=db.scalar(select(CampaignRun.id).where(CampaignRun.campaign_id==c.id,CampaignRun.state.in_(('prepared','queued','running'))).limit(1))
    if not pending and c.state!='paused':c.state='complete';c.completed_at=now()
    db.commit();return r

def expected_ids(label):return set(str(label.get('Affected_Supplier_IDs') or '').replace(',',';').split(';'))-{''}
def exact(label,result):return label['Is_Risk']==result['is_risk'] and label['Urgent']==result['urgent'] and expected_ids(label)==set(result['affected_supplier_ids'])

def aggregate(rows):
    valid=[r for r in rows if r.state in ('done','review') and r.result and r.result.get('is_risk') in ('Y','N')]
    labelled=[r for r in valid if r.reference]
    automatic=[r for r in valid if r.state=='done'];auto=[r for r in automatic if r.reference]
    pairs=[(r.reference,r.result) for r in labelled]
    return {'total':len(rows),'completed':len(valid),'errors':sum(r.state=='error' for r in rows),'pending':sum(r.state not in ('done','review','error') for r in rows),'labelled_completed':len(pairs),'quality':metrics(pairs) if pairs else None,'quality_limit':'Training/validation ya inspeccionados; agregado descriptivo sobre completados, fallos visibles aparte' if pairs else 'No disponible: sin etiquetas' if all(not r.reference for r in rows) else 'No disponible: sin predicciones válidas','automatic':len(automatic),'review':sum(r.state=='review' for r in valid),'automatic_rate':ratio(len(automatic),len(rows)),'review_rate':ratio(sum(r.state=='review' for r in valid),len(rows)),'automatic_errors':sum(not exact(r.reference,r.result) for r in auto) if auto else None,'automatic_labelled':len(auto),'automatic_positive':{'n':sum(r.reference['Is_Risk']=='Y' for r in auto),'errors':sum(not exact(r.reference,r.result) for r in auto if r.reference['Is_Risk']=='Y')},'automatic_negative':{'n':sum(r.reference['Is_Risk']=='N' for r in auto),'errors':sum(not exact(r.reference,r.result) for r in auto if r.reference['Is_Risk']=='N')},'automatic_risks':sum(r.reference['Is_Risk']=='Y' and exact(r.reference,r.result) for r in auto),'automatic_urgencies':sum(r.reference['Urgent']=='Y' and exact(r.reference,r.result) for r in auto),'new_requests':sum(r.audit.get('new_requests',0) for r in rows),'cache_stages':sum(len(r.audit.get('_cache_stages',[])) for r in rows),'retries':sum(r.audit.get('retries',0) for r in rows),'http_errors':sum(c.get('status')!=200 for r in rows for c in r.audit.get('calls',[])),'tokens':{k:sum(r.audit.get('usage',{}).get(k,0) for r in rows) for k in ('input_tokens','output_tokens','total_tokens')},'analysis_wall_seconds_sum':sum(r.audit.get('wall_seconds',0) for r in rows),'elapsed_seconds':(max(r.completed_at for r in rows if r.completed_at)-min(r.started_at for r in rows if r.started_at)).total_seconds() if any(r.completed_at for r in rows) else None}

def listing(db):
    return [{'id':c.id,'name':c.name,'state':c.state,'created_at':c.created_at,'started_at':c.started_at,'completed_at':c.completed_at,'profiles':list(c.freeze['versions'])} for c in db.scalars(select(EvaluationCampaign).order_by(EvaluationCampaign.created_at.desc()))]

def report(db,cid,split='training',full=False):
    c=db.get(EvaluationCampaign,cid)
    if not c:raise ValueError('Campaña no encontrada')
    rows=db.scalars(select(CampaignRun).where(CampaignRun.campaign_id==cid).order_by(CampaignRun.input_key,CampaignRun.profile)).all()
    chosen=[r for r in rows if split=='all' or (split=='labelled' and r.split in ('training','validation')) or r.split==split]
    suppliers={s['supplier_id']:s for s in c.freeze['suppliers']}
    items=[]
    for r in chosen:
        result=r.result or {};ref=r.reference
        p=set(result.get('affected_supplier_ids',[]));e=expected_ids(ref) if ref else None
        items.append({'id':r.id,'key':r.input_key,'news_id':r.source['news_id'],'headline':r.source['headline'],'source':r.source['source'],'split':r.split,'profile':r.profile,'state':r.state,'reference':ref,'result':result,'supplier_added':sorted(p-e) if e is not None else None,'supplier_omitted':sorted(e-p) if e is not None else None,'critical_errors':[{'supplier_id':sid,'criticality':suppliers[sid]['criticality'],'single_source':suppliers[sid]['single_source']} for sid in sorted(p^e if e is not None else []) if sid in suppliers],'started_at':r.started_at,'completed_at':r.completed_at,'audit':r.audit if full else {k:v for k,v in r.audit.items() if not k.startswith('_') and k!='calls'},'input':r.source if full else None})
    elapsed=(c.completed_at-c.started_at).total_seconds() if c.completed_at and c.started_at else None
    return {'id':c.id,'name':c.name,'state':c.state,'created_at':c.created_at,'started_at':c.started_at,'completed_at':c.completed_at,'elapsed_seconds':elapsed,'split':split,'freeze':c.freeze if full else {k:v for k,v in c.freeze.items() if k not in ('inputs','suppliers','materials')},'aggregate':{p:aggregate([r for r in chosen if r.profile==p]) for p in PROFILES},'progress':dict(Counter(r.state for r in rows)),'rows':items,'note':'Comparación de pipelines completos; referencias solo en evaluación privada. Test/LiveDay sin precisión. No modifica métricas/decisiones operativas ni renueva A20.'}
