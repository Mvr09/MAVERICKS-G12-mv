"""Operational human decisions. Model predictions, gold labels and exports stay immutable."""
from copy import deepcopy
from typing import Literal
from pydantic import BaseModel,Field,ConfigDict,model_validator
from sqlalchemy import select,text,func
from app.models import Article,Analysis,Supplier,HumanDecision,Incident,Alert,now
from app.importer import digest
from reference.scoring import priority
from app.settings import POLICY

class ReviewConflict(ValueError):pass

class DecisionInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    supplier_id:str
    intent:Literal['decision','note']='decision'
    generation:int=Field(ge=0)
    source_version:int=Field(ge=1)
    analysis_id:str
    source_hash:str
    case_scope_confirmed:bool=False
    previous_id:str|None=None
    association:Literal['confirmed','rejected','unknown']
    risk:Literal['Y','N']|None=None
    urgent:Literal['Y','N']|None=None
    severity:float|None=Field(default=None,ge=1,le=10)
    exposure:Literal['potential','reported']='potential'
    impact_status:Literal['active','monitoring']|None=None
    note:str=Field(min_length=8,max_length=4000)
    evidence:str=Field(default='',max_length=4000)
    evidence_source:str=Field(default='',max_length=1000)
    @model_validator(mode='after')
    def coherent(self):
        if len(self.note.strip())<8:raise ValueError('Describe una observación concreta')
        if self.case_scope_confirmed and self.association=='unknown':raise ValueError('Las dudas generales siguen abiertas mientras falte información')
        if self.association=='confirmed' and (self.risk is None or self.urgent is None):raise ValueError('Confirma riesgo y urgencia o conserva asociación por verificar')
        if self.urgent=='Y' and self.risk!='Y':raise ValueError('La urgencia requiere riesgo')
        if self.association=='confirmed' and self.risk=='Y' and self.severity is None:raise ValueError('Indica severidad humana para calcular prioridad sin inventarla')
        if self.association=='confirmed' and self.risk=='Y' and self.impact_status is None:raise ValueError('Confirma el estado del impacto por separado de la urgencia')
        if self.association!='unknown' and (len(self.evidence.strip())<8 or len(self.evidence_source.strip())<3):raise ValueError('Una decisión cerrada requiere evidencia y procedencia')
        if self.association!='confirmed' and (self.risk is not None or self.urgent is not None or self.exposure=='reported'):raise ValueError('No atribuyas riesgo o afectación a una asociación no confirmada')
        return self

def latest_analysis(db,article):
    return db.scalar(select(Analysis).where(Analysis.article_id==article.id,Analysis.generation==article.generation).order_by(Analysis.created_at.desc()))

def source_context(db,article):
    if 'source_versions'not in db.info:
        db.info['source_versions']=dict(db.execute(select(Article.origin_key,func.max(Article.version)).group_by(Article.origin_key)).all())
    latest=db.info['source_versions'].get(article.origin_key,article.version)
    obsolete=article.state=='superseded' or article.version<latest
    newest=db.scalar(select(Article.id).where(Article.origin_key==article.origin_key,Article.version==latest))if obsolete else article.id
    return {'source_obsolete':obsolete,'latest_article_id':newest}

def rows(db,article):
    if 'human_decision_rows' not in db.info:
        grouped={}
        for r,origin in db.execute(select(HumanDecision,Article.origin_key).join(Article,Article.id==HumanDecision.article_id).order_by(HumanDecision.created_at,HumanDecision.id)):
            grouped.setdefault(origin,[]).append(r)
        db.info['human_decision_rows']=grouped
    return db.info['human_decision_rows'].get(article.origin_key,[])

