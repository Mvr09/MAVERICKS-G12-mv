"""Controlled synthetic BASE decisions; only support verification is real JEV.
These are policy safety controls, never classifier accuracy measurements.
"""
from types import SimpleNamespace
from tests.helpers import answer
from app import link_candidate
from app.duration import durations

SUPPLIER = {'supplier_id':'QA901', 'name':'QA Vials Madrid', 'country':'Spain',
    'city':'Madrid', 'category':'Primary packaging', 'material':'Glass vials',
    'criticality':'High', 'single_source':'Y', 'alternate_id':None,
    'lead_days':20, 'inventory_days':30, 'share_category_pct':30}


def cases(model):
    scenarios = [
        ('urgent_secondary', 'QA Vials Madrid factory destroyed by fire', 'QA Vials Madrid has halted all production after a fire. Immediate buyer coordination is required. Recovery date is unknown.', .95, .95, .95, False),
        ('irrelevant_macro', 'Swiss franc strengthens against euro', 'The Swiss franc exchange rate rose this morning. No production or delivery disruption is reported.', .05, .05, .05, False),
        ('unknown_route', 'Asia-Europe sea freight suspended', 'Sea freight between Asia and Europe is suspended. Rail services are operating normally.', .1, .95, .95, True),
        ('partial_negative', 'QA Vials Madrid output reduced by half', 'QA Vials Madrid reports half of production capacity offline for ten days. Shipments may be delayed.', .95, .1, .1, True),
        ('urgency_uncertain', 'QA Vials Madrid factory interrupted', 'QA Vials Madrid production is interrupted for two days while safety checks are conducted. No deliveries have yet been missed.', .95, .95, .53, True),
        ('positive_named', 'QA Vials Madrid expands approved capacity', 'QA Vials Madrid received approval for expanded capacity. Production and deliveries continue normally.', .95, .05, .05, False),
    ]
    out=[]
    for name,headline,summary,pl,pr,pu,review in scenarios:
        s=dict(SUPPLIER)
        if name=='unknown_route':s.update(category='Logistics',material='General freight services',inventory_days=None)
        data={'news_id':'SYN-REVIEW-'+name,'headline':headline,'summary':summary,
            'source':'SINTÉTICO CONTROLADO · base MOCK; soporte JEV real', 'published_date':'2026-10-18T12:00:00+00:00', 'context_id':'exercise'}
        art=SimpleNamespace(id='SYN-REVIEW-'+name,news_id=data['news_id'],context='exercise',data=data)
        aa=answer(link_candidate.stage_a(data,[s],model));bb=answer(link_candidate.stage_b(data,[s],durations(data),model),risk=pr,urgent=pu)
        sid=s['supplier_id']
        for key,val in {'identity':pl,'area':pl,'operation':.9,'inclusion_support':.95,'exclusion_support':.1,'risk_support':.2}.items():
            bb['answers'][key+'_'+sid]['noul']=val
        bb['answers']['impact_state_'+sid].update(choice='active' if pr>=.5 else 'positive',confidence=.95)
        if name=='urgent_secondary':bb['answers']['severity_'+sid]['confidence']=.2
        pred=link_candidate.normalize(art,[s],aa,bb,durations(data))
        out.append({'group':'controlled_policy','case':name,'data':data,'suppliers':[s],
            'prediction':pred,'expected_review':review,'expected_sound':name=='urgent_secondary'})
    return out
