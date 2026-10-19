"""Atomic manual selections; manifests reuse durable jobs and never run inference here."""
from sqlalchemy import select, text
from app.models import Article, Job, now
from app.reanalysis import enqueue_article

KIND = 'analysis_selection'


def view(db, manifest):
    items = manifest.payload['items']
    ids = [i['job_id'] for i in items if i.get('job_id')]
    jobs = {j.id: j for j in db.scalars(select(Job).where(Job.id.in_(ids)))} if ids else {}
    rows = []
    counts = dict(done=0, queued=0, running=0, error=0, skipped=0)
    for item in items:
        job = jobs.get(item.get('job_id'))
        state = job.state if job else item.get('state', 'error')
        if state not in counts:
            state = 'error'
        error = job.error if job else item.get('error')
        if item.get('job_id') and not job:
            state, error = 'error', 'El trabajo ya no está disponible; requiere diagnóstico.'
        counts[state] += 1
        rows.append({**item, 'state': state, 'error': error,
            'analysis_profile': job.payload.get('analysis_profile', '1.0.0') if job else None})
    total = len(items)
    finished = counts['done'] + counts['error'] + counts['skipped']
    return {'id': manifest.id, 'context': manifest.payload['context'],
            'analysis_profile': manifest.payload['analysis_profile'],
            'created_at': manifest.payload['created_at'], 'total': total,
            'finished': finished, 'counts': counts, 'items': rows,
            'state': 'running' if finished < total else 'partial' if counts['error'] else 'complete'}


def create(db, request_id, article_ids, context, profile):
    if len(set(article_ids)) != len(article_ids):
        raise ValueError('La selección contiene noticias repetidas.')
    key = 'analysis-selection:' + str(request_id)
    db.execute(text('SELECT pg_advisory_xact_lock(hashtext(:key))'), {'key': key})
    existing = db.scalar(select(Job).where(Job.key == key))
    selection = {'article_ids': article_ids, 'context': context, 'analysis_profile': profile}
    if existing:
        if any(existing.payload[k] != v for k, v in selection.items()):
            raise ValueError('Este identificador ya pertenece a otra selección.')
        return view(db, existing)
    articles = {a.id: a for a in db.scalars(select(Article).where(Article.id.in_(article_ids)).order_by(Article.id).with_for_update())}
    if any(a.context != context for a in articles.values()):
        raise ValueError('Selecciona noticias de un único contexto.')
    active = {j.payload['article_id']: j for j in db.scalars(select(Job).where(
        Job.kind == 'analysis', Job.state.in_(('queued', 'running')),
        Job.payload['article_id'].as_string().in_(article_ids)))}
    items = []
    for aid in article_ids:
        a = articles.get(aid)
        item = {'article_id': aid, 'headline': a.data.get('headline', '') if a else '', 'job_id': None}
        if not a:
            item.update(state='error', error='La noticia ya no está disponible.')
        elif a.state != 'pending':
            item.update(state='skipped', error='Ya no está pendiente; se conserva su resultado y no se reanaliza.')
        elif aid in active:
            item['job_id'] = active[aid].id
        else:
            try:
                with db.begin_nested():
                    job = enqueue_article(db, aid, profile)
                    item['job_id'] = job.id
            except ValueError as exc:
                item.update(state='error', error=str(exc))
        items.append(item)
    # This row is an accepted-request manifest, not a queued worker task.
    # Its immutable payload preserves the denominator; view derives live progress.
    if db.get(Job, str(request_id)):
        raise ValueError('Identificador de selección no disponible.')
    manifest = Job(id=str(request_id), key=key, kind=KIND, state='done', payload={**selection,
        'created_at': now().isoformat(), 'items': items})
    db.add(manifest); db.flush()
    return view(db, manifest)