def current_decisions(db,article,analysis=None):
    if source_context(db,article)['source_obsolete']:return {}
    if analysis is not None: analysis_id=analysis.id
    else:
        if 'operational_analysis_ids' not in db.info:
            db.info['operational_analysis_ids']={(aid,g):rid for aid,g,rid in db.execute(select(Analysis.article_id,Analysis.generation,Analysis.id).join(Article,Article.id==Analysis.article_id).where(Analysis.generation==Article.generation).order_by(Analysis.created_at))}
        analysis_id=db.info['operational_analysis_ids'].get((article.id,article.generation))
    return {r.supplier_id:r for r in rows(db,article)if r.article_id==article.id and r.analysis_id==analysis_id and r.generation==article.generation and r.source_version==article.version and r.content_hash==article.content_hash}

def required_suppliers(result):
    return set(result.get('affected_supplier_ids',[]))|{a['supplier_id']for a in result.get('assessments',[])if a.get('needs_review') and a.get('p_link',0)>=POLICY['thresholds']['review_low']}|{d['supplier_id']for d in result.get('review_details',[])if d.get('requires_review')and d.get('relevance')=='association'and d.get('supplier_id')}

def summary(db,article,analysis=None):
    analysis=analysis or latest_analysis(db,article);latest=current_decisions(db,article,analysis);model_required=required_suppliers(analysis.result)if analysis else set();required=model_required|set(latest)
    resolved={sid for sid,r in latest.items()if r.data['association']!='unknown'}
    result=analysis.result if analysis else {}
    general=[d.get('resolution_hint')or d['code'] for d in result.get('review_details',[])if d.get('requires_review')and not d.get('supplier_id')and d.get('relevance')not in('auxiliary','priority')]
    general += [r for r in result.get('review_reasons',[]) if r not in {'event_type_confidence_low','severity_confidence_low'} and ':'not in r and not any(d.get('code')==r for d in result.get('review_details',[]))]
    general_pending=bool(result.get('analysis_status')=='review' and (general or not model_required) and not any(r.data.get('case_scope_confirmed')and r.data['association']!='unknown'for r in latest.values()))
    return {**source_context(db,article),'state':'obsolete'if source_context(db,article)['source_obsolete']else'resolved'if latest and not(required-resolved) and not general_pending else'in_verification'if latest else'pending'if result.get('analysis_status')=='review'else'not_required','updated_at':max((r.created_at.isoformat() for r in latest.values()),default=None),'general_pending':general_pending,'general_questions':general,'resolved_suppliers':sorted(resolved),'remaining_suppliers':sorted(required-resolved),'decisions':[{'supplier_id':r.supplier_id,'id':r.id,'association':r.data['association'],'risk':r.data['risk'],'urgent':r.data['urgent'],'exposure':r.data['exposure']}for r in latest.values()]}

def view(db,article):
    analysis=latest_analysis(db,article)
    return {**summary(db,article,analysis),'analysis_id':analysis.id if analysis else None,'generation':article.generation,'source_version':article.version,'source_hash':article.content_hash,'history':[{'id':r.id,'supplier_id':r.supplier_id,'article_id':r.article_id,'source_version':r.source_version,'analysis_id':r.analysis_id,'generation':r.generation,'created_at':r.created_at,'obsolete':source_context(db,article)['source_obsolete'] or r.article_id!=article.id or not analysis or r.analysis_id!=analysis.id or r.generation!=article.generation or r.content_hash!=article.content_hash or r.source_version!=article.version,**r.data}for r in reversed(rows(db,article))]}

def effective_result(db,article,result):
    """Read model facts plus human decisions for operations, NEVER evaluation/export."""
    result=deepcopy(result);latest=current_decisions(db,article)
    for sid,r in latest.items():
        d=r.data
        assessment=next((a for a in result['assessments']if a['supplier_id']==sid),None)
        if assessment is None and d['association']!='rejected':
            assessment={'supplier_id':sid,'p_link':None,'p_risk':None,'p_urgent':None,'model_probabilities_available':False,'is_risk':None,'urgent':None,'severity':None,'priority':None,'priority_band':None,'factor_values':{},'evidence_ids':[],'review_reasons':[],'impact_status':'unclear'}
            result['assessments'].append(assessment)
        if d['association']=='unknown':
            if assessment:assessment.update(needs_review=True,decision_origin='human',human_review_id=r.id)
            continue
        if assessment:assessment.update(needs_review=False,review_reasons=[],decision_origin='human',human_review_id=r.id)
        if d['association']=='rejected':
            result['affected_supplier_ids']=[s for s in result['affected_supplier_ids']if s!=sid]
            if assessment:assessment.update(is_risk='N',urgent='N')
        elif sid not in result['affected_supplier_ids']:result['affected_supplier_ids'].append(sid)
        if assessment and d['association']=='confirmed':assessment.update(is_risk=d['risk'],urgent=d['urgent'],exposure_kind=d['exposure'])
    return result

