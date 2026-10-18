"""Forward-only preservation check in a dedicated synthetic PostgreSQL database."""
import json,os,subprocess,sys
import psycopg
from sqlalchemy import create_engine,text,inspect
from sqlalchemy.engine import make_url
from app.settings import settings
from app.models import Article,Draft
from sqlalchemy.orm import Session
url=make_url(settings.database_url);target=url.set(database='radar_migration_test_v3')
with psycopg.connect(host=url.host,port=url.port,user=url.username,password=url.password,dbname='postgres',autocommit=True) as conn:
 if not conn.execute("SELECT 1 FROM pg_database WHERE datname='radar_migration_test_v3'").fetchone():conn.execute('CREATE DATABASE radar_migration_test_v3')
env=dict(os.environ);env['DATABASE_URL']=target.render_as_string(hide_password=False)
e=create_engine(target)
with e.connect() as c:has_schema=inspect(e).has_table('alembic_version');current=c.execute(text('select version_num from alembic_version')).scalar() if has_schema else None
if current!='0008':
 subprocess.run([sys.executable,'-m','alembic','upgrade','0007'],env=env,check=True)
 with e.begin() as c:
  c.execute(text("INSERT INTO suppliers(id,data) VALUES ('S999','{}'::json) ON CONFLICT DO NOTHING"))
  c.execute(text("INSERT INTO incidents(id,context,supplier_id,event_type,signature,state,priority,historical_priority,event_date,revision,history) VALUES ('MOCK-INC','exercise','S999','other','MOCK','active',1,1,'2026-10-18',1,'[]'::json) ON CONFLICT DO NOTHING"))
  c.execute(text("INSERT INTO drafts(id,supplier_id,incident_id,kind,text,context_hash) VALUES ('MOCK-OLD','S999','MOCK-INC','supplier','MOCK original persisted','MOCK') ON CONFLICT DO NOTHING"))
 subprocess.run([sys.executable,'-m','alembic','upgrade','head'],env=env,check=True)
with e.connect() as c:
 old=c.execute(text("select incident_id,text,article_id,evidence_snapshot from drafts where id='MOCK-OLD'")).one()
 assert old==('MOCK-INC','MOCK original persisted',None,None)
with Session(e) as db:
 if not db.get(Article,'MOCK-ART'):
  db.add(Article(id='MOCK-ART',origin_key='MOCK-MIGRATION',context='rss',news_id='MOCK',data={'headline':'MOCK'},content_hash='MOCK'));db.flush()
  db.add(Draft(id='MOCK-NEW',supplier_id='S999',incident_id=None,article_id='MOCK-ART',kind='verification',text='MOCK inquiry',context_hash='MOCK',evidence_snapshot={'exposure_status':'potential_unconfirmed'}));db.commit()
with Session(e) as db:assert db.get(Draft,'MOCK-NEW').evidence_snapshot['exposure_status']=='potential_unconfirmed'
print(json.dumps({'schema':'0008','old_draft_preserved':True,'source_inquiry_persisted_after_reconnect':True,'database':'radar_migration_test_v3','destructive_operations':False}))
