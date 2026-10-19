import socket, ipaddress, hashlib, calendar
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit, urljoin
import bleach, feedparser, httpx
from defusedxml.ElementTree import fromstring
from sqlalchemy import select
from app.models import Source, Article, now
from app.settings import RSS
from app.importer import digest


class FeedError(Exception):
    pass


def safe_url(url, allowed):
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or parsed.hostname not in allowed
    ):
        raise FeedError("Destino RSS no permitido")
    addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(
        not ipaddress.ip_address(a[4][0]).is_global for a in addresses
    ):
        raise FeedError("Dirección RSS no pública")
    return url


def plain(value):
    return bleach.clean(str(value or ""), tags=[], attributes={}, strip=True).strip()


def ingest(db, source, content):
    # Explicitly forbid DTD/entities before feedparser, which handles RSS and Atom.
    try:
        fromstring(content, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except Exception:
        raise FeedError("XML RSS inválido o contiene entidades no permitidas")
    parsed = feedparser.parse(content)
    if not parsed.entries and parsed.bozo:
        raise FeedError("No se pudo interpretar el feed RSS/Atom")
    received = duplicates = new = 0
    cutoff = now() - timedelta(hours=RSS["initial_lookback_hours"])
    for item in parsed.entries:
        stamp = item.get("published_parsed") or item.get("updated_parsed")
        if not stamp:
            continue  # No invented publication time.
        published = datetime.fromtimestamp(calendar.timegm(stamp), timezone.utc)
        if published < cutoff or published > now() + timedelta(minutes=10):
            continue
        if received >= RSS["max_new_items_per_source_poll"]:
            break
        received += 1
        url = item.get("link", "")
        url = url if urlsplit(url).scheme in ("http", "https") else ""
        guid = str(item.get("id") or url or "")
        if not guid:
            continue
        origin = source.id + ":" + hashlib.sha256(guid.encode()).hexdigest()
        data = {
            "news_id": guid,
            "published_date": published.isoformat(),
            "source": source.data["name"],
            "headline": plain(item.get("title"))[:2000],
            "summary": plain(item.get("summary"))[:15000],
            "language": source.data["language"],
            "context_id": "rss",
            "url": url,
        }
        content_hash = digest(data)
        versions = db.scalars(
            select(Article)
            .where(Article.origin_key == origin)
            .order_by(Article.version.desc())
        ).all()
        if any(v.content_hash == content_hash for v in versions):
            duplicates += 1
            continue
        for previous in versions:
            if previous.state == "pending":
                previous.state = "superseded"
        version = versions[0].version + 1 if versions else 1
        db.add(
            Article(
                origin_key=origin,
                version=version,
                source_id=source.id,
                context="rss",
                news_id=guid,
                data=data,
                content_hash=content_hash,
            )
        )
        new += 1
    source.item_count = new
    source.received_count += received
    source.duplicates += duplicates
    return {
        "received": received,
        "new": new,
        "duplicates": duplicates,
        "parsed": len(parsed.entries),
    }


def sync_source(db, source_id, transport=None, check_dns=True):
    from sqlalchemy import text

    db.execute(text("SELECT pg_advisory_xact_lock_shared(72642, 4)"))
    source = db.scalar(
        select(Source).where(Source.id == source_id).with_for_update(skip_locked=True)
    )
    if not source:
        return {"skipped": "source_locked"}
    source.last_attempt_at = now()
    source.http_status = None
    source.item_count = 0
    headers = {"User-Agent": "SupplierRiskRadar/0.1 (RSS demo; metadata only)"}
    if source.etag:
        headers["If-None-Match"] = source.etag
    if source.modified:
        headers["If-Modified-Since"] = source.modified
    allowed = {urlsplit(x["url"]).hostname for x in RSS["sources"]}
    url = source.data["url"]
    result = {}
    try:
        with httpx.Client(
            transport=transport, timeout=RSS["timeout_seconds"], follow_redirects=False
        ) as client:
            for _ in range(4):
                if check_dns:
                    safe_url(url, allowed)
                with client.stream("GET", url, headers=headers) as response:
                    source.http_status = response.status_code
                    if response.status_code in (301, 302, 303, 307, 308):
                        url = urljoin(url, response.headers.get("location", ""))
                        continue
                    if response.status_code == 304:
                        source.status = "unchanged"
                        source.last_success_at = now()
                        source.error = None
                        source.data = {**source.data, "last_poll": {"received": 0, "new": 0, "duplicates": 0, "not_modified": True}}
                        return {"http": 304, "new": 0}
                    if response.status_code != 200:
                        raise FeedError(f"HTTP {response.status_code}")
                    chunks = []
                    size = 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > RSS["max_response_bytes"]:
                            raise FeedError("Respuesta RSS superior a 4 MB")
                        chunks.append(chunk)
                    result = ingest(db, source, b"".join(chunks))
                    source.etag = response.headers.get("etag")
                    source.modified = response.headers.get("last-modified")
                    source.status = "ok"
                    source.last_success_at = now()
                    source.error = None
                    break
            else:
                raise FeedError("Demasiadas redirecciones RSS")
    except (httpx.RequestError, FeedError, socket.gaierror) as exc:
        source.status = "error"
        source.error_count += 1
        source.error = (
            str(exc)
            if isinstance(exc, FeedError)
            else "Error de conexión o resolución DNS"
        )
        result = {"error": source.error}
    source.data = {**source.data, "last_poll": result}
    db.flush()
    return {"http": source.http_status, **result}
