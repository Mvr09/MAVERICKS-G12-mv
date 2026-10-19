"""Authenticated private import. Never commits inputs/references or repeats JEV."""
import sys,json
from pathlib import Path
import httpx
from app.settings import settings
base=sys.argv[2].rstrip('/') if len(sys.argv)>2 else 'https://mavericks-g12-mv-production.up.railway.app'
with httpx.Client(base_url=base,timeout=120,headers={'Origin':base}) as c:
 auth=c.post('/api/session',json={'password':settings.admin_password.get_secret_value()});auth.raise_for_status();c.headers['X-CSRF-Token']=auth.json()['csrf']
 with Path(sys.argv[1]).open('rb') as f:
  r=c.post('/api/campaigns/import',files={'file':('campaign-private.json',f,'application/json')});r.raise_for_status();print(json.dumps(r.json()))
 c.delete('/api/session')
