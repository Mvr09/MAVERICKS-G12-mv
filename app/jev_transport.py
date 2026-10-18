"""Bound independent fan-out to provider context without changing questions/state."""
import json
from collections import Counter
from app.settings import ROOT, POLICY
from app.jev import ProviderError, validate_response
from app.models import RequestCache
from app.importer import digest

CONFIG=json.loads((ROOT/'config/jev_transport.json').read_text())
VERSION=CONFIG['version']


def encoded_size(payload):
    try:return len(json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode())
    except (TypeError,ValueError):raise ProviderError('JEV_REQUEST_INVALID_LOCAL')


def partition(payload,budget=None):
    budget=budget or CONFIG['request_json_budget_bytes']
    for q in payload['questions'].values():
        if q['type']=='choice' and len(q['criteria'])>CONFIG['max_choice_options']:
            raise ProviderError('JEV_CHOICE_LIMIT_LOCAL')
        if q['type']=='score' and not 2<=len(q['criteria'])<=CONFIG['max_score_levels']:
            raise ProviderError('JEV_SCORE_LIMIT_LOCAL')
    if encoded_size(payload)<=budget:return [payload]
    parts=[];questions={}
    for key,q in payload['questions'].items():
        combined={**payload,'questions':{**questions,key:q}}
        if encoded_size(combined)>budget:
            if questions:parts.append({**payload,'questions':questions})
            questions={key:q}
            if encoded_size({**payload,'questions':questions})>budget:
                raise ProviderError('JEV_QUESTION_CONTEXT_LOCAL')
        else:questions[key]=q
    if questions:parts.append({**payload,'questions':questions})
    return parts


class BoundedFanoutClient:
    def __init__(self,client):
        self.client=client
        self.transport_records=[]

    def __getattr__(self,name):return getattr(self.client,name)

    def ask(self,payload,stage,deadline):
        key=digest({'payload':payload,'questions':POLICY['question_version']})
        keys = [key] + [digest({'request':key,'run_key':run}) for run in (self.run_key, *getattr(self.client,'reuse_runs',())) if run]
        cached = next((row for cache_key in keys if (row := self.db.get(RequestCache,cache_key)) is not None),None)
        if cached:
            self.transport_records.append({'stage':stage,'mode':'cached_complete','version':VERSION,'origin_transport':cached.response.get('_transport')})
            return self.client.ask(payload,stage,deadline)
        parts=partition(payload)
        record={'stage':stage,'version':VERSION,'mode':'single' if len(parts)==1 else 'partitioned',
            'logical_payload_hash':digest(payload),'logical_bytes':encoded_size(payload),'parts':[]}
        self.transport_records.append(record)
        if len(parts)==1:return self.client.ask(payload,stage,deadline)
        answers={};usage=Counter();models=set()
        for i,p in enumerate(parts):
            part_stage=f'{stage}.part{i+1}'
            meta={'stage':part_stage,'payload_hash':digest(p),'bytes':encoded_size(p),'question_ids':list(p['questions'])}
            record['parts'].append(meta)
            response=self.client.ask(p,part_stage,deadline)
            models.add(response['model'])
            if set(answers)&set(response['answers']):raise ProviderError('CONTRACT_DUPLICATE_PART')
            answers.update(response['answers'])
            for name,value in response['usage'].items():
                if isinstance(value,(int,float)) and not isinstance(value,bool):usage[name]+=value
        if models!={payload['model']}:raise ProviderError('MODEL_MISMATCH')
        merged=validate_response(payload,{'model':payload['model'],'answers':answers,'usage':dict(usage)})
        # A combined response is explicitly labelled; each original response and
        # request remains in the private audit/cache and durable ApiCall ledger.
        self.db.merge(RequestCache(id=key,response={**merged,'_transport':record}));self.db.commit()
        return merged
