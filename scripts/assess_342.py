"""Assess frozen guards, all predictions included; no network or held-out input."""
import json
from collections import Counter
from scripts.window_common import ROOT,save
from scripts.check_link_candidate import report_metrics
from app.model_metrics import percentiles


def exact(ref,p):
 return (ref['Is_Risk'],ref['Urgent'],set(x.strip()for x in (ref.get('Affected_Supplier_IDs') or '').split(';')if x.strip()))==(p['is_risk'],p['urgent'],set(p['affected_supplier_ids']))


def main():
 dev=json.loads((ROOT/'reports/private/window-risk-publication.json').read_text());fresh=json.loads((ROOT/'reports/private/window-fresh-342.json').read_text());assert dev['complete']and fresh['complete']
 pairs=[];deltas=[]
 for key,row in dev['results'].items():pairs.append((key,row.get('reference'),row['old'],row['prediction']))
 for row in fresh['results'].values():
  if row['profile']=='candidate_3_4_2':pairs.append(('fresh:'+row['case'],row['reference'],fresh['results'][row['case']+':prior_3_3']['prediction'],row['prediction']))
 new_errors=[]
 for key,ref,old,new in pairs:
  assert old['affected_supplier_ids']==new['affected_supplier_ids'],key
  assert {a['supplier_id']:a['p_urgent']for a in old['assessments']}=={a['supplier_id']:a['p_urgent']for a in new['assessments']},key
  if ref and new['analysis_status']=='done' and not exact(ref,new) and not(old['analysis_status']=='done'and not exact(ref,old)):new_errors.append(key)
  if ref and (old['is_risk'],old['urgent'],old['analysis_status'])!=(new['is_risk'],new['urgent'],new['analysis_status']):
   deltas.append({'case':key,'prior':{'risk':old['is_risk'],'urgent':old['urgent'],'status':old['analysis_status']},'candidate':{'risk':new['is_risk'],'urgent':new['urgent'],'status':new['analysis_status']},'correct':exact(ref,new)})
 assert not new_errors
 for group,ms in dev['metrics'].items():
  for k in ('risk','urgent'):
   assert ms['prediction'][k]['fp']<=ms['old'][k]['fp'];assert ms['prediction'][k]['fn']<=ms['old'][k]['fn']
 for k in ('risk','urgent'):
  assert fresh['metrics']['candidate_3_4_2'][k]['fp']<=fresh['metrics']['prior_3_3'][k]['fp'];assert fresh['metrics']['candidate_3_4_2'][k]['fn']<=fresh['metrics']['prior_3_3'][k]['fn']
 unknown=[v for v in fresh['results'].values()if v['profile']=='candidate_3_4_2' and v['reference']is None]
 assert len(unknown)==4 and all(v['prediction']['analysis_status']=='review'for v in unknown)
 assert all(not any(a.get('exposure_kind')=='reported'for a in v['prediction']['assessments'])for v in unknown)
 for row in dev['results'].values():
  if row['reference']is None and row['group']=='inspected_controls_development':assert row['prediction']['analysis_status']=='review'
 trials=[]
 for r in (dev,fresh):
  usage=Counter()
  for call in r['calls']:
   for k,v in call['usage'].items():
    if isinstance(v,(int,float))and not isinstance(v,bool):usage[k]+=v
  trials.append({'run':r['run'],'requests':r['requests'],'retries':r['retries'],'http_status':dict(Counter(str(c['status'])for c in r['calls'])),'reported_usage':dict(usage),'http_seconds_sum':sum(c['seconds']for c in r['calls']),'cached_stages':sum(len(v.get('cached_stages',[]))for v in r['results'].values()),'direct_a_b_reuse':'Development only validates stored effective A/B; fresh3.4 uses exact payload cache from3.3.'})
 report={'profile':'radar-1.0.0-candidate','versions':fresh['protocol']['versions'],'decision':'Adopt as sole selectable experimental candidate; keep default1.0.0. Improves supported partial-risk decisions and correct automation without changing matching or urgency probability. No independent RSS generalisation claim.', 'default':'1.0.0','promoted_default':False,'development':dev['metrics'],'fresh':{'authored_before_calls':True,'scorable':14,'unknown_controls':4,'metrics':fresh['metrics'],'states':{name:dict(Counter(v['prediction']['analysis_status']for v in fresh['results'].values()if v['profile']==name))for name in ('baseline','prior_3_3','candidate_3_4_2')},'latency':{name:{**percentiles([v['seconds']for v in fresh['results'].values()if v['profile']==name]),'includes_cache':True,'environment':'Local controlled run with fanout for all; not production latency or A20'}for name in ('baseline','prior_3_3','candidate_3_4_2')},'safety_passed':4,'limits':'Author-generated controls; not independent RSS accuracy. All reviewed predictions included; unknowns are not true negatives.'},'guards':{'supplier_predictions_invariant':True,'urgency_probabilities_invariant':True,'no_additional_risk_fp_or_fn':True,'no_additional_urgency_fp_or_fn':True,'no_newly_wrong_automatic_case':True,'unknowns_remain_reviewed':True,'default_unchanged':True},'changes':deltas,'consumption':{'trials':trials,'additional_new_requests':dev['requests']+fresh['requests'],'retries':dev['retries']+fresh['retries'],'counter_before':917,'counter_after':fresh['global_counter']},'remaining':{'training_risk_fn':1,'training_urgency_fp':2,'training_supplier_fp':3,'fresh_supplier_fp':1,'all_known_classification_errors_reviewed':True,'a06':'Still open; matching unchanged from3.3 and default1.0 not promoted. S003 province unknown.'}}
 save(ROOT/'reports/candidate-342-results.json',report);save(ROOT/'app/candidate_refinement.json',report)
 print(json.dumps({'decision':report['decision'],'guards':report['guards'],'requests':report['consumption']['additional_new_requests'],'fresh':fresh['metrics']['candidate_3_4_2']}))
if __name__=='__main__':main()
