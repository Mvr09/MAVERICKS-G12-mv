"""Synthetic inputs only: isolate the added facts from risk/urgency instructions."""
from types import SimpleNamespace
from copy import deepcopy
from app import stable_geography as geo
from reference import jev_requests as original
from tests.unit.test_support_contract import SUPPLIER


def test_exact_original_questions_and_catalog_fields_are_preserved():
    suppliers = [dict(SUPPLIER, supplier_id=f'QA{i:03}') for i in range(40)]
    article = {'headline': 'MOCK reduced power in Zhejiang', 'summary': 'MOCK for two days',
        'Is_Risk': 'DO_NOT_SEND', 'Affected_Supplier_IDs': 'DO_NOT_SEND'}
    for old, new, args in [(original.stage_a, geo.stage_a, (article, suppliers, 'jev-1.13.0')),
                            (original.stage_b, geo.stage_b, (article, suppliers, [], 'jev-1.13.0'))]:
        before = old(*args); after = new(*args)
        assert before['questions'] == after['questions']
        assert len(after['state']['suppliers']) == 40
        for a, b in zip(before['state']['suppliers'], after['state']['suppliers']):
            assert a == {k:v for k,v in b.items() if k != 'geography'}
        assert 'DO_NOT_SEND' not in str(after)
        assert after['state']['suppliers'][0]['geography']['places'][0]['admin1']['name'] == 'Zhejiang'


def test_ambiguous_province_is_never_selected_and_missing_fact_does_not_set_risk():
    s=dict(SUPPLIER, supplier_id='QA001', city='Taizhou')
    article=SimpleNamespace(data={'headline':'MOCK factories in Zhejiang reduce output'})
    base={'question_version':'1.0.0','analysis_status':'done','is_risk':'N','urgent':'N',
        'affected_supplier_ids':[],'review_reasons':[],'assessments':[]}
    out=geo.annotate(deepcopy(base),article,[s])
    assert out['is_risk']==out['urgent']=='N' and out['affected_supplier_ids']==[]
    assert out['analysis_status']=='review'
    assert 'operational_province_unknown:QA001' in out['context_notes']
    payload=geo.stage_a(article.data,[s],'jev-1.13.0')
    assert {p['admin1']['name'] for p in payload['state']['suppliers'][0]['geography']['places']}=={'Jiangsu','Zhejiang'}


def test_unrelated_geography_does_not_create_a_relationship_or_unknown_province_warning():
    s=dict(SUPPLIER, supplier_id='QA001', city='Taizhou')
    article=SimpleNamespace(data={'headline':'MOCK harmless film festival in Oslo'})
    result={'analysis_status':'done','is_risk':'N','urgent':'N','affected_supplier_ids':[], 'review_reasons':[], 'assessments':[]}
    geo.annotate(result,article,[s])
    assert result['analysis_status']=='done' and not result['context_notes']
