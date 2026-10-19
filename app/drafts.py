from app.models import Supplier


def make_draft(db, supplier, incident, kind):
    from app.views import current

    s = supplier.data
    entry = current(incident)
    assessment = entry.get("assessment")
    if not assessment or assessment.get("needs_review"):
        raise ValueError("Revisa primero las evidencias y los datos del incidente")
    facts = entry.get("explanation", "").strip()
    if entry.get("human_review_id"):
        from app.models import HumanDecision
        decision = db.get(HumanDecision, entry["human_review_id"])
        if decision:
            facts = "Validación humana del presentador: " + decision.data["evidence"] + " (Procedencia: " + decision.data["evidence_source"] + "). " + facts
    if not facts:
        raise ValueError("Falta evidencia validada para redactar la consulta")
    if entry.get("published_date"):
        facts += f" (Noticia publicada el {entry['published_date']})."
    if kind == "alternate":
        alt = db.get(Supplier, s["alternate_id"]) if s["alternate_id"] else None
        if not alt:
            raise ValueError("Sin alternativo registrado en el catálogo")
        return f"Asunto: Consulta de disponibilidad — {s['material']}\n\nA la atención de {alt.data['name']}:\n\nSu oferta registrada es {alt.data['material']}. Antes de considerar esta alternativa para {s['material']}, solicitamos confirmar su adecuación técnica y operativa, disponibilidad, capacidad y plazo de entrega. Estamos revisando una incidencia relativa a {s['name']}.\n\nInformación publicada (impacto sobre nuestras entregas por confirmar): {facts}\n\nNo disponemos de confirmación de stock ni capacidad. Esta consulta no constituye un pedido. Rogamos confirmar las condiciones y alternativas posibles.\n\nEquipo de Compras · Helixa Pharmaceuticals"
    return f"Asunto: Confirmación de continuidad de suministro — {s['material']}\n\nA la atención de {s['name']}:\n\nEstamos revisando la siguiente información publicada: {facts}\n\nSolicitamos confirmar el impacto sobre nuestras entregas, las medidas de continuidad y el plazo de recuperación, si se conoce. Rogamos distinguir fechas confirmadas de estimaciones.\n\nEquipo de Compras · Helixa Pharmaceuticals"
