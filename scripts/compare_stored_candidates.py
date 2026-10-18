"""Offline training comparison. No DB, Excel, API or held-out inputs."""
import json
from pathlib import Path
from scripts.check_link_candidate import report_metrics
ROOT=Path(__file__).resolve().parents[1]

def build():
    v3=json.loads((ROOT/'reports/private/link-3-development.json').read_text())
    v2=json.loads((ROOT/'reports/private/link-training-comparison.json').read_text())
    rows=[r for r in v3['results'].values() if r['group']=='training']
    second=[r for r in v2['results'].values() if r['prediction']['question_version']=='link-2.2.0']
    assert len(rows)==len(second)==30
    ref=lambda y: (y['Is_Risk'],y['Urgent'],sorted(s.strip() for s in (y.get('Affected_Supplier_IDs') or '').split(';') if s.strip()))
    expected={r['case']:ref(r['reference']) for r in rows}
    assert all(expected[r['news_id']]==ref(r['reference']) for r in second)
    groups={'1.0.0':[{**r,'prediction':r['baseline']} for r in rows], 'link-2.2.0':second,'link-3.0.0-dev':rows}
    report={'scope':'30 identical training references, every prediction including review','independent_evaluation':False,
      'metrics':{version:report_metrics(values) for version,values in groups.items()},'new_requests':0,
      'comparability':'Stored2.2 predates duration-1.1.0; baseline and3.0 here use duration-1.1.0. Same reference set/model/policy, different questions and input snapshots. Descriptive comparison, not isolated causal estimate.',
      'sources':['private/link-3-development.json','private/link-training-comparison.json']}
    for version,values in groups.items():
      m=report['metrics'][version];m['automatic_positive_risk_cases']=sum(r['prediction']['analysis_status']=='done' and r['reference']['Is_Risk']=='Y' for r in values)
    (ROOT/'reports/stored-candidates-comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report
if __name__=='__main__': print(json.dumps(build()['metrics'],ensure_ascii=False))
