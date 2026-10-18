"""Actual reconciliation/alert path, synthetic DB only, no network."""
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4
import pytest
from sqlalchemy import select
from sqlalchemy.engine import make_url
from app.db import Session,engine,Base
from app.models import Article,Supplier,Alert,Incident
from app.incidents import reconcile
from scripts.review_scenarios import cases
from tests.unit.test_review_policy import verified
from app import review_policy
from app.importer import digest

pytestmark=pytest.mark.skipif(make_url(str(engine.url)).database!='radar_test',reason='Isolated synthetic DB only')


def test_one_incident_urgent_with_score_warning_other_uncertain_remains_silent():
    Base.metadata.create_all(engine)
    c=cases('jev-1.13.0')[0];r=review_policy.apply(c['prediction'],verified(c))
    with Session() as db:
        for sid in ('QA901','QA902'):
            if not db.get(Supplier,sid):db.add(Supplier(id=sid,data={**c['suppliers'][0],'supplier_id':sid}))
        data={**c['data'],'published_date':'2026-10-18T12:00:00+00:00'}
        a=Article(origin_key='MOCK-REVIEW-'+str(uuid4()),context='exercise',news_id='MOCK-REVIEW',data=data,content_hash=digest(data));db.add(a);db.flush()
        r['article_id']=a.id;r['analysis_status']='review'
        second=deepcopy(r['assessments'][0]);second.update(supplier_id='QA902',needs_review=True,review_reasons=['association_support_insufficient'],human_attention='verify_decision')
        r['assessments'].append(second)
        reconcile(db,a,r);db.flush()
        alerts=db.scalars(select(Alert).join(Incident).where(Incident.history[0]['article_id'].as_string()==a.id)).all()
        assert len(alerts)==2
        aa={row.data['supplier_id']:row.data for row in alerts}
        assert aa['QA901']['sound_eligible'] and not aa['QA901']['needs_review']
        assert aa['QA901']['priority_requires_review'] and aa['QA901']['human_attention']=='immediate_contact'
        assert not aa['QA902']['sound_eligible'] and aa['QA902']['needs_review']
        # No-repeat handling remains downstream; persisted eligibility is local.
        db.rollback()
