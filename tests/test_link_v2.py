"""Independent synthetic geography and association regressions; mock provider."""
import json
import httpx
from sqlalchemy import select
from app.analysis import process_article
from app.db import Session
from app.models import Supplier
from app.geography import location, retrieval_hints
from app.link_questions import stage_a, stage_b, select_candidates, VERSION
from app.settings import settings
from tests.helpers import synthetic


def mock_response(p, *, identity=None, exposure=None, candidates=None, risk=.8, urgent=.1, auxiliary_conf=.95, evidence=True, support=.98):
    identity, exposure, candidates = identity or {}, exposure or {}, candidates or {}
    out={}
    for key,q in p['questions'].items():
        sid=key.rsplit('_',1)[-1]
        if q['type']=='noul':
            value = risk if key=='article_threat' else support if key.startswith(('association_support_','risk_support_')) else .98 if key=='scope_coverage' else candidates.get(sid,.02) if key.startswith('candidate_') else identity.get(sid,.02) if key.startswith('identity_') else exposure.get(sid,.02) if key.startswith(('exposure_','area_','operation_')) else risk if key.startswith('risk_') else urgent
            out[key]={'type':'noul','noul':value};continue
        if q['type']=='score':
            out[key]={'type':'score','score':6.,'confidence':auxiliary_conf,'probabilities':{str(i):float(i==6) for i in range(len(q['criteria']))},'legend':{str(i):v for i,v in enumerate(q['criteria'])}};continue
        choice = 'natural_disaster' if key=='event_type' else 'active' if key=='event_state' or key.startswith('impact_state_') else 'supported' if key.startswith('scope_') and max(identity.get(sid,.02),exposure.get(sid,.02))>=.5 else 'excluded' if key.startswith('scope_') else ('e1' if evidence else 'none') if key.startswith(('evidence_','link_evidence_')) else 'unknown'
        conf=auxiliary_conf if key in ('event_type','event_state') or key.startswith(('impact_state_','duration_')) else .98
        out[key]={'type':'choice','choice':choice,'confidence':conf,'probabilities':{k:float(k==choice) for k in q['criteria']}}
    return {'model':p['model'],'answers':out,'usage':{'input_tokens':1,'output_tokens':1}}


def run(db, headline, **values):
    a=synthetic(db,headline,'MOCK independent article for test.')
    seen=[]
    def fetch(r):
        p=json.loads(r.content);seen.append(p)
        return httpx.Response(200,json=mock_response(p,**values))
    return process_article(db,a.id,httpx.MockTransport(fetch),profile=VERSION,run_key="MOCK:"+a.id),seen


def test_geographic_provenance_and_aliases_do_not_invent_region():
    with Session() as db:
        suppliers={s.id:s.data for s in db.scalars(select(Supplier))}
        assert {p['admin1']['name'] for p in location(suppliers['S003'])['places']}=={'Jiangsu','Zhejiang'}
        assert location(suppliers['S017'])['status']=='ambiguous'
        for sid,text in [('S034','MOCK Bangalore event'),('S040','MOCK Tanger event'),('S019','MOCK Łódź event')]:
            hints=retrieval_hints({'headline':text},suppliers[sid])
            assert any(h['kind']=='city' and h['source_url'].startswith('https://www.geonames.org/') for h in hints)
        assert any(h['kind']=='region' for h in retrieval_hints({'headline':'MOCK Zhejiang outage'},suppliers['S024']))


def test_final_exposure_can_recover_low_initial_candidate_without_urgent_shortcut():
    with Session() as db:
        result,payloads=run(db,'MOCK Zhejiang industrial interruption',exposure={'S024':.91},risk=.8,urgent=.1)
        a=result['assessments'][[x['supplier_id'] for x in result['assessments']].index('S024')]
        assert a['p_candidate']==.02 and a['p_link']==.91
        assert result['affected_supplier_ids']==['S024']
        assert result['is_risk']=='Y' and result['urgent']=='N'
        assert 'geography' in payloads[0]['state']['suppliers'][0]
        assert len([k for k in payloads[0]['questions'] if k.startswith('candidate_')])==40
        assert 'area_S024' in payloads[1]['questions'] and 'operation_S024' in payloads[1]['questions']


