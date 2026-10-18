"""Exact effective-payload reuse across candidate generations, in PostgreSQL.

Run keys still isolate attempt accounting. They do not invalidate otherwise
identical model questions. Legacy/vote experiments retain their old client.
"""
from app.jev import JevClient, validate_response
from app.models import RequestCache
from app.importer import digest
from app.settings import POLICY


class PayloadCacheClient(JevClient):
    def __init__(self,*args,reuse_runs=(),**kwargs):
        super().__init__(*args,**kwargs)
        self.reuse_runs=tuple(reuse_runs)
        self.reuse_details=[]

    def ask(self,payload,stage,deadline):
        key=digest({'payload':payload,'questions':POLICY['question_version']})
        keys=[('effective_payload',key)]+[(run,digest({'request':key,'run_key':run})) for run in self.reuse_runs]
        for origin,cache_key in keys:
            cached=self.db.get(RequestCache,cache_key)
            if cached:
                response=validate_response(payload,cached.response)
                self.cached_stages.append(stage)
                self.reuse_details.append({'stage':stage,'source':origin,'payload_hash':digest(payload)})
                if cache_key!=key:self.db.merge(RequestCache(id=key,response=response));self.db.commit()
                return response
        response=super().ask(payload,stage,deadline)
        self.db.merge(RequestCache(id=key,response=response));self.db.commit()
        return response
