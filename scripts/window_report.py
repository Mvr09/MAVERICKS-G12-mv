"""Publish only aggregates; case references/raw responses stay private."""
import json
from collections import Counter
from sqlalchemy import select
from app.db import Session
from app.models import Supplier,Material
from scripts.window_common import ROOT,save
from scripts.check_link_candidate import report_metrics
from scripts.evaluate_review_policy import summarize
from app.model_metrics import percentiles


def main():
    review=json.loads((ROOT/'reports/private/window-review.json').read_text());potential=json.loads((ROOT/'reports/private/window-matching-potential.json').read_text());final=json.loads((ROOT/'reports/private/window-final-evaluation.json').read_text());old=json.loads((ROOT/'reports/private/review-facts-development.json').read_text())
    assert potential['complete'] and final['complete']
    groups={'1.0.0':[{**v,'prediction':v['baseline']} for v in potential['results'].values() if v['group']=='training'],
        '3.0 + review1.1':[v for v in old['results'].values() if v['group']=='training'],
        '3.0 + review1.2':[v for v in review['results'].values() if v['group']=='training'],
        '3.3 + review1.2':[v for v in potential['results'].values() if v['group']=='training']}
    training={k:report_metrics(v) for k,v in groups.items()};strata={};private=[]
    with Session() as db:
        ss={s.id:s.data for s in db.scalars(select(Supplier))};materials=[m.data for m in db.scalars(select(Material))]
        for version,values in groups.items():
            c=Counter()
            for row in values:
                r=row['prediction'];ref=row['reference'];truth={x.strip() for x in ref.get('Affected_Supplier_IDs','').split(';') if x.strip()};pred=set(r['affected_supplier_ids'])
                for kind,ids in [('fn',truth-pred),('fp',pred-truth)]:
                    for sid in ids:
                        c[kind]+=1;c[kind+'_high']+=ss[sid]['criticality']=='High';c[kind+'_single_source']+=ss[sid]['single_source']=='Y'
                        if version=='3.3 + review1.2':
                            private.append({'case':row['case'],'kind':kind,'supplier':ss[sid],'materials':[m for m in materials if sid in (m['primary_id'],m['alternate_id'])],
                                'assessment':next(a for a in r['assessments'] if a['supplier_id']==sid),'action_effect':'Verify scope and facts before deciding mitigation; reviewed hypothesis, not validated affected delivery.'})
            strata[version]={k:c[k] for k in ('fn','fn_high','fn_single_source','fp','fp_high','fp_single_source')}
    trials=[]
    for f in ['window-review.json','window-matching.json','window-matching-potential.json','window-final-evaluation.json','window-risk-focus.json','window-risk-current.json']:
        r=json.loads((ROOT/'reports/private'/f).read_text());usage=Counter()
        for call in r['calls']:
            for k,v in call['usage'].items():
                if isinstance(v,(int,float)) and not isinstance(v,bool):usage[k]+=v
        trials.append({'run':r['run'],'requests':r['requests'],'retries':r['retries'],'http_statuses':dict(Counter(str(c['status']) for c in r['calls'])),
            'http_seconds_sum':sum(c['seconds'] for c in r['calls']),'reported_usage':dict(usage),
            'new_stage_requests':sum(v.get('new_requests',0) for v in r['results'].values()),
            'reuse_stages':sum(len(v.get('cache_stages',v.get('cached_stages',[])))+int(v.get('retrieval_reused',False)) for v in r['results'].values())})
    safety=[]
    for row in final['results'].values():
        if row['profile']=='candidate' and row['reference'] is None:
            p=row['prediction'];safety.append({'case':row['case'],'status':p['analysis_status'],'expected_review':row['expected_review'],
                'review_pass':p['analysis_status']=='review','reported_individual_effect':any(a.get('exposure_kind')=='reported' for a in p['assessments'])})
    all_cases = {name:dict(Counter(v['prediction']['analysis_status'] for v in final['results'].values() if v['profile']==name)) for name in ('baseline','prior','candidate')}
    latency = {name:{**percentiles([v['seconds'] for v in final['results'].values() if v['profile']==name]),'includes_cache':True,'environment':'local development, not Railway A20'} for name in ('baseline','prior','candidate')}
    report={'candidate':'radar-1.0.0-candidate','versions':potential['versions'],'default':'1.0.0','runtime_enabled':True,'promoted_default':False,
        'recommendation':'Selectable assisted discovery; do not promote. Higher recall and correct automation coexist with reviewed false associations/urgencies and two controlled risk omissions.',
        'training':training,'operational_strata':strata,'review_causes':{k:summarize(v) for k,v in groups.items() if k!='1.0.0'},
        'controlled_final':{'authored_before_calls':True,'metrics':final['metrics'],'scorable':18,'total':24,'all_case_states':all_cases,'latency':latency,'unknown_controls':safety,'all_predictions_included':True,
            'errors':{'prior':1,'candidate':0,'baseline':0},'automatic_candidate_correct':12,'automatic_candidate_total':12,'urgent_correct_automatic':4,
            'controlled_execution_guards_pass':True,'default_promotion_justified':False,'limits':'Author-generated controls are not independent evidence of real RSS generalisation. Six underdetermined controls are safety checks, not negative labels.'},
        'consumption':{'new_requests':sum(t['requests'] for t in trials),'retries':sum(t['retries'] for t in trials),'counter_before':595,'counter_after':json.loads((ROOT/'reports/private/window-risk-current.json').read_text())['global_counter'],'trials':trials,
            'maximum_window_attempts':1500,'periodic_paid_rss':False},
        'known_errors':{'training':{'risk_fn':1,'urgent_fp':2,'supplier_fp':3,'all_reviewed':True},'controlled':{'risk_fn':2,'supplier_fp':3,'all_reviewed':True}},
        'a06':'open; baseline still omits supported exposure, S003 province still unknown. Controlled S024 partial-risk recovery is not proof that N044 is solved.',
        'historical_2_2_confound':'Stored2.2 precedes duration1.1; do not attribute all differences to matching.'}
    report['controlled_final']['reuse_status']='Inspected controls: development only for subsequent candidates; original frozen3.3 comparison retained.'
    report['followup_experiments']=[{'version':'risk-focus1.0 / decision3.4','requests':6,'decision_es':'No adoptado: training conserva14revisadas y16automáticas; solo un control sintético adicional se automatiza correctamente, sin reparar omisiones de riesgo.'}, {'version':'risk-focus1.1 / review1.3','requests':9,'decision_es':'No adoptado: comprobar amenaza actual no mejora decisiones ni cobertura. Conserva dudas semánticas en interrupciones parciales y amenazas estratégicas. No se rebajan umbrales.'}]
    rss=json.loads((ROOT/'reports/window-rss-evidence.json').read_text())
    report['rss_rehearsal']={'new_requests':rss['attributed_requests'],'counter_before':rss['sync']['jev_after'],'counter_after':rss['analysis_jev_after'],'periodic_paid':False,'scope':'Railway RSS only; separate from local experiment counter','articles':[{'id':v['id'],'headline':v['headline'],'status':v['result']['status'],'risk':v['result']['risk'],'urgent':v['result']['urgent'],'suppliers':v['result']['suppliers'],'requests':v['network_requests']} for v in rss['analyses'] if v.get('complete')], 'limits':'No hay referencias independientes de precisión RSS. La noticia de fletes queda en revisión sin proveedor vinculado; la consulta manual no modifica JEV. Dos intentos anteriores fallidos están incluidos.'}
    save(ROOT/'app/window_evaluation.json',report);save(ROOT/'reports/window-candidate-results.json',report);save(ROOT/'reports/private/window-operational-errors.json',private)
    # Preserve earlier candidate evidence; add the operational candidate and its
    # review-only predecessor without rewriting any historical metrics.
    p=ROOT/'app/model_candidates.json';oldreport=json.loads(p.read_text())
    for name in ('3.0 + review1.1','3.0 + review1.2','3.3 + review1.2'):
        oldreport['metrics'][name]=training[name];oldreport['operational_strata'][name]=strata[name]
    oldreport['preferred_candidate']='radar-1.0.0-candidate · opt-in';oldreport['promoted_default']=False;oldreport['window_comparison']='window-candidate-results.json';save(p,oldreport)
    print(json.dumps({'training':training['3.3 + review1.2'],'calls':report['consumption']['new_requests'],'safety':safety,'strata':strata['3.3 + review1.2']}))
if __name__=='__main__':main()
