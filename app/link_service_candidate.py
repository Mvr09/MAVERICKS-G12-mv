"""Internal candidate: location exposure and explicit catalog service are separate.
Never imported by production analysis; baseline and2.2 remain reproducible.
"""
from copy import deepcopy
from app import link_candidate as previous, link_questions, link_analysis
from app.settings import POLICY
VERSION='link-4.0.0-dev'


def stage_a(article,suppliers,model):
    p=previous.stage_a(article,suppliers,model)
    p['state']['association_protocol']['version']=VERSION
    return p


select_candidates=previous.select_candidates


def stage_b(article,suppliers,durations,model):
    p=previous.stage_b(article,suppliers,durations,model)
    calibrated=link_questions.stage_b(article,suppliers,durations,model)
    p['state']['association_protocol']['version']=VERSION
    for s in suppliers:
        sid=s['supplier_id'];q=p['questions'];subject=q['area_'+sid]['instructions'].copy();subject.pop('question')
        def noul(name,text):q[name+'_'+sid]={'type':'noul','instructions':{**subject,'question':text}}
        noul('area', 'Does the article explicitly cover the catalog city/region as an affected industrial area, using supplied geographic facts? This is SITE scope, not a transport route. A generic river/corridor mention does not prove a manufacturer uses that route. Alternatives are not additional sites. Do not choose an unknown province. Service corridors are evaluated separately.')
        noul('operation', 'Is the described supplier activity itself within the affected class of operations? Regional industrial output restrictions may expose compatible manufacturing without naming each company. Chemical shippers/distributors do not automatically include glass manufacturers or every upstream/downstream industry. Do not invent a factory, input dependency, transport mode or shipping route. Harmless city events are unrelated.')
        noul('service_scope', 'Does the catalog explicitly describe a SERVICE whose route AND mode or operational scope match the reported disruption? A material such as Asia to Europe sea freight explicitly declares that corridor and mode; a city address is not the service route. Sea disruption does not expose rail on the same corridor. Generic goods/distribution do not prove river/barge transport. False if no relevant service is declared. This establishes potential service exposure, not a shipment or company damage.')
        noul('risk_support', 'Conditionally on a supported identity or operational scope, do article facts support deciding whether the declared activity faces a potential continuity or strategic threat? A concrete reduced-output/delivery-delay fact supports a threat without proof of an actual stockout or Helixa shipment. Positive/harmless facts can support no threat. Missing facts about the event itself mean insufficient support. This answer cannot establish association.')
        for field in ('risk','urgent'):q[field+'_'+sid]=deepcopy(calibrated['questions'][field+'_'+sid])
    return p


def normalize(article,suppliers,a,b,durations):
    # Adapter to the unchanged2.2 normalizer. Raw B is never mutated. The virtual
    # area/operation pair encodes the documented independent scope composition.
    adapted=deepcopy(b) if b else None
    components={}
    if adapted:
        bb=adapted['answers']
        for s in suppliers:
            sid=s['supplier_id']
            if 'identity_'+sid not in bb:continue
            site=min(bb['area_'+sid]['noul'],bb['operation_'+sid]['noul'])
            service=bb['service_scope_'+sid]['noul'];exposure=max(site,service)
            pl=max(bb['identity_'+sid]['noul'],exposure)
            bb['area_'+sid]={'type':'noul','noul':exposure};bb['operation_'+sid]={'type':'noul','noul':1.0}
            bb['association_support_'+sid]=bb[('inclusion_support_' if pl>=POLICY['thresholds']['link'] else 'exclusion_support_')+sid]
            components[sid]=(site,service)
    result=link_analysis.normalize(article,suppliers,a,adapted,durations)
    result['question_version']=VERSION
    result['context_notes'].append('scope_composition:max(identity,min(site,operation),declared_service)')
    for sid,(site,service) in components.items():
        result['review_details'].append({'code':'scope_components','field':'exposure_basis','supplier_id':sid,'relevance':'auxiliary','requires_review':False,'value':f'site={site};declared_service={service}','threshold':None})
    return result
