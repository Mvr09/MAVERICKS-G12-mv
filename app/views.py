from sqlalchemy import select
from app.models import Supplier, Material, Article, Analysis, Incident, Source, Batch, now

def current(incident):
    return max((h for h in incident.history if 'assessment' in h),key=lambda h:h.get('published_date',''),default={})

def articles_view(db,context='exercise'):
    articles=db.scalars(select(Article).where(Article.context==context).order_by(Article.fetched_at.desc(),Article.row_order).limit(500)).all()
    out=[]
    for a in articles:
        result=db.scalar(select(Analysis).where(Analysis.article_id==a.id).order_by(Analysis.created_at.desc()))
        out.append({'id':a.id,'batch_id':a.batch_id,'state':a.state,'version':a.version,'fetched_at':a.fetched_at,'source_id':a.source_id,**a.data,'analysis':result.result if result else None,'cached':result.cached if result else False})
    return out

def suppliers_view(db,context='exercise'):
    materials=[m.data for m in db.scalars(select(Material)).all()]
    incidents=db.scalars(select(Incident).where(Incident.context==context)).all()
    out=[]
    for s in db.scalars(select(Supplier).order_by(Supplier.id)):
        hist=[i for i in incidents if i.supplier_id==s.id]
        active=[i for i in hist if i.state in ('active','monitoring')]
        rows=[{'id':i.id,'state':i.state,'priority':i.priority,'historical_priority':i.historical_priority,'event_type':i.event_type,'event_date':i.event_date,'revision':i.revision,'history':i.history,'stale':(now().date().isoformat()>i.event_date[:10] and (now().date()-__import__('datetime').date.fromisoformat(i.event_date[:10])).days>7) if context=='rss' else False} for i in hist]
        products=sorted(set(p for m in materials if s.id in (m['primary_id'],m['alternate_id']) for p in m['products']))
        latest=max(active,key=lambda i:i.priority,default=None)
        assessment=current(latest).get('assessment',{}) if latest else {}
        out.append({**s.data,'products':products,'products_mapped':bool(products),'materials':[m for m in materials if s.id in (m['primary_id'],m['alternate_id'])],'priority':max((i.priority for i in active),default=None),'urgent':any(current(i).get('assessment',{}).get('urgent')=='Y' for i in active),'needs_review':any(current(i).get('assessment',{}).get('needs_review') for i in active),'incidents':rows,'incident_count':len(active),'latest_evidence':latest.event_date if latest else None,'reason':current(latest).get('explanation','Sin incidentes analizados activos') if latest else 'Sin incidentes analizados activos','status':'active' if active else ('resolved' if hist else 'pending')})
    return sorted(out,key=lambda s:(-(s['priority'] if s['priority'] is not None else -1),s['supplier_id']))

def sources_view(db):
    return [{'id':s.id,**s.data,'status':s.status,'last_attempt_at':s.last_attempt_at,'last_success_at':s.last_success_at,'http_status':s.http_status,'item_count':s.item_count,'received_count':s.received_count,'duplicates':s.duplicates,'error_count':s.error_count,'error':s.error} for s in db.scalars(select(Source).order_by(Source.id))]
