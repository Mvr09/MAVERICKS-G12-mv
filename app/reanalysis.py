"""Explicit new runs preserve results, drafts and the last known incident state.

Only successful publication supersedes earlier evidence. Superseded is not a
recovery: a new model conclusion must not manufacture a resolved real event.
"""
from sqlalchemy import select
from app.models import Article, Batch, Incident, Alert, Job, GrantArticle, now
from app.settings import POLICY


def enqueue_article(db, aid, profile):
    from app.queue import enqueue, reserve, analysis_key, analysis_payload
    from app.profiles import PUBLIC_EXERCISE_PROFILES
    from app.jev import grant_requires_diagnosis
    if profile not in PUBLIC_EXERCISE_PROFILES:
        raise ValueError('Perfil de análisis no disponible.')
    article=db.scalar(select(Article).where(Article.id==aid).with_for_update())
    if not article:
        raise ValueError('Noticia no encontrada.')
    latest=db.scalar(select(Article.version).where(Article.origin_key==article.origin_key).order_by(Article.version.desc()).limit(1))
    if article.state=='superseded' or article.version!=latest:
        raise ValueError('Existe una versión más reciente de esta noticia. Abre la versión actual para analizarla.')
    if article.context=='rss' and profile=='link-2.2.0':
        raise ValueError('Elige el perfil RSS actual o la candidata.')
    active=db.scalar(select(Job).where(Job.kind=='analysis',Job.payload['article_id'].as_string()==aid,Job.state.in_(('queued','running'))))
    if active:
        raise ValueError('Esta noticia ya tiene un análisis en curso.')
    reservation=db.get(GrantArticle,aid)
    if reservation and grant_requires_diagnosis(db,reservation.grant_id):
        raise ValueError('Diagnostica primero el error del proveedor; sus intentos se conservan.')
    split=db.get(Batch,article.batch_id).split if article.batch_id else 'rss'
    if not reserve(db,article,split,manual_rss=True,fresh=article.state!='pending'):
        raise ValueError('Sin autorización o cupo disponible para este análisis.')
    if article.state!='pending':article.generation+=1
    article.state='pending'
    if article.batch_id:
        db.get(Batch,article.batch_id).completed_at=None
    return enqueue(db,analysis_key(article),'analysis',analysis_payload(article,profile),100)


def retire_effects(db,article,result):
    if result['analysis_status']=='error':return
    stamp=now().isoformat()
    # A changed RSS source has a new Article ID but the same origin_key.
    # Retire only older versions after successful inference; never on error.
    source_cache={}
    def older(h):
        if h.get('article_id')==article.id:return h.get('generation',0)<article.generation
        aid=h.get('article_id')
        if aid not in source_cache:
            previous=db.get(Article,aid)if aid else None
            source_cache[aid]=(previous.origin_key,previous.version)if previous else None
        previous=source_cache[aid]
        return bool(previous and previous[0]==article.origin_key and previous[1]<article.version)

    for inc in db.scalars(select(Incident).where(Incident.context==article.context).with_for_update()):
        if not any(older(h) and not h.get('superseded') for h in inc.history):continue
        inc.history=[{**h,'superseded':True,'superseded_at':stamp,'superseded_by_generation':article.generation}
            if older(h) and not h.get('superseded') else h for h in inc.history]
        current=max((h for h in inc.history if h.get('assessment') and not h.get('superseded')),
            key=lambda h:(h.get('published_date',''),h.get('at','')),default=None)
        manual=max((h.get('at','') for h in inc.history if h.get('manual')),default='')
        if manual and (not current or manual>current.get('at','')):
            # Manual resolution remains authoritative after model reanalysis.
            inc.state='resolved';inc.priority=0
        elif current:
            a=current['assessment'];state=a.get('impact_status','monitoring')
            inc.state=state if state in ('active','monitoring','resolved') else 'monitoring'
            inc.priority=0 if inc.state=='resolved' else a.get('priority') or 0
            inc.event_date=current['published_date']
        else:
            inc.state='superseded';inc.priority=0
        for alert in db.scalars(select(Alert).where(Alert.incident_id==inc.id)):
            if older({'article_id':alert.data.get('article_id'),'generation':alert.data.get('generation',0)}):
                alert.data={**alert.data,'state':'superseded','sound_eligible':False,'superseded_by_generation':article.generation}
    db.flush()
