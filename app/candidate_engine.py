"""Operational principal candidate; optional, explicit, and fully versioned."""
from app import candidate_matching as matching, candidate_review as original_review, candidate_review_focus as review
from app import candidate_risk
from app import review_support, review_facts
from app.review_policy import binding
from app.duration import durations, VERSION as DURATION_VERSION
from app.schemas import NormalizedAnalysis
from app.importer import digest

PROFILE = matching.PROFILE
VERSIONS = {'profile':PROFILE, 'matching':matching.VERSION, 'retrieval':matching.RETRIEVAL_VERSION,
    'questions':candidate_risk.QUESTIONS, 'risk':candidate_risk.VERSION, 'review':review.VERSION, 'support':review_support.VERIFIER_VERSION,
    'facts':review_facts.QUESTIONS, 'exclusion':original_review.EXCLUSION_VERSION, 'duration':DURATION_VERSION}


def run(client, article, suppliers, deadline, cached_a=None, cached_b=None):
    raw = {'_profile':PROFILE,'_versions':dict(VERSIONS)}
    pa=matching.stage_a(article.data,suppliers,client_model(client),article.context)
    if cached_a is not None:
        from app.jev import validate_response
        raw['a']=validate_response(pa,cached_a)
        raw['_retrieval_reused']=True
    else:raw['a']=client.ask(pa,'a',deadline)
    selected=matching.select_candidates(article.data,suppliers,raw['a'])
    ds=durations({**article.data,'summary':article.data.get('summary','')+' '+article.data.get('full_text','')})
    pb=matching.stage_b(article.data,selected,ds,client_model(client),article.context)
    if cached_b is not None:
        from app.jev import validate_response
        raw['b']=validate_response(pb,cached_b)
    else:raw['b']=client.ask(pb,'b',deadline) if selected else None
    base=matching.normalize(article,suppliers,raw['a'],raw['b'],ds)
    # Independently established support may already resolve association without
    # changing its probability. Reuse exact valid support; never infer it from risk.
    pre_support=None
    pre=original_review.apply(base)
    from app.settings import POLICY
    t=POLICY['thresholds']
    if any(a['p_link']>t['review_high'] and (t['review_low']<=a['p_risk']<=t['review_high'] or (a['is_risk']=='N' and any(d['supplier_id']==a['supplier_id'] and d['code']=='risk_evidence_insufficient' and d['requires_review'] for d in base['review_details']))) for a in pre['assessments']):
        pp=review_support.payload(base,article.data,suppliers,client_model(client))
        if pp['questions']:
            raw['pre_support']=client.ask(pp,'candidate_pre_support',deadline)
            pre_support={'binding':binding(base),'version':review_support.VERIFIER_VERSION,'response':raw['pre_support']}
            pre=original_review.apply(base,pre_support)
    focus=None;changes=[]
    pfocus=candidate_risk.payload(pre,article.data,suppliers,client_model(client))
    if pfocus['questions']:
        # Prior valid questions are reusable with byte-identical state/instructions;
        # only the genuinely new current-threat proposition needs a new request.
        old={**pfocus,'questions':{k:v for k,v in pfocus['questions'].items() if not k.startswith('focus_current_')}}
        extra={**pfocus,'questions':{k:v for k,v in pfocus['questions'].items() if k.startswith('focus_current_')}}
        old_response=client.ask(old,'candidate_risk_focus',deadline)
        current_response=client.ask(extra,'candidate_current_threat',deadline)
        from app.jev import validate_response
        focus=validate_response(pfocus,{'model':old_response['model'],'answers':{**old_response['answers'],**current_response['answers']},'usage':{}})
        raw['risk_focus']=focus;raw['current_threat']=current_response
        projected,changes=candidate_risk.project(pre,raw['b'],focus)
        raw['_risk_projection']=changes
        base=matching.normalize(article,suppliers,raw['a'],projected,ds)
        for change in changes:
            if change['fact_prediction_conflict']:
                base['review_details'].append({'code':'risk_fact_prediction_conflict','field':'risk','supplier_id':change['supplier_id'],'relevance':'risk','requires_review':True,'value':change['p_risk_after'],'threshold':t['risk']})
    base['question_version']=candidate_risk.QUESTIONS
    if article.context=='rss':
        reading=article.data.get('enrichment',{'status':'summary_only'})
        base['source_reading']={k:v for k,v in reading.items() if k in ('status','checked_at','source_url','text_hash','characters','http_status','reason','method')}
        if reading.get('status')!='public_text' and not article.data.get('full_text') and any(x in article.data.get('summary','') for x in ('...','…')):
            base['review_details'].append({'code':'source_text_incomplete','field':'unclassified','supplier_id':None,'relevance':'risk','requires_review':True,'value':reading.get('status'),'threshold':None})
    result=review.apply(base,focus=focus,changes=changes);support=facts=exclusions=None
    if result['analysis_status']=='review':
        pc=review_support.payload(base,article.data,suppliers,client_model(client))
        if pc['questions']:
            known={}
            if pre_support and pc['state']==pp['state'] and pc['model']==pp['model']:
                known={k:raw['pre_support']['answers'][k] for k,q in pc['questions'].items() if pp['questions'].get(k)==q}
            missing={k:q for k,q in pc['questions'].items() if k not in known}
            fresh=client.ask({**pc,'questions':missing},'candidate_support',deadline) if missing else None
            from app.jev import validate_response
            raw['support']=validate_response(pc,{'model':pc['model'],'answers':{**known,**(fresh['answers']if fresh else {})},'usage':fresh['usage']if fresh else {}})
            raw['_support_composition']={'exact_questions_reused':list(known),'new_or_cached_delta_questions':list(missing),'independent_external_corroboration':False}
            support={'binding':binding(base),'version':review_support.VERIFIER_VERSION,'response':raw['support']}
            result=review.apply(base,support,focus=focus,changes=changes)
    if result['analysis_status']=='review':
        needed={d['supplier_id'] for d in result['review_details'] if d['requires_review'] and d['code']=='urgency_support_insufficient'}
        pf=review_facts.payload(base,article.data,suppliers,client_model(client))
        # Only factual urgency checks still needed. The obsolete generic topic
        # question is replaced by supplier-relative operational exclusion.
        pf['questions']={k:v for k,v in pf['questions'].items() if k.startswith('urgency_basis_') and any(k==('urgency_basis_'+sid) or k==('urgency_basis_'+sid+'_passage') for sid in needed)}
        pe=original_review.exclusion_payload(result,article.data,suppliers,client_model(client))
        pf['questions'].update(pe['questions']);pf['state']['protocol']='radar-followup-1.0.0'
        if pf['questions']:
            raw['followup']=client.ask(pf,'candidate_followup',deadline)
            facts={'binding':binding(base),'version':review_facts.QUESTIONS,'response':raw['followup']}
            exclusions={'binding':binding(base),'version':original_review.EXCLUSION_VERSION,'response':raw['followup']}
            result=review.apply(base,support,facts,exclusions,focus,changes)
    result['analysis_versions']={**VERSIONS,'model':raw['a']['model']}
    result['analysis_profile']=PROFILE;result['matching_version']=matching.VERSION
    result['context_notes']=sorted(set(result.get('context_notes',[])+['model_check_same_source_not_independent_corroboration']))
    raw['_request_payload_hashes']={'a':digest(pa),'b':digest(pb) if selected else None}
    raw['_new_requests']=client.network_requests;raw['_cache_stages']=client.cached_stages
    raw['_cache_reuse']=getattr(client,'reuse_details',[])
    for assessment in result['assessments']:
        if assessment.get('exposure_kind')=='unknown' and not assessment['needs_review'] and assessment['supplier_id'] not in result['affected_supplier_ids']:
            assessment['exposure_kind']='excluded'
    valid={e['id'] for e in result['evidence']}
    for e in result['evidence']:
        if article.data[e['field']][e['start']:e['end']]!=e['text']:
            raise ValueError('Source evidence does not match its literal span')
    for a in result['assessments']:
        if not set(a['evidence_ids']).issubset(valid):
            raise ValueError('Unknown evidence reference')
    NormalizedAnalysis.model_validate(result)
    return result,raw


def client_model(client):
    from app.settings import settings
    return settings.jev_model
