"""Create a fresh, reasoned control sample BEFORE obtaining any model responses."""
import json,hashlib
from datetime import datetime,timezone
from pathlib import Path
from sqlalchemy import select
from app.db import Session
from app.models import Supplier
from scripts.window_common import ROOT,save
from app.candidate_engine import VERSIONS

PATH=ROOT/'reports/private/window-final-sample.json'
FREEZE=ROOT/'reports/window-final-evaluation-freeze.json'


def create():
    if PATH.exists():return json.loads(PATH.read_text())
    archived=ROOT/'reports/window-final-controls.json'
    if archived.exists():
        PATH.parent.mkdir(parents=True,exist_ok=True)
        PATH.write_bytes(archived.read_bytes())
        return json.loads(PATH.read_text())
    with Session() as db:ss={s.id:s.data for s in db.scalars(select(Supplier))}
    rows=[]
    def add(key,headline,summary,ids=(),risk='N',urgent='N',reason='',review=None,scorable=True):
        rows.append({'case':key,'data':{'news_id':'QA-FINAL-'+key,'headline':headline,'summary':summary,
            'published_date':'2026-10-18T22:00:00+00:00','source':'SINTÉTICO CONTROLADO · evaluación interna, no RSS real',
            'language':'en','context_id':'exercise'},'reference':{'Is_Risk':risk,'Urgent':urgent,'Affected_Supplier_IDs':'; '.join(ids)} if scorable else None,
            'reasoned_reference':reason,'expected_review':review,'sound_must_be_false':urgent=='N' or review is True})
    add('harmless_hangzhou','Hangzhou school opens a science exhibition','Local school pupils exhibit astronomy projects. The event concerns education; no commercial restriction is reported.',reason='Education activity has no operational relation to the material suppliers in Hangzhou.')
    add('passenger_cork','Cork airport reports record holiday passenger traffic','More holiday passengers used Cork airport. Cargo, manufacturing and deliveries are not affected.',reason='Passenger statistics are different from biologics production; shared city alone is insufficient.')
    add('sport_valencia','Valencia celebrates a local athletics award','A city athlete receives a medal. Commercial production and deliveries continue normally.',reason='Sport is unrelated to starch supply; source explicitly preserves normal activity.')
    add('culture_mainz','Mainz museum hosts a Rhine painting exhibition','Visitors can see paintings of the river Rhine. No shipping or industrial event is reported.',reason='River mention in a museum event is not a waterway or glass-supplier interruption.')
    add('policy_debate','European Parliament debates future publication rules','Members discussed a proposal about public publication of policy documents. No law, transport restriction or pharmaceutical production change was adopted.',reason='Discussion of document publication has no actual supplier operational impact.')
    add('wind_oslo','Oslo wind orchestra wins international competition','A youth wind orchestra won an award. This is a music competition, not an energy or industrial event.',reason='Wind is musical activity, not power restrictions or lipid production.')
    for key,sid in [('named_positive_biologic','S008'),('named_positive_labels','S023')]:
        name=ss[sid]['name'];add(key,name+' expands approved capacity',name+' obtained approval to expand capacity. Existing production and deliveries continue normally, with no adverse operational change.',[sid],reason='Exact organisation identity retained; positive expansion is neither supply risk nor urgency.',review=False)
    for key,sid in [('partial_leaflets','S024'),('partial_filters','S027')]:
        name=ss[sid]['name'];add(key,name+' reports limited production reduction',name+' reports a 20% reduction of production capacity for two days during scheduled repairs. Current deliveries remain on time and normal output returns after repairs.',[sid],'Y','N','Named organisation and partial capacity reduction support risk. Short, limited event with preserved deliveries supports regular follow-up, not urgent coordination.')
    name=ss['S009']['name'];add('short_delivery',name+' reports a brief delivery slowdown',name+' reports a minor delivery slowdown lasting two days. Production is normal; existing delivery commitments remain covered and there is no serious near-term supply delay.', ['S009'],'Y','N','A named slowdown remains risk; explicit limited timing and preserved commitments support non-urgency.')
    add('sea_not_rail','Asia-Europe sea freight faces a limited two-day slowdown','Commercial sea freight from Asia to Europe will operate at reduced capacity for two days. Rail freight between Asia and Europe remains normal. The reduction is minor and no serious near-term supply stoppage is expected.', ['S032'],'Y','N','Catalog explicitly declares S032 maritime corridor; S033 is rail and explicitly unaffected. No headquarters or undocumented route inference.')
    for key,sid in [('urgent_named_api','S001'),('urgent_named_bags','S025'),('urgent_named_vials','S015'),('urgent_named_capsules','S036')]:
        name=ss[sid]['name'];add(key,name+' halts all production after destructive fire',name+' has halted all production and all shipments after a destructive factory fire. The company reports severe damage, no restart date and immediate cancellation of forthcoming deliveries. No alternate capacity is confirmed.',[sid],'Y','Y','Exact organisation, active serious production and shipment stoppage with no recovery date supports immediate procurement coordination. Alternate capacity is not assumed.',review=False)
    add('two_affected_sites','Limited production restrictions in Valencia and Barcelona','Material manufacturers in Valencia and Barcelona report a 10% output reduction for two days due to scheduled electricity maintenance. Current delivery commitments remain on time. Other cities are unaffected.', ['S011','S018'],'Y','N','Both catalog cities and manufacturing activities are within stated scope. Potential class exposure is not proven damage to individual firms; limited duration and intact deliveries keep urgency N.')
    add('lodz_alias','Minor production restrictions in Łódź','Manufacturers in Łódź will reduce output by 10% for two days during planned maintenance. Deliveries remain on schedule and operations in other cities are normal.', ['S019'],'Y','N','Łódź is a verified alias of catalog Lodz. Potential manufacturing exposure; minor short interruption with preserved deliveries is not urgent.')
    # These six have deliberately underdetermined reference fields. Never label an
    # unknown association as a true negative to inflate accuracy. Safety/review is
    # assessed separately, not included in binary precision denominators.
    add('unknown_taizhou','Jiangsu industrial restrictions announced','Industrial sites in Jiangsu will face restrictions. The article does not name individual companies or identify the province of any Taizhou supplier.',reason='S003 Taizhou province is unknown; essential location cannot be completed from an expected label.',review=True,scorable=False)
    add('unknown_route','River barge terminal closed in a region','A river barge terminal is closed after a local equipment failure. The affected firms and transport routes are not specified.',reason='Catalog does not document individual suppliers using this terminal or a barge route.',review=True,scorable=False)
    add('unknown_site','Inspection at an unidentified packaging facility','Inspectors paused output at a packaging facility. The operator, city, country and material have not been identified.',reason='Missing essential identity and geography prevent confirmation or confident exclusion of the relevant supplier.',review=True,scorable=False)
    add('unknown_scope','Possible electricity restrictions near Taizhou','Officials are considering restrictions near a city called Taizhou. The province, affected activities and implementation date are not specified.',reason='Both province and enacted operational scope are missing; potential future action is not actual urgent supplier damage.',review=True,scorable=False)
    add('unknown_timing','Unverified report about production at Hsinchu Membrane Tech','An unverified message says Hsinchu Membrane Tech may face an operational issue. It does not say what happened, whether output changed or when any effect could occur.',reason='Organisation identity exists, but risk, impact and timing are uncertain. Identity alone must not prove risk or urgency.',review=True,scorable=False)
    add('unknown_transport_mode','Asia-Europe transport interruption reported without a mode','A report says some transport between Asia and Europe may be interrupted. It does not specify sea, rail or air, affected operators or the operational timing.',reason='S032/S033 explicit corridors share geography but mode and real impact are missing; do not assume maritime or rail.',review=True,scorable=False)
    result={'authored_at':datetime.now(timezone.utc).isoformat(),'kind':'author-generated controlled sample, not independent RSS generalisation','catalog_hash':hashlib.sha256(json.dumps(ss,sort_keys=True).encode()).hexdigest(),'cases':rows}
    assert len(rows)==24 and sum(r['reference'] is not None for r in rows)==18
    save(PATH,result);return result


