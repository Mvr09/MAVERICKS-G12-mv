"""Authorized initial check: at most three training articles, persisted grant.
Stops on first error to diagnose rather than spending the remainder blindly.
No labels or response bodies are written to the report.
"""
import json,time
from sqlalchemy import select
from app.db import Session
from app.models import Batch,Article,ApiCall,Grant,Job,now
from app.queue import enqueue_batch
from app.analysis import process_article
from app.settings import ROOT

def main():
    started=time.monotonic();reports=[]
    with Session() as db:
        b=db.scalar(select(Batch).where(Batch.split=='training'))
        jobs=enqueue_batch(db,b.id);db.commit()
    for jid in jobs:
        with Session() as db:
            j=db.get(Job,jid);a=db.get(Article,j.payload['article_id'])
            result=process_article(db,a.id)
            j.state='error' if result['analysis_status']=='error' else 'done';j.error=result['error'];db.commit()
            calls=db.scalars(select(ApiCall).where(ApiCall.article_id==a.id).order_by(ApiCall.created_at)).all()
            reports.append({'news_id':a.news_id,'status':result['analysis_status'],'error':result['error'],'model':result['model_id'],'requests':[{'stage':c.stage,'attempt':c.attempt,'http_status':c.status,'seconds':round(c.duration,3),'model':c.model,'usage':c.usage} for c in calls]})
            if result['analysis_status']=='error':break
    with Session() as db:used=db.get(Grant,'initial-training-3').used
    report={'environment':'local development; not Railway','checked_at':now().isoformat(),'authorized_article_limit':3,'reserved_articles':used,'seconds':round(time.monotonic()-started,3),'articles':reports}
    (ROOT/'reports/jev-local.json').write_text(json.dumps(report,indent=2,ensure_ascii=False));print(json.dumps(report,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
