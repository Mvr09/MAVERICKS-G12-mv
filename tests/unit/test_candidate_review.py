from copy import deepcopy
import json
from pathlib import Path
from app import candidate_review as c, review_policy
from scripts.review_scenarios import cases
from tests.helpers import answer
from tests.unit.test_review_policy import verified
from tests.unit.test_review_facts import facts


def exclusion(case, score=.95, kind='different_subject', cite=True):
    p = c.exclusion_payload(case['prediction'], case['data'], case['suppliers'], 'jev-1.13.0')
    r = answer(p)
    for key, a in r['answers'].items():
        if a['type']=='noul':a['noul']=score
        elif key.startswith('relationship_passage_'):a['choice']='e1' if cite else 'none'
        else:a.update(choice=kind,confidence=.95)
    return {'binding':review_policy.binding(case['prediction']),'version':c.EXCLUSION_VERSION,'response':r}


def test_relative_subject_resolves_exclusion_not_unknown_route_or_ambiguous_link():
    case=cases('jev-1.13.0')[1]
    assert c.apply(case['prediction'],verified(case,.1),exclusions=exclusion(case))['analysis_status']=='done'
    for opts in ({'score':.65},{'kind':'unknown_scope'},{'cite':False}):
        assert c.apply(case['prediction'],verified(case,.1),exclusions=exclusion(case,**opts))['analysis_status']=='review'
    case['prediction']['assessments'][0]['p_link']=.4
    assert c.apply(case['prediction'],verified(case,.1),exclusions=exclusion(case))['analysis_status']=='review'


def test_named_positive_identity_stays_and_unknown_global_doubt_blocks_sound():
    case=cases('jev-1.13.0')[5];r=c.apply(case['prediction'],verified(case))
    assert r['affected_supplier_ids']==['QA901'] and r['is_risk']=='N' and r['analysis_status']=='done'
    case=cases('jev-1.13.0')[0];case['prediction']['review_reasons'].append('unknown_source_integrity')
    r=c.apply(case['prediction'],verified(case))
    assert r['assessments'][0]['needs_review'] and not review_policy.alarm_decision(r['assessments'][0])['sound_eligible']


def test_prior_review_results_are_reproducible_if_available():
    path=Path('reports/private/review-facts-development.json')
    if not path.exists():return  # Private artifacts are intentionally not in Git.
    for row in json.loads(path.read_text())['results'].values():
        r=c.apply(row['before'],row['verification'],row['facts'])
        assert (r['analysis_status'],r['review_reasons'])==(row['prediction']['analysis_status'],row['prediction']['review_reasons'])
        assert [a['needs_review'] for a in r['assessments']]==[a['needs_review'] for a in row['prediction']['assessments']]


def test_exclusion_effective_payload_cannot_include_protected_labels():
    case=cases('jev-1.13.0')[1]
    for field in ('Is_Risk','Urgent','Affected_Supplier_IDs','Event_Type','Explanation'):case['data'][field]='PROTECTED-SENTINEL'
    assert 'PROTECTED-SENTINEL' not in str(c.exclusion_payload(case['prediction'],case['data'],case['suppliers'],'jev-1.13.0'))
