"""Standalone audit failures retain unknown decisions and valid historical results."""
import pytest
from sqlalchemy import create_engine,select,func
from sqlalchemy.orm import Session
from app.db import Base
from app.models import Article,Analysis
from scripts.record_experiment_failure import record_failure

def test_failure_is_unknown_and_idempotent():
 engine=create_engine('sqlite://');Base.metadata.create_all(engine)
 with Session(engine)as db:
  article=Article(origin_key='SYNTHETIC-AUDIT',context='exercise',news_id='SYNTHETIC',data={},content_hash='synthetic');db.add(article);db.commit()
  first=record_failure(db,article,run='synthetic',code='JEV_HTTP_400',profile='synthetic',model='MOCK')
  second=record_failure(db,article,run='synthetic',code='JEV_HTTP_400',profile='synthetic',model='MOCK')
  assert first.id==second.id and article.state=='error'
  assert first.result['is_risk']is None and first.result['urgent']is None
  assert db.scalar(select(func.count()).select_from(Analysis))==1

def test_failure_cannot_replace_a_valid_analysis():
 engine=create_engine('sqlite://');Base.metadata.create_all(engine)
 with Session(engine)as db:
  article=Article(origin_key='SYNTHETIC-VALID',context='exercise',news_id='SYNTHETIC',data={},content_hash='synthetic',state='done');db.add(article);db.flush()
  valid=Analysis(article_id=article.id,generation=0,request_hash='synthetic',result={'analysis_status':'done','is_risk':'Y','urgent':'N'},raw={},duration=0,cached=True);db.add(valid);db.commit()
  with pytest.raises(ValueError,match='valid prediction'):record_failure(db,article,run='synthetic',code='JEV_HTTP_400',profile='synthetic',model='MOCK')
  assert article.state=='done'and valid.result['is_risk']=='Y'