def project(db,article,record,analysis):
    """Retire this article/provider contribution only; retain original and shared evidence."""
    d=record.data;sid=record.supplier_id
    incidents=db.scalars(select(Incident).where(Incident.context==article.context,Incident.supplier_id==sid).with_for_update()).all();target=None
    for inc in incidents:
        if not any(h.get('article_id')==article.id for h in inc.history):continue
        target=inc
        previous_entry=next((h for h in reversed(inc.history) if h.get('article_id')==article.id and h.get('assessment') and not h.get('superseded')),None)
        if d['association']=='unknown':
            if previous_entry:
                inc.history=[{**h,'superseded':True,'superseded_by_human_review':record.id} if h.get('article_id')==article.id and not h.get('superseded') else h for h in inc.history]
                pending={**deepcopy(previous_entry),'superseded':False,'at':now().isoformat(),'decision_origin':'human','human_review_id':record.id,'explanation':'Verificación humana en curso; conclusión operativa pendiente.'}
                pending['assessment'].update(needs_review=True,review_reasons=['human_verification_pending'],human_review_id=record.id,decision_origin='human')
                inc.history=[*inc.history,pending];inc.revision+=1
            for alert in db.scalars(select(Alert).where(Alert.incident_id==inc.id)):
                if alert.data.get('article_id')==article.id:alert.data={**alert.data,'needs_review':True,'sound_eligible':False}
            continue
        inc.history=[{**h,'superseded':True,'superseded_by_human_review':record.id}if h.get('article_id')==article.id and not h.get('superseded')else h for h in inc.history]
        active=[h for h in inc.history if h.get('assessment')and not h.get('superseded')]
        if inc.state!='resolved':
            if active:
                newest=max(active,key=lambda h:(h.get('published_date',''),h.get('at','')));inc.state=newest['assessment'].get('impact_status','monitoring');inc.priority=max(h['assessment'].get('priority')or 0 for h in active)
            else:inc.state='superseded';inc.priority=0
        inc.revision+=1
        for alert in db.scalars(select(Alert).where(Alert.incident_id==inc.id)):
            if alert.data.get('article_id')==article.id:alert.data={**alert.data,'state':'superseded','sound_eligible':False}
    if d['association']!='confirmed' or d['risk']!='Y':return
    s=db.get(Supplier,sid).data;prior=next((a for a in analysis.result['assessments']if a['supplier_id']==sid),{})
    score=priority(is_risk=True,severity=d['severity'],criticality=s.get('criticality'),single_source=s.get('single_source'),share_category_pct=s.get('share_category_pct'),inventory_days=s.get('inventory_days'),lead_days=s.get('lead_days'),disruption_days=prior.get('duration_days'),inventory_applicability='not_applicable'if s.get('category')in('Logistics','Services')else'physical')
    # Probabilities remain original estimates; human confirmation does not make p=1.
    assessment={**prior,'supplier_id':sid,'p_link':prior.get('p_link'),'p_risk':prior.get('p_risk'),'p_urgent':prior.get('p_urgent'),'model_probabilities_available':bool(prior),'is_risk':d['risk'],'urgent':d['urgent'],'severity':d['severity'],'priority':score['priority'],'priority_band':score['band'],'factor_values':score['factors'],'needs_review':False,'review_reasons':[],'priority_requires_review':score['needs_review'],'localized_warnings':score['warnings'],'impact_status':d['impact_status'],'decision_origin':'human','human_review_id':record.id,'exposure_kind':d['exposure'],'requires_pathway_confirmation':d['exposure']=='potential'}
    entry={'article_id':article.id,'generation':article.generation,'origin_key':article.origin_key,'published_date':article.data['published_date'],'headline':article.data['headline'],'at':now().isoformat(),'assessment':assessment,'decision_origin':'human','human_review_id':record.id,'explanation':'Decisión humana registrada; '+('afectación individual confirmada por el presentador.'if d['exposure']=='reported'else'exposición potencial; entregas individuales por confirmar.'),'tokens':[]}
    if target and (target.state=='resolved' or article.data['published_date']<target.event_date):
        target.history=[*target.history,{**entry,'superseded':True,'projection_note':'No reabre incidente cerrado o más reciente'}];return
    if not target:
        target=Incident(context=article.context,supplier_id=sid,event_type=analysis.result.get('event_type')or'other',signature=digest(['human',article.id,sid]),state=assessment['impact_status'],priority=score['priority']or 0,historical_priority=score['priority']or 0,event_date=article.data['published_date'],history=[]);db.add(target);db.flush()
    target.history=[*target.history,entry];target.state='active'if any(h.get('article_id')!=article.id and not h.get('superseded') and h.get('assessment',{}).get('impact_status')=='active'for h in target.history)else assessment['impact_status'];target.event_date=article.data['published_date'];target.priority=max((h.get('assessment',{}).get('priority')or 0 for h in target.history if not h.get('superseded')),default=0);target.historical_priority=max(target.historical_priority,target.priority)
    db.add(Alert(incident_id=target.id,revision=target.revision,data={'supplier_id':sid,'supplier_name':s['name'],'article_id':article.id,'headline':article.data['headline'],'priority':target.priority,'needs_review':False,'urgent':d['urgent'],'state':target.state,'sound_eligible':False,'decision_origin':'human','human_review_id':record.id}))

