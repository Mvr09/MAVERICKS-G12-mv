"""Operational principal candidate; optional, explicit, and fully versioned."""
from app import candidate_matching as matching, candidate_review as review
from app import review_support, review_facts
from app.review_policy import binding
from app.duration import durations, VERSION as DURATION_VERSION
from app.schemas import NormalizedAnalysis
from app.importer import digest

PROFILE = matching.PROFILE
VERSIONS = {'profile':PROFILE, 'matching':matching.VERSION, 'retrieval':matching.RETRIEVAL_VERSION,
    'questions':matching.VERSION, 'review':review.VERSION, 'support':review_support.VERIFIER_VERSION,
    'facts':review_facts.QUESTIONS, 'exclusion':review.EXCLUSION_VERSION, 'duration':DURATION_VERSION}


def run(client, article, suppliers, deadline, cached_a=None):
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
    raw['b']=client.ask(pb,'b',deadline) if selected else None
    base=matching.normalize(article,suppliers,raw['a'],raw['b'],ds)
    if article.context=='rss':
        reading=article.data.get('enrichment',{'status':'summary_only'})
        base['source_reading']={k:v for k,v in reading.items() if k in ('status','checked_at','source_url','text_hash','characters','http_status','reason','method')}
        if reading.get('status')!='public_text' and not article.data.get('full_text') and any(x in article.data.get('summary','') for x in ('...','…')):
            base['review_details'].append({'code':'source_text_incomplete','field':'unclassified','supplier_id':None,'relevance':'risk','requires_review':True,'value':reading.get('status'),'threshold':None})
    result=review.apply(base);support=facts=exclusions=None
    if result['analysis_status']=='review':
        pc=review_support.payload(base,article.data,suppliers,client_model(client))
        if pc['questions']:
            raw['support']=client.ask(pc,'candidate_support',deadline)
            support={'binding':binding(base),'version':review_support.VERIFIER_VERSION,'response':raw['support']}
            result=review.apply(base,support)
    if result['analysis_status']=='review':
        needed={d['supplier_id'] for d in result['review_details'] if d['requires_review'] and d['code']=='urgency_support_insufficient'}
        pf=review_facts.payload(base,article.data,suppliers,client_model(client))
        # Only factual urgency checks still needed. The obsolete generic topic
        # question is replaced by supplier-relative operational exclusion.
        pf['questions']={k:v for k,v in pf['questions'].items() if k.startswith('urgency_basis_') and any(k==('urgency_basis_'+sid) or k==('urgency_basis_'+sid+'_passage') for sid in needed)}
        pe=review.exclusion_payload(result,article.data,suppliers,client_model(client))
        pf['questions'].update(pe['questions']);pf['state']['protocol']='radar-followup-1.0.0'
        if pf['questions']:
            raw['followup']=client.ask(pf,'candidate_followup',deadline)
            facts={'binding':binding(base),'version':review_facts.QUESTIONS,'response':raw['followup']}
            exclusions={'binding':binding(base),'version':review.EXCLUSION_VERSION,'response':raw['followup']}
            result=review.apply(base,support,facts,exclusions)
    result['analysis_versions']={**VERSIONS,'model':raw['a']['model']}
    result['analysis_profile']=PROFILE;result['matching_version']=matching.VERSION
    result['context_notes']=sorted(set(result.get('context_notes',[])+['model_check_same_source_not_independent_corroboration']))
    raw['_request_payload_hashes']={'a':digest(pa),'b':digest(pb) if selected else None}
    raw['_new_requests']=client.network_requests;raw['_cache_stages']=client.cached_stages
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
