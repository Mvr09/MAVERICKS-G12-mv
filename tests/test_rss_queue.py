import httpx,pytest
from datetime import timedelta
from sqlalchemy import select
from app.db import Session
from app.models import Source,Article,Job,Grant,GrantArticle,now
from app.rss import sync_source,safe_url,FeedError
from app.queue import enqueue,claim,reserve
from tests.helpers import synthetic

def feed(title='Synthetic RSS title',guid='synthetic-guid'):
    from email.utils import format_datetime
    return f'<rss version="2.0"><channel><title>MOCK RSS</title><item><guid>{guid}</guid><title>{title}</title><description>&lt;script&gt;alert(1)&lt;/script&gt;Synthetic summary</description><link>https://example.org/item</link><pubDate>{format_datetime(now())}</pubDate></item></channel></rss>'.encode()

def test_feed_repeat_edit_and_304():
    with Session() as db:
        source=db.get(Source,'ema')
        result=sync_source(db,'ema',httpx.MockTransport(lambda r:httpx.Response(200,content=feed(),headers={'etag':'mock-etag'})),check_dns=False)
        db.commit();assert result['new']==1
        result=sync_source(db,'ema',httpx.MockTransport(lambda r:httpx.Response(200,content=feed())),check_dns=False);db.commit();assert result['duplicates']==1
        result=sync_source(db,'ema',httpx.MockTransport(lambda r:httpx.Response(200,content=feed('Synthetic changed title'))),check_dns=False);db.commit();assert result['new']==1
        versions=db.scalars(select(Article).where(Article.context=='rss').order_by(Article.version)).all();assert [a.version for a in versions]==[1,2]
        assert '<script>' not in versions[0].data['summary']
        result=sync_source(db,'ema',httpx.MockTransport(lambda r:httpx.Response(304)),check_dns=False);db.commit();assert result['http']==304;assert source.status=='unchanged';assert source.item_count==0

def test_bad_xml_and_one_source_failure_do_not_stop_others():
    with Session() as db:
        sync_source(db,'ema',httpx.MockTransport(lambda r:httpx.Response(500)),check_dns=False);db.commit();assert db.get(Source,'ema').status=='error'
        result=sync_source(db,'gdacs',httpx.MockTransport(lambda r:httpx.Response(200,content=feed())),check_dns=False);db.commit();assert result['new']==1
        sync_source(db,'ema',httpx.MockTransport(lambda r:httpx.Response(200,content=b'<!DOCTYPE foo [<!ENTITY x SYSTEM "file:///etc/passwd">]><rss>&x;</rss>')),check_dns=False);db.commit();assert db.get(Source,'ema').status=='error'

@pytest.mark.parametrize('url',['http://www.ema.europa.eu/en/news.xml','https://127.0.0.1/feed','https://localhost/feed','https://metadata.google.internal/feed','https://www.ema.europa.eu:8000/feed','https://user:secret@www.ema.europa.eu/feed'])
def test_ssrf_rejected(url):
    with pytest.raises(FeedError):safe_url(url,{'www.ema.europa.eu'})

def test_claim_two_workers_and_expired_lease():
    with Session() as db:
        one=enqueue(db,'synthetic-one','rss',{'source_id':'ema'});two=enqueue(db,'synthetic-two','rss',{'source_id':'gdacs'});db.commit()
    with Session() as first,Session() as second:
        a=claim(first);b=claim(second);assert a.id!=b.id;first.commit();second.commit()
    with Session() as db:
        a=db.get(Job,one.id);a.lease_until=now()-timedelta(seconds=1);db.commit()
        recovered=claim(db);assert recovered.id==a.id;assert recovered.attempts==2;db.commit()

def test_grant_survives_resume_and_rss_disabled():
    with Session() as db:
        articles=[synthetic(db,headline=f'Synthetic article {i}') for i in range(4)]
        for a in articles[:3]:assert reserve(db,a,'training')
        assert not reserve(db,articles[3],'training');db.commit()
    with Session() as db:
        assert db.get(Grant,'initial-training-3').used==3
        assert reserve(db,db.get(Article,articles[0].id),'training')
        assert not reserve(db,articles[3],'rss')