def freeze():
    sample=create()
    files=['app/candidate_matching.py','app/candidate_review.py','app/candidate_engine.py','app/payload_cache.py','app/review_support.py','app/review_facts.py','app/link_candidate.py','app/link_analysis.py','app/link_questions.py','app/duration.py','app/geography.py','config/geography.json','config/risk_policy.json','reference/jev_requests.py','reference/scoring.py']
    value={'created_at':sample['authored_at'],'versions':VERSIONS,'sample_hash':hashlib.sha256(PATH.read_bytes()).hexdigest(),
      'sample_count':24,'scorable':18,'underdetermined_safety_controls':6,'initial_request_ceiling':240,'maximum_attempts':720,
      'hypothesis':'Candidate3.3 recovers compatible potential exposure and limited-production risk while review1.2 reduces irrelevant-topic review; unknown operational scope stays uncertain.',
      'criteria_before_responses':['Keep default1.0 unless evidence sufficient beyond training and controlled tests; not independent RSS accuracy',
        'No new automatic jointly erroneous case on the 18 scorable controls; all reviewed predictions remain in TP/FP/FN',
        'All four named serious stoppages correctly riskY/urgentY, at least two automatic',
        'Two named positive suppliers retain identity and riskN/urgentN automatically',
        'No automatic urgent decision for short/minor disruptions with preserved deliveries',
        'Unknown province, site, mode or route must not be represented as confirmed individual effect; report review failures separately',
        'Training known errors and operational consequences disclosed, no adoption by aggregate F1 alone'],
      'files':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files},'held_out':'No validation/test/LiveDay/answer key; new controlled sample authored before calls. Any post-inspection change makes this development.'}
    if FREEZE.exists():assert json.loads(FREEZE.read_text())==value,'Frozen candidate or sample changed'
    else:save(FREEZE,value)
    return value
if __name__=='__main__':print(json.dumps(freeze()))
