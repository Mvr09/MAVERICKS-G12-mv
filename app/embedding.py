"""Exact presentation framing policy and cross-site session cookie support.

Framing is not CORS permission. Session mutations retain Origin and CSRF checks.
"""
from http.cookies import SimpleCookie
from app.settings import settings

PRESENTATION_ORIGIN = "https://helixa-signal-to-action.jvaswiss-9277.chatgpt.site"
SESSION_COOKIE = "radar_session"
EMBED_COOKIE = "radar_embed_session"
BASE_CSP = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"


def apply_framing_policy(request, response):
    navigable = response.headers.get('content-type', '').lower().startswith('text/html') or (
        300 <= response.status_code < 400 and not request.url.path.startswith('/api/'))
    if navigable:
        if 'X-Frame-Options' in response.headers:
            del response.headers['X-Frame-Options']
        response.headers['Content-Security-Policy'] = BASE_CSP.replace(
            "frame-ancestors 'none'", f"frame-ancestors 'self' {PRESENTATION_ORIGIN}")
    else:
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = BASE_CSP


def partitioned_cookie(response, value, max_age=28800):
    # Python 3.12/Starlette cannot yet serialize the Partitioned attribute.
    # Serialize the signed value safely, then append the standard flag.
    c = SimpleCookie()
    c[EMBED_COOKIE] = value
    for key, val in {'path':'/', 'max-age':str(max_age), 'samesite':'None', 'secure':True, 'httponly':True}.items():
        c[EMBED_COOKIE][key] = val
    response.headers.append('Set-Cookie', c[EMBED_COOKIE].OutputString() + '; Partitioned')


def set_session_cookies(response, value, embedded=False):
    secure = settings.app_base_url.startswith('https://')
    response.set_cookie(SESSION_COOKIE, value, httponly=True, secure=secure,
                        samesite='none' if secure else 'lax', max_age=28800)
    if secure and embedded:
        partitioned_cookie(response, value)


def clear_session_cookies(response):
    secure = settings.app_base_url.startswith('https://')
    response.delete_cookie(SESSION_COOKIE, httponly=True, secure=secure,
                           samesite='none' if secure else 'lax')
    if secure:
        partitioned_cookie(response, '', max_age=0)
