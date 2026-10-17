from app.models import Supplier

def make_draft(db,supplier,incident,kind):
    s=supplier.data
    assessments=[h['assessment'] for h in incident.history if 'assessment' in h]
    if not assessments or assessments[-1].get('needs_review'): raise ValueError('Revisa primero las evidencias y los datos del incidente')
    facts=assessments[-1].get('explanation','')
    if kind=='alternate':
        alt=db.get(Supplier,s['alternate_id']) if s['alternate_id'] else None
        if not alt: raise ValueError('Sin alternativo aprobado en el catálogo')
        return f'Asunto: Consulta de disponibilidad — {s["material"]}\n\nA la atención de {alt.data["name"]}:\n\nSolicitamos confirmar disponibilidad, capacidad y plazo de entrega para {s["material"]}. Estamos revisando una incidencia relativa a {s["name"]}.\n\nHechos verificados: {facts}\n\nNo disponemos de confirmación de stock ni capacidad. Esta consulta no constituye un pedido. Rogamos confirmar las condiciones y alternativas posibles.\n\nEquipo de Compras · Helixa Pharmaceuticals'
    return f'Asunto: Confirmación de continuidad de suministro — {s["material"]}\n\nA la atención de {s["name"]}:\n\nEstamos revisando la siguiente información publicada: {facts}\n\nSolicitamos confirmar el impacto sobre nuestras entregas, las medidas de continuidad y el plazo de recuperación, si se conoce. Rogamos distinguir fechas confirmadas de estimaciones.\n\nEquipo de Compras · Helixa Pharmaceuticals'
