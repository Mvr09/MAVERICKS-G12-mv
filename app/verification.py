"""An evidence-backed question, never a manual override of JEV or a risk alert."""
from app.importer import digest


def prepare(article,supplier,result,evidence_ids,note):
    if article.context!='rss' or result.get('analysis_status') not in ('done','review'):
        raise ValueError('Se requiere una noticia RSS analizada; un error o pendiente no permite crear esta consulta.')
    if not evidence_ids or len(set(evidence_ids))!=len(evidence_ids) or len(evidence_ids)>3:
        raise ValueError('Selecciona entre uno y tres fragmentos distintos.')
    evidence={e['id']:e for e in result['evidence']}
    selected=[]
    for key in evidence_ids:
        e=evidence.get(key)
        if not e or article.data.get(e['field'],'')[e['start']:e['end']]!=e['text']:
            raise ValueError('El fragmento no coincide con la fuente guardada.')
        selected.append(dict(e))
    if sum(len(e['text']) for e in selected)>10000:
        raise ValueError('Selecciona fragmentos más breves para esta consulta.')
    if len(note.strip()) < 12:
        raise ValueError('Describe la hipótesis de compras antes de crear la consulta.')
    s=supplier.data
    snapshot={'article_id':article.id,'generation':article.generation,'version':article.version,
      'headline':article.data['headline'],'source':article.data['source'],'published_date':article.data['published_date'],
      'url':article.data.get('url'),'evidence':selected,'buyer_hypothesis':note.strip(),
      'supplier_id':supplier.id,'supplier_material':s['material'],'question_version':result['question_version'],
      'exposure_status':'potential_unconfirmed','portfolio':'Cartera ficticia de Helixa; sin confirmación de entregas afectadas.'}
    quotes='\n'.join('> '+e['text'] for e in selected)
    text=(f"Asunto: Verificación de posible exposición — {s['material']}\n\nA la atención de {s['name']}:\n\n"
      f"Estamos revisando una noticia de {snapshot['source']} publicada el {snapshot['published_date']}: {snapshot['headline']}.\n"
      f"Fragmentos literales de la fuente:\n{quotes}\n"+(f"Fuente: {snapshot['url']}\n" if snapshot['url'] else '')+
      f"\nHipótesis de compras, pendiente de confirmar: {snapshot['buyer_hypothesis']}\n\n"
      "¿Esta situación afecta a su actividad o ruta declarada y a las entregas que tendríamos que revisar? Si aplica, rogamos confirmar alcance, fechas y medidas disponibles; si no aplica, agradecemos confirmar la ausencia de exposición.\n\n"
      "No se ha confirmado afectación individual, stock, capacidad alternativa ni entregas comprometidas. Esta consulta no valida la clasificación del modelo ni constituye un pedido.\n\n"
      "Borrador para una cartera ficticia · Helixa Pharmaceuticals. Sin envío externo.")
    return text,snapshot,digest(snapshot)
