"""Record failed standalone experiments explicitly; never manufacture negatives."""
from sqlalchemy import select
from app.models import Analysis
from app.importer import digest

def record_failure(db,article,*,run,code,profile,model,seconds=0):
 previous=db.scalar(select(Analysis).where(Analysis.article_id==article.id,Analysis.generation==article.generation))
 if previous:
  if previous.result.get('analysis_status')!='error':raise ValueError('Refuse to overwrite a valid prediction')
  return previous
 result={'article_id':article.id,'news_id':article.news_id,'context_id':article.context,'analysis_status':'error','is_risk':None,'urgent':None,'affected_supplier_ids':[],'assessments':[],'model_id':model,'question_version':profile,'policy_version':'1.0.0','error':code,'event_type':None,'evidence':[],'review_reasons':[]}
 record=Analysis(article_id=article.id,generation=article.generation,request_hash=digest([run,article.id,'recorded_failure',code]),result=result,raw={'failure_run':run,'recorded_after_audit':True,'no_inference_performed':True},duration=seconds,cached=False)
 db.add(record);article.state='error';db.commit();return record
