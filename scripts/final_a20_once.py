"""One final LiveDay measurement after source freeze; preserve every prior generation.

No training, validation, test or answer key is read. --execute is explicit.
A failed/uncertain attempt never silently starts a second measurement.
"""
import argparse,json,time,hashlib
from datetime import datetime,timezone
from io import BytesIO
from pathlib import Path
import httpx
from openpyxl import load_workbook
from app.settings import ROOT,settings

BASE='https://mavericks-g12-mv-production.up.railway.app'
PRIVATE=ROOT/'reports/private/a20-final-current.json'

def rows(data):
    book=load_workbook(BytesIO(data),read_only=True,data_only=False)
    try:return list(book.active.values)
    finally:book.close()

def stamp():return datetime.now(timezone.utc).isoformat()
def save(r):PRIVATE.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--commit',required=True);args=p.parse_args()
    freeze=json.loads((ROOT/'reports/final-candidate-freeze.json').read_text())
    for file,h in freeze['files'].items():assert hashlib.sha256((ROOT/file).read_bytes()).hexdigest()==h,file
    if not args.execute:print(json.dumps({'prepared':True,'profile':freeze['stable_profile'],'maximum_requests':84,'measurements':1}));return
    if PRIVATE.exists():raise SystemExit('Measurement already exists; do not create a second attempt')
    report={'revision':args.commit,'profile':freeze['stable_profile'],'model':'jev-1.13.0','maximum_requests':84,'started':False,'new_independent_accuracy_evaluation':False,'errors':[]}
    PRIVATE.parent.mkdir(parents=True,exist_ok=True)
    with httpx.Client(base_url=BASE,headers={'Origin':BASE},timeout=25,follow_redirects=False) as c:
        def get(path):
            r=c.get(path);r.raise_for_status();return r
        assert get('/healthz').json()['revision']==args.commit
        assert get('/api/worker').json()['compatible']
        config=get('/api/config').json();assert config['question_version']==report['profile'] and config['model']==report['model'] and not config['rss_paid_analysis']
        auth=c.post('/api/session',json={'password':settings.admin_password.get_secret_value()});assert auth.status_code==200
        c.headers['X-CSRF-Token']=auth.json()['csrf']
        try:
            batches=[b for b in get('/api/batches').json() if b['split']=='liveday' and b['count']==14]
            assert len(batches)==1,'Exactly one declared 14-row LiveDay batch required'
            batch=batches[0];bid=batch['id'];report['batch_id']=bid
            prior=get('/api/batches/'+bid+'/export.xlsx');before=rows(prior.content)
            header=list(before[0]);ni=header.index('News_ID');expected=[str(r[ni]) for r in before[1:]]
            assert len(expected)==14 and len(set(expected))==14
            article_path='/api/articles?context=exercise&origin=batch:'+bid
            old=get(article_path).json();assert len(old)==14
            report['previous_generations']={a['id']:a['generation'] for a in old}
            old_runs={a['id']:[{'generation':r['generation'],'created_at':r['created_at'],'fingerprint':hashlib.sha256(json.dumps(r['result'],sort_keys=True).encode()).hexdigest()} for r in get('/api/articles/'+a['id']+'/runs').json()] for a in old}
            previous_calls=get('/api/batches/'+bid+'/execution').json()['calls'];prior_ids={r['id'] for r in previous_calls}
            preview=c.post('/api/demo/preview',json={'selection':['batch:'+bid],'mode':'rerun','analysis_profile':report['profile']});assert preview.status_code==200
            approved=preview.json();assert approved['analysis_profile']==report['profile'] and not approved['blocked']
            report['started']=True;report['started_at']=stamp();save(report)
            start=time.monotonic()
            response=c.post('/api/demo/cleanup',json={'token':approved['token'],'confirmation':'REANALIZAR'})
            assert response.status_code==200,'Do not retry uncertain measurement POST'
            jobs=response.json()['deleted']['job_ids'];assert len(jobs)==14
            report['jobs']=jobs;save(report)
            while True:
                states=[get('/api/jobs/'+j).json() for j in jobs]
                if any(j['state']=='error' for j in states):raise RuntimeError('ANALYSIS_ERROR_STOP_NO_RETRY')
                if all(j['state']=='done' for j in states):break
                if time.monotonic()-start>300:raise RuntimeError('A20_TIMEOUT')
                time.sleep(.4)
            exported=get('/api/batches/'+bid+'/export.xlsx');received_at=stamp();elapsed=time.monotonic()-start
            actual=rows(exported.content);names=list(actual[0]);ix=names.index('News_ID')
            assert len(actual)-1==14 and [str(r[ix]) for r in actual[1:]]==expected
            for r in actual[1:]:
                assert r[names.index('Is_Risk')] in ('Y','N') and r[names.index('Urgent')] in ('Y','N')
                ids=str(r[names.index('Affected_Supplier_IDs')] or '')
                parts=[p.strip() for p in ids.split(';') if p.strip()]
                assert parts==sorted(set(parts))
            output=ROOT/'reports/private/a20-final-current.xlsx';output.write_bytes(exported.content)
            current=get(article_path).json();assert len(current)==14
            history_preserved=True
            for a in current:
                assert a['generation']==report['previous_generations'][a['id']]+1
                runs=get('/api/articles/'+a['id']+'/runs').json()
                for previous in old_runs[a['id']]:
                    assert any(r['generation']==previous['generation'] and r['created_at']==previous['created_at'] and hashlib.sha256(json.dumps(r['result'],sort_keys=True).encode()).hexdigest()==previous['fingerprint'] for r in runs)
            calls=[r for r in get('/api/batches/'+bid+'/execution').json()['calls'] if r['id'] not in prior_ids]
            assert len(calls)<=84
            assert sum((a.get('new_requests') or 0) for a in current)==len(calls)
            report.update({'export_received_at':received_at,'elapsed_to_export_seconds':elapsed,'rows':14,
                'within_300_seconds':elapsed<=300,'new_requests':len(calls),'calls':calls,
                'cached_stage_count':sum(len(a.get('cache_stages') or []) for a in current),
                'fully_cached_articles':sum(bool(a.get('cached')) for a in current),
                'history_preserved':history_preserved,'unique_ids_and_order':True,'export_http':200,
                'new_generations':{a['id']:a['generation'] for a in current},'passed':elapsed<=300,
                'timer':'time.monotonic; from rerun POST to Excel response received; includes queue/retries/download'})
            save(report)
            public={k:v for k,v in report.items() if k not in ['calls','previous_generations','new_generations','jobs','batch_id']}
            public['http_200']=sum(r['http_status']==200 for r in calls);public['retry_attempts']=sum(r['attempt']>1 for r in calls)
            (ROOT/'reports/a20-current-results.json').write_text(json.dumps(public,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps(public,ensure_ascii=False),flush=True)
        except Exception as exc:
            report['errors'].append(type(exc).__name__);report['passed']=False;save(report)
            raise
        finally:c.delete('/api/session')

if __name__=='__main__':main()
