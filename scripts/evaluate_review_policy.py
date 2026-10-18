"""Offline policy isolation. Reads only stored training/synthetic results."""
import json
from collections import Counter, defaultdict
from pathlib import Path
from app import review_policy
from app.schemas import NormalizedAnalysis
from scripts.check_link_candidate import report_metrics

ROOT=Path(__file__).resolve().parents[1]


def cause(d):
    if d['field']=='geography':return 'association'
    if d['field']=='severity':return 'severity'
    if d['field']=='impact_state':return 'impact'
    if d['field']=='duration':return 'duration'
    if d['field']=='catalog_or_buffer':return 'missing_data'
    return d['relevance']


def summarize(rows):
    counts=Counter();articles=defaultdict(set);discarded=Counter();aux=Counter()
    for row in rows:
        r=row['prediction'];accepted=set(r['affected_supplier_ids'])
        for d in r['review_details']:
            if d['requires_review']:
                category=cause(d);counts[category]+=1;articles[category].add(row['case'])
                if d['supplier_id'] and d['supplier_id'] not in accepted:discarded[category]+=1
            else:aux[cause(d)]+=1
    return {'blocking_details':dict(counts),'articles_per_cause':{k:len(v) for k,v in articles.items()},
        'discarded_supplier_blockers':dict(discarded),'nonblocking_details':dict(aux)}


def invariant(old,new):
    for k in ('is_risk','urgent','affected_supplier_ids','question_version','policy_version'):
        assert old[k]==new[k],k
    for a,b in zip(old['assessments'],new['assessments'],strict=True):
        for k in ('supplier_id','p_link','p_risk','p_urgent','is_risk','urgent','severity','priority','priority_band','impact_status','duration_days','factor_values'):
            assert a[k]==b[k],k


def main():
    source=json.loads((ROOT/'reports/private/link-3-development.json').read_text())
    rows=[v for v in source['results'].values() if v['group']=='training'];assert len(rows)==30
    after=[];private=[]
    for v in rows:
        p=review_policy.apply(v['prediction']);invariant(v['prediction'],p);NormalizedAnalysis.model_validate(p)
        after.append({**v,'prediction':p})
        private.append({'case':v['case'],'reference':v['reference'],'prediction_before':v['prediction'],
            'policy_only':p,'omitted':sorted({s.strip() for s in (v['reference'].get('Affected_Supplier_IDs') or '').split(';') if s.strip()}-set(p['affected_supplier_ids']))})
    report={'policy_version':review_policy.VERSION,'question_version':'link-3.0.0-dev',
        'hypothesis':'Localize priority uncertainty, preserve uncertain association/risk/urgency/exclusion; factual support verification is a separate step.',
        'sample':'30 training; all predictions including reviewed; no held-out evaluation',
        'before':report_metrics(rows),'policy_only':report_metrics(after),'causes_before':summarize(rows),
        'causes_policy_only':summarize(after),'prediction_changes':0,'new_requests':0}
    (ROOT/'reports/review-policy-isolation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'reports/private/review-policy-diagnosis.json').write_text(json.dumps(private,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
