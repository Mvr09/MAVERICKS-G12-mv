"""Durable experiment accounting for the explicitly authorized five-hour window."""
from datetime import datetime, timezone
from pathlib import Path
import json
from sqlalchemy import select, func
from app.models import ConsumptionBudget, Grant, GrantArticle, ApiCall, Batch, Article
from app.importer import digest

ROOT=Path(__file__).resolve().parents[1]
BUDGET='autonomous-window-20261018'
START=datetime(2026,10,18,21,42,32,tzinfo=timezone.utc)
STABILIZE=datetime(2026,10,19,2,12,32,tzinfo=timezone.utc)
END=datetime(2026,10,19,2,42,32,tzinfo=timezone.utc)


def check_time():
    if datetime.now(timezone.utc)>=STABILIZE:
        raise RuntimeError('Experiment cutoff reached; stabilize and publish instead')


def ensure_grant(db):
    if not db.get(ConsumptionBudget,BUDGET):db.add(ConsumptionBudget(id=BUDGET,request_limit=1500))
    if not db.get(Grant,BUDGET):db.add(Grant(id=BUDGET,split='training',article_limit=1000,used=0,budget_id=BUDGET))
    db.flush()


def clone(db, run, key, data, order, count):
    ensure_grant(db);bh=digest([run,'development_cases'])
    batch=db.scalar(select(Batch).where(Batch.file_hash==bh))
    if not batch:batch=Batch(file_hash=bh,filename='QA_WINDOW_'+run,split='training',count=count);db.add(batch);db.flush()
    origin=run+':'+key;art=db.scalar(select(Article).where(Article.origin_key==origin))
    if not art:
        art=Article(origin_key=origin,batch_id=batch.id,context='exercise',row_order=order,
            news_id=data.get('news_id',key),data=data,content_hash=digest(data))
        db.add(art);db.flush();db.add(GrantArticle(article_id=art.id,grant_id=BUDGET));db.get(Grant,BUDGET).used+=1
    assert art.content_hash==digest(data),'Source changed; use an explicitly new experiment'
    db.commit();return art


def save(path, value):
    path=Path(path);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)


def accounting(db, run):
    calls=db.scalars(select(ApiCall).where(ApiCall.run_key==run).order_by(ApiCall.created_at)).all()
    return {'requests':len(calls),'retries':sum(c.attempt>1 for c in calls),
        'global_counter':db.scalar(select(func.count()).select_from(ApiCall)),
        'window_reserved':db.get(ConsumptionBudget,BUDGET).requests_used,
        'calls':[{'stage':c.stage,'attempt':c.attempt,'model':c.model,'status':c.status,'seconds':c.duration,
                  'at':c.created_at.isoformat(),'usage':c.usage} for c in calls]}
