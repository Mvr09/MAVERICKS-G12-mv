"""Offline inbox retrieval diagnostics on stored training only; never classification."""
import json,time
from pathlib import Path
from collections import Counter
from sqlalchemy import select
from sqlalchemy.engine import make_url
from app.db import Session,engine
from app.models import Article,Supplier
from app.relevance import hints
ROOT=Path(__file__).resolve().parents[1]
def main():
 assert make_url(str(engine.url)).database=='radar_link_development'
 stored=json.loads((ROOT/'reports/private/window-risk-publication.json').read_text())['results'];tp=fp=fn=0;levels=Counter();rows=[];start=time.monotonic()
 with Session() as db:
  ss=[s.data for s in db.scalars(select(Supplier).order_by(Supplier.id))];assert len(ss)==40;catalog=json.dumps(ss,sort_keys=True)
  for row in stored.values():
   if row['group']!='training':continue
   a=db.get(Article,row['prediction']['article_id']);r=hints(a.data['headline'],a.data['summary'],catalog);pred={v['supplier_id']for v in r['suppliers']};truth={s.strip()for s in(row['reference'].get('Affected_Supplier_IDs')or'').split(';')if s.strip()};tp+=len(pred&truth);fp+=len(pred-truth);fn+=len(truth-pred);levels[r['level']]+=1;rows.append({'case':row['case'],'candidate_ids':sorted(pred),'reference_ids':sorted(truth),'reasons':r['reasons']})
  synthetic=[('regional','Zhejiang power maintenance','Controlled regional exposure, no supplier named.','geography'),('name_positive',ss[0]['name']+' receives an award','Positive mention, no risk implied.','named'),('unrelated','Namibia forest fire','No connection with the supplied catalog.','none'),('country_only','China economic outlook','Only country mentioned, no operations.','none'),('sea_route','Asia-Europe container freight rates','Controlled pricing news, no delivery impact established.','service'),('rail_route','Asia-Europe rail freight booking','Controlled rail market news.','service'),('harmless_city','Mainz university seminar','Academic event, no industrial interruption.','geography')]
  controls=[]
  for name,head,text,expected in synthetic:
   r=hints(head,text,catalog);assert r['level']==expected,(name,r);controls.append({'case':name,'expected_retrieval':expected,'actual':r['level'],'passed':True})
 out={'version':'inbox-retrieval-1.0.0','scope':'30 stored training, all reviewed included; seven controlled retrieval-only development probes. No validation/test/LiveDay.','training':{'n':len(rows),'candidate_pair_tp':tp,'candidate_pair_fp':fp,'candidate_pair_fn':fn,'precision':tp/(tp+fp)if tp+fp else None,'recall':tp/(tp+fn)if tp+fn else None,'levels':dict(levels)},'synthetic':controls,'new_jev_requests':0,'classification_prediction_changes':0,'priority_formula_changes':0,'seconds_offline':time.monotonic()-start,'limits':'Geography-only candidates include innocuous events and are explicitly hypotheses. Pair FP/FN measure retrieval only, not risk/urgency or final supplier decisions. No generalisation claim or before/after classifier gain.'}
 (ROOT/'reports/inbox-retrieval-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');(ROOT/'reports/private/inbox-retrieval-rows.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
