import pytest
from pathlib import Path
from sqlalchemy.engine import make_url
from app.db import engine,Base,Session
from app import models
from app.importer import import_excel
from app.cli import seed

@pytest.fixture(autouse=True)
def clean_test_database():
    # Destruction is strictly limited to the dedicated database created for tests.
    if make_url(str(engine.url)).database!='radar_test':
        pytest.fail('Pruebas requieren DATABASE_URL con base dedicada radar_test')
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with engine.begin() as c:
        c.exec_driver_sql('CREATE TABLE IF NOT EXISTS alembic_version(version_num varchar(32) primary key)')
        c.exec_driver_sql('DELETE FROM alembic_version');c.exec_driver_sql("INSERT INTO alembic_version VALUES ('0002')")
    with Session() as db:
        seed(db)
        db.get(models.Grant,'initial-training-3').used=0  # Only MOCK transport in isolated test database.
        for file in ('supplier_training.xlsx','supplier_validation.xlsx','supplier_test.xlsx','supplier_liveday.xlsx'):
            import_excel(db,Path('inputs',file).read_bytes(),file)
        db.commit()
    yield
