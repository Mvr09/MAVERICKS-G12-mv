"""Cached, paired demo-selection audit. No inference, no held-out file reads."""
import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
from scripts.check_link_candidate import report_metrics
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads((ROOT/p).read_text())
def ids(r):return set(x.strip()for x in (r.get('Affected_Supplier_IDs')or'').split(';')if x.strip())
def detail(rows):
 out=report_metrics(rows);auto=[r for r in rows if r['prediction']['analysis_status']=='done'];out['automatic_breakdown']={}
 for name,key in [('risk','Is_Risk'),('urgent','Urgent')]:
  predkey='is_risk'if name=='risk'else'urgent'
  out['automatic_breakdown'][name]={'reference_positive':sum(r['reference'][key]=='Y'for r in auto),'reference_negative':sum(r['reference'][key]=='N'for r in auto),'predicted_positive':sum(r['prediction'][predkey]=='Y'for r in auto),'predicted_negative':sum(r['prediction'][predkey]=='N'for r in auto),'true_positive':out['automatic'][name]['tp'],'false_positive':out['automatic'][name]['fp'],'false_negative':out['automatic'][name]['fn'],'true_negative':out['automatic'][name]['tn']}
 out['automatic_breakdown']['suppliers']={'articles_with_reference_suppliers':sum(bool(ids(r['reference']))for r in auto),'articles_without_reference_suppliers':sum(not ids(r['reference'])for r in auto),'tp':out['automatic']['suppliers']['tp'],'fp':out['automatic']['suppliers']['fp'],'fn':out['automatic']['suppliers']['fn'],'exact':out['automatic']['suppliers']['exact']}
 return out

def main():
 previous=load('reports/private/window-matching-potential.json')['results'];current=load('reports/private/window-risk-publication.json')['results'];fresh=load('reports/private/window-fresh-342.json')['results']
 training={'1.0.0':[],'3.4.2':[]}
 for key,v in current.items():
  if v['group']!='training':continue
  assert v['reference']==previous[key]['reference']
  training['1.0.0'].append({**v,'prediction':previous[key]['baseline']});training['3.4.2'].append(v)
 assert all(len(v)==30 for v in training.values())
 controls={name:[v for v in fresh.values()if v['profile']==profile and v['reference']is not None]for name,profile in [('1.0.0','baseline'),('3.4.2','candidate_3_4_2')]};assert all(len(v)==14 for v in controls.values())
 files=['app/candidate_engine.py','app/candidate_matching.py','app/candidate_review.py','app/candidate_review_focus.py','app/candidate_risk.py','app/duration.py','app/geography.py','config/geography.json','config/risk_policy.json']
 freeze={'frozen_at':datetime.now(timezone.utc).isoformat(),'recommended_demo':'radar-1.0.0-candidate','versions':load('reports/candidate-342-results.json')['versions'],'default':'1.0.0','promote_default':False,'reason':'Previously frozen criteria explicitly retain default; controlled samples and training do not establish independent real-RSS matching reliability. Candidate improves omissions and correct automation with disclosed reviewed false associations.','calls_prepared':{'retrospective_N044_max_attempts':36,'purpose':'Frozen candidate diagnosis only; no tuning or independent validation claim.','runtime_excel':'Three training inputs through real importer/worker/export, explicitly a subset; not A20 or new model evaluation.','rss':'Reuse valid current3.4.2 result, no gratuitous reanalysis.'},'files':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()for f in files},'no_semantic_changes_after_freeze':True}
 path=ROOT/'reports/demo-selection-freeze.json'
 if path.exists():assert json.loads(path.read_text())['files']==freeze['files']
 else:path.write_text(json.dumps(freeze,ensure_ascii=False,indent=2)+'\n')
 out={'generated_at':datetime.now(timezone.utc).isoformat(),'recommendation':freeze,'samples':{'training30':{k:detail(v)for k,v in training.items()},'controlled14':{k:detail(v)for k,v in controls.items()}},'new_jev_requests_for_comparison':0,'limits':['Both samples already inspected: development/controlled retrospective comparison, never independent generalisation.','All reviewed predictions included.','Four underdetermined controls excluded from14 scorable denominators; candidate keeps all four reviewed.','Baseline semantic payloads preserved but fresh controls used state-preserving fanout; not an unmodified-default performance benchmark.']}
 (ROOT/'reports/demo-selection-comparison.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'samples':{k:{p:{'auto':m['automatic']['n'],'errors':m['automatic_joint_errors']}for p,m in v.items()}for k,v in out['samples'].items()},'new_requests':0}))
if __name__=='__main__':main()
