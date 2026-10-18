"""Aggregate evaluated review candidates; keep case-level evidence private."""
import json
from pathlib import Path
from collections import Counter
from app import review_policy
from app.jev import validate_response
from app.schemas import NormalizedAnalysis
from jsonschema import validate
from scripts.evaluate_review_policy import invariant

ROOT=Path(__file__).resolve().parents[1]


def main():
    isolated=json.loads((ROOT/'reports/review-policy-isolation.json').read_text())
    first=json.loads((ROOT/'reports/private/review-support-development.json').read_text())
    final=json.loads((ROOT/'reports/private/review-facts-development.json').read_text())
    assert first['complete'] and final['complete']
    schema=json.loads((ROOT/'contracts/article_analysis.schema.json').read_text())
    correct=lambda r: r['reference']['Is_Risk']==r['prediction']['is_risk'] and r['reference']['Urgent']==r['prediction']['urgent'] and {s.strip() for s in (r['reference'].get('Affected_Supplier_IDs')or'').split(';') if s.strip()}==set(r['prediction']['affected_supplier_ids'])
    controls=[];private=[]
    for row in final['results'].values():
        p=row['prediction'];invariant(row['before'],p);NormalizedAnalysis.model_validate(p);validate(p,schema)
        if row.get('verification'):validate_response(row['effective_payload'],row['verification']['response'])
        if row.get('facts'):validate_response(row['facts_payload'],row['facts']['response'])
        if row['group']=='controlled_policy':
            sound=any(review_policy.alarm_decision(a)['sound_eligible'] for a in p['assessments'])
            controls.append({'case':row['case'],'expected_review':row['expected_review'],'actual_review':p['analysis_status']=='review','expected_sound':row['expected_sound'],'actual_sound':sound,'passed':(p['analysis_status']=='review')==row['expected_review'] and sound==row['expected_sound'],
                'scope':'Controlled base predictions, real JEV support verification; not full classifier accuracy'})
        elif row['group']=='training':
            private.append({'case':row['case'],'headline':(row.get('effective_payload') or {}).get('state',{}).get('article',{}).get('headline'),
                'reference':row['reference'],'before':row['before'],'after':p,'correct':correct(row),
                'discarded_supplier_doubts':[d for d in p['review_details'] if d['requires_review'] and d['supplier_id'] and d['supplier_id'] not in p['affected_supplier_ids']],
                'verification':row['verification'],'facts':row['facts']})
    rows=[r for r in final['results'].values() if r['group']=='training']
    known_errors=[r for r in rows if not correct(r)]
    newly_auto=[r for r in rows if r['before']['analysis_status']=='review' and r['prediction']['analysis_status']=='done']
    usage=Counter()
    for call in final['calls']:
        for k,v in call['usage'].items():
            if not k.startswith('_') and isinstance(v,(int,float)):usage[k]+=v
    blockers_before=Counter(d['code'] for row in rows for d in row['before']['review_details'] if d['requires_review'])
    blockers_after=Counter(d['code'] for row in rows for d in row['prediction']['review_details'] if d['requires_review'])
    report={'policy_version':'review-1.1.0-candidate','source_question_version':'link-3.0.0-dev',
        'sample':'30 training; all reviewed predictions included; development comparison, not independent evaluation',
        'runtime_enabled':False,'default_profile':'1.0.0','prediction_changes':0,'priority_changes':0,
        'stages':{'3.0_original':isolated['before'],'policy_only':isolated['policy_only'],
            'review_1_0_support':first['metrics']['after'],'review_1_1_facts':final['metrics']['after']},
        'causes_before':isolated['causes_before'],'causes_after':final['causes_after'],
        'codes_before':dict(blockers_before),'codes_after':dict(blockers_after),
        'controls':controls,'new_correct_automatic':sum(correct(r) for r in newly_auto),
        'new_incorrect_automatic':sum(not correct(r) for r in newly_auto),
        'known_error_cases':len(known_errors),'known_errors_still_reviewed':sum(r['prediction']['analysis_status']=='review' for r in known_errors),
        'positive_risk_automatic':final['metrics']['after']['automatic']['risk']['tp'],
        'training_sound_eligible':sum(review_policy.alarm_decision(a)['sound_eligible'] for r in rows for a in r['prediction']['assessments']),
        'consumption':{'support_trial':first['requests'],'facts_trial':final['requests_this_trial'],'total':final['requests_shared'],
            'retries':sum(c['attempt']>1 for c in final['calls']),'statuses':dict(Counter(str(c['status']) for c in final['calls'])),
            'counter_before':first['global_calls_before'],'counter_after':final['global_calls_after'],'shared_limit':126,
            'provider_reported_usage':dict(usage),'duration_seconds_sum':sum(c['seconds'] for c in final['calls']),
            'original_classification_replayed':False,'valid_support_responses_reused':first['requests']},
        'promotion_guards_passed':all(c['passed'] for c in controls) and all(r['prediction']['analysis_status']=='review' for r in known_errors) and not any(not correct(r) for r in newly_auto) and len(newly_auto)>0,
        'recommendation':'Adopt1.1 as the review policy of the development candidate; do not replace default1.0 or silently apply to RSS/2.2. Independent scope evaluation and runtime integration remain required before general production promotion.',
        'limitations':['Small inspected training sample; zero errors among12automatic cases is not a production accuracy guarantee.',
            'Five known erroneous cases remain reviewed; classification itself is unchanged.',
            'Some clearly non-operational topics still have conflicting support and remain reviewed; do not lower thresholds just to remove these.',
            'Three training urgent cases become automatic but none meets all original0.8audio thresholds. Controlled urgent case does.',
            'Validation remains retrospective; no test/LiveDay/answer-key access. Paid RSS periodic remains off.']}
    (ROOT/'reports/review-policy-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'app/review_evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'reports/private/review-policy-before-after.json').write_text(json.dumps(private,ensure_ascii=False,indent=2)+'\n')
    lines=['# Diagnóstico privado · 23 revisiones originales de3.0','',
        'Solo training; referencias para evaluación de desarrollo. Ninguna cambia las proposiciones enviadas aJEV.','',
        '|Noticia|Referencia riesgo/urgencia/proveedores|Predicción|Antes→después|Dudas que permanecen|','|---|---|---|---|---|']
    for r in private:
        if r['before']['analysis_status']!='review':continue
        ref=r['reference'];p=r['after'];expected=str(ref.get('Affected_Supplier_IDs')or'ninguno')
        title=(r['headline'] or '').replace('|','/')
        lines.append(f"|{r['case']} · {title}|{ref['Is_Risk']}/{ref['Urgent']}/{expected}|{p['is_risk']}/{p['urgent']}/{' ; '.join(p['affected_supplier_ids'])or'ninguno'}|revisión→{p['analysis_status']}|{', '.join(p['review_reasons'])or'ninguna; soporte trazado enJSON'}|")
    lines.extend(['','Las omisiones de riesgoN018/N025 y el vínculoS032deN039 siguen revisados; los2FPdeproveedorN037 y la falsa urgencia restante también. No se reetiquetan ni se consideran arreglados. Porcampo y respuestaexacta:review-policy-diagnosis.json yreview-policy-before-after.json.'])
    (ROOT/'reports/private/REVISION_23_DIAGNOSTICO.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'before_review':isolated['before']['review_count'],'after_review':final['metrics']['after']['review_count'],
        'new_correct_automatic':report['new_correct_automatic'],'controls_passed':all(c['passed'] for c in controls),
        'guard':report['promotion_guards_passed'],'known_errors':len(known_errors),'consumption':report['consumption']}))
if __name__=='__main__':main()
