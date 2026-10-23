"""Local-only iframe contract server: real auth/CSP; catalogue API fixtures.

No database, inference, RSS fetch or external communication. Never deploy this.
Run: PYTHONPATH=. .venv/bin/python tests/embed_server.py
"""
from pydantic import SecretStr
from fastapi.responses import JSONResponse
from app.main import app
from app.db import get_db
from app.settings import settings
from tests.unit.test_embedding import MemorySessions,BASE
settings.app_base_url=BASE
settings.admin_password=SecretStr('MOCK-iframe-password')
settings.session_secret=SecretStr('MOCK-session-signing-key-only-tests')
settings.typesafe_api_key=SecretStr('')
settings.llm_provider='none'
db=MemorySessions();app.dependency_overrides[get_db]=lambda:db

@app.middleware('http')
async def fixture_reads(request,call_next):
    path=request.url.path
    data={'/api/overview':{'received':0,'processed':0,'pending':0,'active_incidents':0,'urgent_suppliers':0,'healthy_sources':0},
      '/api/suppliers':{'items':[],'total':0},'/api/articles':[], '/api/sources':[], '/api/batches':[],
      '/api/alerts':{'items':[],'unread':0,'cursor':0},'/api/plans':{'plans':{}},'/api/materials':[]}
    if request.method=='GET' and path in data:return JSONResponse(data[path])
    return await call_next(request)

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=4188,access_log=False)
