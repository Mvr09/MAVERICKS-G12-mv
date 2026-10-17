import psycopg
from app.settings import settings
from sqlalchemy.engine import make_url

url = make_url(settings.database_url)
with psycopg.connect(
    host=url.host,
    port=url.port,
    user=url.username,
    password=url.password,
    dbname="postgres",
    autocommit=True,
) as c:
    if not c.execute("SELECT 1 FROM pg_database WHERE datname='radar_test'").fetchone():
        c.execute("CREATE DATABASE radar_test")
print("Base dedicada radar_test disponible")
