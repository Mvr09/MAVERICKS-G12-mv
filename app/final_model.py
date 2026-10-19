"""Read-only final profile report. Never loads prompts into clients or starts inference."""
import json, math, statistics
from datetime import datetime
from types import SimpleNamespace
from sqlalchemy import select
from app.settings import ROOT
from app.models import EvaluationCampaign, CampaignRun, Job
from app.campaigns import aggregate

FINAL = json.loads((ROOT / 'config/final_profile.json').read_text())


def stats(values):
    values = sorted(float(v) for v in values if v is not None and math.isfinite(float(v)) and float(v) >= 0)
    return {'n': len(values), 'mean': statistics.fmean(values) if values else None,
            'median': statistics.median(values) if values else None,
            'p95': values[max(0, math.ceil(.95 * len(values))-1)] if values else None}


def delta(end, start):
    if not start or not end: return None
    try:
        value = (datetime.fromisoformat(str(end))-datetime.fromisoformat(str(start))).total_seconds()
        return value if value >= 0 else None
    except (ValueError,TypeError): return None


def report(db, sample='labelled'):
    out = {'profile': FINAL, 'sample': sample, 'quality': None, 'status': 'unavailable',
           'limit': 'Training y validation ya inspeccionados: comparación descriptiva, no validación independiente ni precisión RSS.',
           'performance': None, 'railway': {'fresh': stats([]), 'cached_or_mixed': stats([])}}
    c = db.get(EvaluationCampaign, FINAL['campaign_id'])
    if not c or c.freeze.get('hash') != FINAL['freeze_hash'] or c.freeze['versions'].get(FINAL['profile']) != FINAL['components']:
        out['message'] = 'Evaluación congelada no disponible o no coincide con el perfil. Las métricas no se sustituyen por otra campaña.'
        return out
    # Project only metric inputs and accounting, not full effective payloads/responses.
    selected = db.execute(select(CampaignRun.id, CampaignRun.split, CampaignRun.state,
        CampaignRun.reference, CampaignRun.result['is_risk'].as_string(), CampaignRun.result['urgent'].as_string(),
        CampaignRun.result['affected_supplier_ids'], CampaignRun.started_at, CampaignRun.completed_at,
        CampaignRun.audit['queued_at'], CampaignRun.audit['calls'], CampaignRun.audit['_cache_stages'],
        CampaignRun.audit['new_requests'], CampaignRun.audit['retries']).where(
            CampaignRun.campaign_id == c.id, CampaignRun.profile == FINAL['profile'])).all()
    rows=[]
    for rid, split, state, ref, risk, urgent, suppliers, start, end, queued, calls, cache, requests, retries in selected:
        rows.append(SimpleNamespace(id=rid,split=split,state=state,reference=ref,
            result={'is_risk':risk,'urgent':urgent,'affected_supplier_ids':suppliers or [],'analysis_status':state} if risk else None,
            started_at=start,completed_at=end,audit={'queued_at':queued,'calls':calls or [],'_cache_stages':cache or [],
            'new_requests':requests or 0,'retries':retries or 0,'wall_seconds':delta(end,start) or 0}))
    chosen=[r for r in rows if r.split in ('training','validation') and (sample=='labelled' or r.split==sample)]
    out.update(status='complete' if c.state=='complete' else 'partial', quality=aggregate(chosen),
        evaluation={'id':c.id,'name':c.name,'started_at':c.started_at,'completed_at':c.completed_at,
                    'commit':c.freeze['created_commit'],'infrastructure':c.freeze['infrastructure']})
    valid=[r for r in rows if r.state in ('done','review') and r.started_at and r.completed_at]
    fresh=[r for r in valid if r.audit['new_requests']>0 and not r.audit['_cache_stages']]
    tokens=[]
    for r in fresh:
        calls=r.audit['calls']
        if calls and all(isinstance(k.get('usage',{}).get('input_tokens'),(int,float)) and isinstance(k.get('usage',{}).get('output_tokens'),(int,float)) for k in calls):
            tokens.append(sum(k['usage']['input_tokens']+k['usage']['output_tokens'] for k in calls))
    out['performance']={'fresh':stats([delta(r.completed_at,r.started_at) for r in fresh]),
        'cached_or_mixed':stats([delta(r.completed_at,r.started_at) for r in valid if r not in fresh]),
        'queue':stats([delta(r.started_at,r.audit['queued_at']) for r in fresh]),'tokens_reported':stats(tokens),
        'tokens_basis':'Suma de entrada y salida reportadas en todas las llamadas; aproximación, no certificación de tokens facturables. Caché del proveedor no informada.',
        'new_requests':sum(r.audit['new_requests'] for r in fresh),'start':min((r.started_at for r in fresh),default=None),'end':max((r.completed_at for r in fresh),default=None),
        'environment':c.freeze['infrastructure'],'definition':'Duración individual started_at→completed_at; etapas completas, sin espera en cola. No es tiempo paralelo de campaña / noticias.'}
    jobs = db.scalars(select(Job).where(Job.kind=='analysis', Job.state=='done',
        Job.payload['analysis_profile'].as_string()==FINAL['profile']).order_by(Job.next_attempt_at.desc()).limit(1000)).all()
    observed=[j.payload['telemetry'] for j in jobs if j.payload.get('profile_snapshot')==FINAL['components'] and
        j.payload.get('telemetry',{}).get('environment')=='Railway' and j.payload.get('telemetry',{}).get('completed_at')]
    out['railway']={'fresh':stats([delta(t['completed_at'],t.get('started_at')) for t in observed if t.get('new_requests',0)>0 and not t.get('cached_stages')]),
        'cached_or_mixed':stats([delta(t['completed_at'],t.get('started_at')) for t in observed if not t.get('new_requests',0) or t.get('cached_stages')]),
        'queue':stats([delta(t.get('started_at'),t.get('queued_at')) for t in observed]),
        'definition':'Nuevas ejecuciones operativas con marcas del worker; no incluye históricos sin esa telemetría.'}
    return out
