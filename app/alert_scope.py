"""An alert records a revision, not perpetual work on all past analyses."""
def current(alert, incident):
    return bool(incident and incident.state in ('active','monitoring') and alert.revision==incident.revision and alert.data.get('state') not in ('superseded','resolved'))

def reason(alert,incident):
    if alert.data.get('state')=='superseded':return 'Análisis sustituido; se conserva en el histórico'
    if incident and incident.state in ('resolved','superseded'):return 'Incidente cerrado o sustituido; conserva su historial'
    if incident and alert.revision!=incident.revision:return 'Aviso de una revisión anterior del incidente'
    return None
