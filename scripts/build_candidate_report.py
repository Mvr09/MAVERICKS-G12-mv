"""Produce aggregate candidate evidence and a private operational error diagnosis."""
import json
from pathlib import Path
from collections import Counter
from sqlalchemy import select,text
from app.db import Session
from app.models import Supplier,Material,Article
from scripts.compare_stored_candidates import build
from scripts.check_link_candidate import report_metrics
ROOT=Path(__file__).resolve().parents[1]

def main():
    report=build();v3=json.loads((ROOT/'reports/private/link-3-development.json').read_text());v2=json.loads((ROOT/'reports/private/link-training-comparison.json').read_text());v4=json.loads((ROOT/'reports/private/link-4-compact-development.json').read_text())
    rows=[r for r in v3['results'].values() if r['group']=='training'];four=[r for r in v4['results'].values() if r['group']=='training']
    report['metrics']['link-4.0.1-dev']=report_metrics(four)
    groups={'1.0.0':[{**r,'prediction':r['baseline']} for r in rows], 'link-2.2.0':[r for r in v2['results'].values() if r['prediction']['question_version']=='link-2.2.0'],'link-3.0.0-dev':rows,'link-4.0.1-dev':four}
    assisted=json.loads((ROOT/'reports/private/link-3-1-development.json').read_text())
    groups['link-3.1.0-assist']=[r for r in assisted['results'].values() if r['group']=='training']
    report['metrics']['link-3.1.0-assist']=report_metrics(groups['link-3.1.0-assist'])
    report['operational_strata']={};details=[]
    with Session() as db:
        db.execute(text('SET TRANSACTION READ ONLY'));ss={s.id:s.data for s in db.scalars(select(Supplier))};materials=[m.data for m in db.scalars(select(Material))]
        for version,values in groups.items():
            counts=Counter()
            for v in values:
                y={s.strip() for s in (v['reference'].get('Affected_Supplier_IDs') or '').split(';') if s.strip()};p=set(v['prediction']['affected_supplier_ids'])
                for kind,ids in [('fn',y-p),('fp',p-y)]:
                    for sid in ids:
                        counts[kind]+=1;counts[kind+'_high']+=ss[sid]['criticality']=='High';counts[kind+'_single_source']+=ss[sid]['single_source']=='Y'
            report['operational_strata'][version]={k:counts[k] for k in ('fn','fn_high','fn_single_source','fp','fp_high','fp_single_source')}
        for v in rows:
            y={s.strip() for s in (v['reference'].get('Affected_Supplier_IDs') or '').split(';') if s.strip()};p=set(v['prediction']['affected_supplier_ids']);old=set(v['baseline']['affected_supplier_ids'])
            for kind,ids in [('lost',(old&y)-p),('new_false',(p-y)-(old-y))]:
                for sid in ids:
                    article=db.get(Article,v['prediction']['article_id']);assessment=next(a for a in v['prediction']['assessments'] if a['supplier_id']==sid)
                    details.append({'case':v['case'],'article':article.data,'kind':kind,'supplier':ss[sid],'materials':[m for m in materials if sid in (m['primary_id'],m['alternate_id'])],'assessment':assessment,'answers':{k:a for k,a in v['raw_b']['answers'].items() if k.endswith('_'+sid)}})
    (ROOT/'reports/private/candidate-operational-errors.json').write_text(json.dumps(details,ensure_ascii=False,indent=2)+'\n')
    report['selected_for']='supervised discovery/recall, not automatic mitigation or default inference'
    report['preferred_candidate']='link-3.0.0-dev';report['precision_reference']='link-2.2.0';report['default_profile']='1.0.0';report['promoted_default']=False
    report['selection_reason']='3.0 misses no High or single-source associations in training; two extra associations are reviewed, one without risk. Its missing declared sea service is operationally relevant.2.2 has fewer false links but misses oneHigh and oneSingle-source.4.0.1 restores synthetic scope but misses five associations including oneSingle-source and adds twoHigh FP. No independent evidence to promote default.'
    report['development_requests']={'total':assisted['requests'],'profile4_0':v4['previous_protocol_requests'],'profile4_0_1':v4['requests_this_profile'],'profile3_1':assisted['requests_this_profile'],'valid_cached_stages3_1':sum(len(r.get('cached_stages',[])) for r in assisted['results'].values()),'http400':1,'retry_attempts':sum(c['attempt']>1 for c in assisted['calls']),'counter_before':381,'counter_after':assisted['global_calls_after'],'maximum':228}
    report['assisted_candidate_decision']='3.1 recovers the declared maritime association and has no supplier FN, but adds a High and a Medium non-disruptive false scope. Both are reviewed/riskN. The partial-interruption synthetic remains riskN and sea diversion urgentY. Keep3.0 as development starting point; do not promote3.1 for unconfirmed scope or automatic mitigation. Next isolate affected service from commercial/geographic compatibility, with explicit factual support; no new calls in this delivery.'
    report['synthetic4_0_1']=[{'case':r['case'],'prediction':{k:r['prediction'][k] for k in ('is_risk','urgent','affected_supplier_ids','analysis_status')},'expected':{k:r['expected'].get(k) for k in ('suppliers','risk','urgent','require_review')}} for r in v4['results'].values() if r['group']=='synthetic']
    (ROOT/'reports/candidate-selection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'app/model_candidates.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'selected':report['preferred_candidate'],'default_promoted':False,'development_requests':report['development_requests']}))
if __name__=='__main__':main()