def test_high_conditional_risk_never_creates_link_and_auxiliary_noise_does_not_review_rejection():
    with Session() as db:
        result,_=run(db,'MOCK harmless conference in Bangalore',risk=.99,urgent=.99,auxiliary_conf=.2)
        assert result['affected_supplier_ids']==[]
        assert result['is_risk']==result['urgent']=='N'
        assert result['analysis_status']=='done'
        assert result['context_notes']
        assert all(not d['requires_review'] for d in result['review_details'])


def test_positive_identity_needs_link_and_negative_risk_evidence_before_clearing_review():
    with Session() as db:
        for evidence,status in [(True,'done'),(False,'review')]:
            result,_=run(db,'MOCK Sunrise BioChem positive expansion',identity={'S001':.96},risk=.02,urgent=.1,auxiliary_conf=.2,evidence=evidence)
            assert result['affected_supplier_ids']==['S001']
            assert result['is_risk']==result['urgent']=='N'
            assert result['analysis_status']==status


def test_ambiguous_geography_requires_review_and_labels_never_enter_effective_payload():
    with Session() as db:
        a=synthetic(db,'MOCK event in Zhejiang factories')
        a.data={**a.data,**{k:'PROTECTED_SENTINEL' for k in ['Is_Risk','Urgent','Affected_Supplier_IDs','Event_Type','Explanation']}}
        db.commit();payloads=[]
        def fetch(r):
            p=json.loads(r.content);payloads.append(p)
            return httpx.Response(200,json=mock_response(p,exposure={'S003':.93}))
        result=process_article(db,a.id,httpx.MockTransport(fetch),profile=VERSION)
        assert 'geography_requires_review:S003' in result['review_reasons']
        assert 'PROTECTED_SENTINEL' not in json.dumps(payloads)
        assert result['analysis_status']=='review'


def test_profile_is_pinned_in_signed_preview_and_persistent_job_history():
    from app.demo import preview,cleanup
    from app.models import Analysis,Article,Job
    from app.auth import codec
    with Session() as db:
        a=synthetic(db,'MOCK version preservation')
        from tests.helpers import answer
        old=process_article(db,a.id,httpx.MockTransport(lambda r:httpx.Response(200,json=answer(json.loads(r.content),linked=('S001',)))))
        token=preview(db,['article:'+a.id],'rerun',VERSION)['token']
        assert codec().loads(token)['analysis_profile']==VERSION
        out=cleanup(db,token);db.commit()
        job=db.get(Job,out['job_ids'][0])
        assert job.payload['analysis_profile']==VERSION
        assert db.get(Article,a.id).generation==1
        assert db.scalar(select(Analysis.result).where(Analysis.article_id==a.id))==old


def test_auxiliary_category_never_hides_weak_support_and_http_errors_redact_secrets():
    from app.jev import safe_http_diagnostic
    from pydantic import SecretStr
    from unittest.mock import patch
    with patch.object(settings,'typesafe_api_key',SecretStr('MOCK-PRIVATE-CREDENTIAL')):
        error=safe_http_diagnostic(httpx.Response(400,json={'error':{'code':'input_too_long','message':'MOCK-PRIVATE-CREDENTIAL omitted'}}))
        assert error['code']=='input_too_long'
        assert 'MOCK-PRIVATE-CREDENTIAL' not in json.dumps(error)
    with Session() as db:
        result,_=run(db,'MOCK Sunrise BioChem favourable approval',identity={'S001':.96},risk=.02,auxiliary_conf=.2,support=.4)
        assert result['analysis_status']=='review'
        assert 'association_support_insufficient:S001' in result['review_reasons']
        assert 'risk_evidence_insufficient:S001' in result['review_reasons']
