"""Cheap retrieval hints for the inbox. Never an exposure/risk decision."""
import json,re
from functools import lru_cache
from app.geography import fold,matches,location,retrieval_hints

@lru_cache(maxsize=1024)
def hints(headline,summary,catalog):
    article={'headline':headline,'summary':summary};text=fold(headline+' '+summary);found=[]
    for s in json.loads(catalog):
        raw=retrieval_hints(article,s);named=matches(text,s['name']) or any(h['kind']=='name' for h in raw);geo=[h for h in raw if h['kind']in('city','region')]
        material=fold(s.get('material',''))
        corridor=re.fullmatch(r'(.+) to (.+) (sea|rail) freight',material)
        service=False
        if corridor:
            origin,destination,mode=corridor.groups()
            vocabulary={'sea':r'\b(container|shipping|maritime|ocean|vessel|contenedor|buque)\w*\b','rail':r'\b(rail|train|ferroviari)\w*\b'}
            service=matches(text,origin) and matches(text,destination) and bool(re.search(vocabulary[mode],text))
        if named or geo or service:
            ambiguous=location(s)['status']=='ambiguous'
            reason='Nombre del proveedor en la fuente'if named else'Corredor declarado e indicio del modo; transporte y embarques por confirmar'if service else'Coincidencia geográfica candidata; provincia sin confirmar'if ambiguous else'Lugar o región del catálogo citado en la fuente'
            found.append({'supplier_id':s['supplier_id'],'supplier_name':s['name'],'reason':reason,'kind':'name'if named else'service'if service else'geography','location_ambiguous':ambiguous})
    found.sort(key=lambda r:({'name':0,'service':1,'geography':2}[r['kind']],r['supplier_id']))
    return {'version':'inbox-retrieval-1.0.0','level':'named'if any(r['kind']=='name'for r in found)else'service'if any(r['kind']=='service'for r in found)else'geography'if found else'none','suppliers':found,'reasons':sorted(set(r['reason']for r in found)),'limitation':'Indicio preliminar para ordenar lectura, no asociación sustentada, riesgo ni afectación individual. Ausencia de indicio no descarta relevancia.'}

def preliminary(db,article):
    from sqlalchemy import select
    from app.models import Supplier
    if 'triage_catalog'not in db.info:
        db.info['triage_catalog']=json.dumps([{'supplier_id':s.id,'name':s.data['name'],'city':s.data.get('city',''),'country':s.data.get('country',''),'material':s.data.get('material','')}for s in db.scalars(select(Supplier).order_by(Supplier.id))],sort_keys=True)
    return hints(article.data.get('headline',''),article.data.get('summary',''),db.info['triage_catalog'])