def save(db,aid,body):
    db.execute(text("SELECT pg_advisory_xact_lock_shared(72642,4)"))
    article=db.scalar(select(Article).where(Article.id==aid).with_for_update())
    if not article:raise ValueError('Noticia no encontrada')
    if source_context(db,article)['source_obsolete']:raise ReviewConflict('Esta versión de la fuente fue sustituida. Abre la noticia vigente antes de decidir')
    analysis=latest_analysis(db,article)
    if not analysis or analysis.result['analysis_status']=='error':raise ReviewConflict('Completa un análisis válido antes de revisar')
    if (body.generation,body.source_version,body.analysis_id,body.source_hash)!=(article.generation,article.version,analysis.id,article.content_hash):raise ReviewConflict('La fuente o el análisis cambió. Recarga la revisión antes de decidir')
    if not db.get(Supplier,body.supplier_id):raise ValueError('Proveedor no encontrado')
    previous=current_decisions(db,article,analysis).get(body.supplier_id)
    if (previous.id if previous else None)!=body.previous_id:raise ReviewConflict('Otra decisión fue registrada. Recarga el historial antes de guardar')
    d=body.model_dump(exclude={'generation','source_version','analysis_id','previous_id','supplier_id','source_hash'});d.update(model_versions=analysis.result.get('analysis_versions',{'model':analysis.result.get('model_id'),'questions':analysis.result.get('question_version')}),human_policy='human-review-1.0.1',actor='Presentador autenticado (acceso compartido)',decision_origin='human',status='in_verification'if body.association=='unknown'else'resolved')
    if body.intent=='note':
        if not previous:raise ValueError('Registra primero una decisión o solicitud de verificación')
        d={**deepcopy(previous.data),'note':body.note,'entry_kind':'note','previous_decision_id':previous.id}
    else:d['entry_kind']='decision'
    record=HumanDecision(article_id=article.id,supplier_id=body.supplier_id,analysis_id=analysis.id,generation=article.generation,source_version=article.version,content_hash=article.content_hash,data=d);db.add(record);db.flush();db.info.pop('human_decision_rows',None);
    if body.intent!='note':project(db,article,record,analysis)
    db.flush();return record
