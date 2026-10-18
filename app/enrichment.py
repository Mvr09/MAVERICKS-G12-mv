"""Texto editorial público para RSS. Sin cookies, credenciales ni acceso a muros de pago."""

import json
import socket
import time
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx
from app.importer import digest
from app.models import now
from app.rss import FeedError, safe_url
from app.settings import RSS

VERSION = "editorial-scope-1.0.0"
AGENT = "SupplierRiskRadar"
MAX_BYTES = 2_000_000
MAX_TEXT = 24_000


class EditorialParser(HTMLParser):
    """Choose one editorial container, never concatenate neighbouring stories."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack=[]
        self.groups={}
        self.paragraph=None
        self.paragraph_scope={}
        self.paragraphs=[]
        self.json_scripts=[]
        self.script=None
        self.restricted=False

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        marker=(attrs.get('class','')+' '+attrs.get('id','')).lower()
        blocked=tag in {'aside','nav','footer','style','noscript','form','button'} or any(x in marker for x in ('paywall','subscription-wall','related-post','comments','ad-box','deskone_ticker'))
        parent=self.stack[-1] if self.stack else ('',False,{})
        scope=dict(parent[2])
        body_marker=attrs.get('itemprop')=='articleBody' or any(x in marker for x in ('entry-content','article-body','post-content','article__body','article-content'))
        if tag=='script':
            if attrs.get('type')=='application/ld+json':self.script=[]
            blocked=True
        if tag in {'article','main'} or body_marker:
            kind='article' if tag=='article' else 'body' if body_marker else 'main'
            group_id=len(self.groups)
            if kind=='article':scope.pop('body',None)
            self.groups[group_id]={'kind':kind,'article_id':scope.get('article'),'paragraphs':[]}
            scope[kind]=group_id
        if tag not in {'br','hr','img','input','meta','link','source','wbr'}:
            self.stack.append((tag,blocked or parent[1],scope))
        if tag in {'p','h2','h3','li'} and self.stack and not self.stack[-1][1] and self.stack[-1][2]:
            self.paragraph=[];self.paragraph_scope=dict(self.stack[-1][2])

    def handle_endtag(self,tag):
        if tag=='script' and self.script is not None:
            self.json_scripts.append(''.join(self.script));self.script=None
        if tag in {'p','h2','h3','li'} and self.paragraph is not None:
            text=' '.join(''.join(self.paragraph).split())
            if text:
                if text not in self.paragraphs:self.paragraphs.append(text)
                for gid in self.paragraph_scope.values():
                    if text not in self.groups[gid]['paragraphs']:self.groups[gid]['paragraphs'].append(text)
            self.paragraph=None
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:del self.stack[i:];break

    def handle_data(self,data):
        if self.script is not None:self.script.append(data)
        elif self.paragraph is not None and self.stack and not self.stack[-1][1]:self.paragraph.append(data)

    def extract(self):
        def walk(obj):
            if isinstance(obj,list):
                for x in obj:yield from walk(x)
            elif isinstance(obj,dict):
                yield obj
                if '@graph'in obj:yield from walk(obj['@graph'])
        for script in self.json_scripts:
            try:
                for obj in walk(json.loads(script)):
                    if 'Article'not in str(obj.get('@type','')):continue
                    if obj.get('isAccessibleForFree')in(False,'False','false'):
                        self.restricted=True;return '', 'restricted'
                    body=obj.get('articleBody')
                    if isinstance(body,str)and len(body)>=200:return body.strip(),'jsonld_article_body'
            except(ValueError,TypeError):continue
        text=lambda g:'\n\n'.join(g['paragraphs'])
        substantive=lambda kind:[(i,g)for i,g in self.groups.items()if g['kind']==kind and len(text(g))>=200]
        articles=substantive('article')
        if articles:
            aid,article=max(articles,key=lambda item:len(text(item[1])))
            bodies=[g for _,g in substantive('body')if g['article_id']==aid]
            chosen=max(bodies,key=lambda g:len(text(g)),default=article)
            return text(chosen),'editorial_article_container'
        bodies=substantive('body')
        if bodies:return text(max(bodies,key=lambda item:len(text(item[1])))[1]),'editorial_body_container'
        mains=substantive('main')
        if mains:return text(max(mains,key=lambda item:len(text(item[1])))[1]),'editorial_main_fallback'
        return '', 'editorial_text_unavailable'


def enrich(db, article, transport=None, check_dns=True):
    """Persistir procedencia y snapshot del texto utilizado; fallar a resumen explícito."""
    if article.context != "rss":
        return
    old = article.data.get("enrichment", {})
    # Las tres evaluaciones y reintentos comparten exactamente el mismo snapshot.
    if old.get("checked_at"):
        from datetime import datetime

        if old.get("extractor_version") == VERSION and (now() - datetime.fromisoformat(old["checked_at"])).total_seconds() < 3600:
            return
    source = next((s for s in RSS["sources"] if s["id"] == article.source_id), None)
    metadata = {
        "status": "summary_only",
        "extractor_version": VERSION,
        "checked_at": now().isoformat(),
        "http_status": None,
    }
    text = ""
    started = time.monotonic()
    try:
        if not source:
            raise FeedError("source_not_configured")
        domains = {urlsplit(source[k]).hostname for k in ("url", "discovery_url")}
        allowed = (
            domains
            | {d.removeprefix("www.") for d in domains}
            | {"www." + d for d in domains if not d.startswith("www.")}
        )
        parts = urlsplit(article.data.get("url", ""))
        url = (
            urlunsplit(("https", parts.netloc, parts.path, parts.query, ""))
            if parts.scheme == "http"
            else parts.geturl()
        )

        def get(client, target, guard=None):
            for _ in range(4):
                if guard:
                    guard(target)
                if time.monotonic() - started > 18:
                    raise FeedError("fetch_timeout")
                if check_dns:
                    safe_url(target, allowed)
                else:
                    parsed = urlsplit(target)
                    if (
                        parsed.scheme != "https"
                        or parsed.hostname not in allowed
                        or parsed.username
                        or parsed.password
                        or parsed.port not in (None, 443)
                    ):
                        raise FeedError("destination_not_allowed")
                with client.stream("GET", target) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        target = urljoin(target, response.headers.get("location", ""))
                        continue
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise FeedError("response_too_large")
                        chunks.append(chunk)
                    return response, b"".join(chunks), target
            raise FeedError("too_many_redirects")

        with httpx.Client(
            transport=transport,
            timeout=8,
            follow_redirects=False,
            headers={
                "User-Agent": AGENT + "/0.2 (+public RSS reading)",
                "Accept": "text/html,text/plain",
            },
        ) as client:
            robot_url = urljoin(url, "/robots.txt")
            robots, raw, _ = get(client, robot_url)
            robot_policy = None
            if robots.status_code == 200:
                parser = RobotFileParser()
                parser.parse(raw.decode("utf-8", errors="replace").splitlines())
                robot_policy = parser
                if not parser.can_fetch(AGENT, url):
                    raise FeedError("robots_disallowed")
            elif robots.status_code not in (404, 410):
                raise FeedError("robots_unavailable")

            def guard(target):
                if urlsplit(target).netloc != urlsplit(url).netloc:
                    raise FeedError("redirect_requires_new_robots_policy")
                if robot_policy and not robot_policy.can_fetch(AGENT, target):
                    raise FeedError("robots_disallowed")

            response, raw, final_url = get(client, url, guard)
            metadata["http_status"] = response.status_code
            if response.status_code != 200:
                raise FeedError("article_http_" + str(response.status_code))
            if "html" not in response.headers.get("content-type", ""):
                raise FeedError("unsupported_content_type")
            parser = EditorialParser()
            parser.feed(raw.decode(response.encoding or "utf-8", errors="replace"))
            text, method = parser.extract()
            if len(text) < 200:
                raise FeedError(
                    "restricted" if parser.restricted else "editorial_text_unavailable"
                )
            truncated = len(text) > MAX_TEXT
            text = text[:MAX_TEXT]
            metadata.update(
                status="partial" if truncated else "public_text",
                source_url=final_url,
                method=method + "@" + VERSION,
                text_hash=digest(text),
                characters=len(text),
            )
    except (httpx.RequestError, socket.gaierror, FeedError, ValueError) as exc:
        metadata["reason"] = (
            str(exc) if isinstance(exc, FeedError) else "fetch_unavailable"
        )
    article.data = {**article.data, "full_text": text, "enrichment": metadata}
    db.flush()
