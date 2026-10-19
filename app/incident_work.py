"""Append-only procurement activity, independent of incident recovery."""
from typing import Literal
from datetime import date
from pydantic import BaseModel,Field,ConfigDict,model_validator
from sqlalchemy import select,text
from app.models import Incident,IncidentWork,Draft
from app.human_review import ReviewConflict
from app.importer import digest
class WorkInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    previous_id:str|None=None
    status:Literal['pending','verifying','followup','done']
    action:str=Field(min_length=8,max_length=500)
    note:str=Field(min_length=8,max_length=4000)
    due_date:date|None=None
    @model_validator(mode='after')
    def meaningful(self):
        if len(self.action.strip())<8 or len(self.note.strip())<8:raise ValueError('Describe la acción y su resultado concreto')
        return self

def view(db,inc):
    history=db.scalars(select(IncidentWork).where(IncidentWork.incident_id==inc.id).order_by(IncidentWork.created_at.desc(),IncidentWork.id.desc())).all()
    return {'incident_id':inc.id,'state':inc.state,'current':{'id':history[0].id,**history[0].data}if history else None,'history':[{'id':r.id,'created_at':r.created_at,**r.data}for r in history],'drafts':[{'id':r.id,'kind':r.kind,'supplier_id':r.supplier_id,'context_changed':r.context_hash!=digest(inc.history)}for r in db.scalars(select(Draft).where(Draft.incident_id==inc.id))]}

def save(db,iid,body):
    db.execute(text("SELECT pg_advisory_xact_lock_shared(72642,4)"))
    inc=db.scalar(select(Incident).where(Incident.id==iid).with_for_update())
    if not inc:raise ValueError('Incidente no encontrado')
    latest=view(db,inc)['current']
    if (latest['id']if latest else None)!=body.previous_id:raise ReviewConflict('La acción cambió. Recarga el seguimiento antes de guardar')
    row=IncidentWork(incident_id=iid,data={**body.model_dump(mode='json',exclude={'previous_id'}),'actor':'Presentador autenticado (acceso compartido)'});db.add(row);db.flush();return row
