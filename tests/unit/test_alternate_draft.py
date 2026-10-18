from types import SimpleNamespace
from app.drafts import make_draft


def test_alternate_is_not_assumed_interchangeable():
 s=SimpleNamespace(data={'alternate_id':'ALT','material':'Ocean freight','name':'Ocean operator'})
 alt=SimpleNamespace(data={'name':'Rail operator','material':'Rail freight'})
 db=SimpleNamespace(get=lambda model,key:alt)
 entry={'assessment':{'needs_review':False},'explanation':'Source describes an ocean delay.'}
 incident=SimpleNamespace(history=[entry],state='active')
 text=make_draft(db,s,incident,'alternate')
 assert 'Rail freight' in text and 'Ocean freight' in text and 'adecuación técnica y operativa' in text
 assert 'no constituye un pedido' in text and 'No disponemos de confirmación de stock' in text
