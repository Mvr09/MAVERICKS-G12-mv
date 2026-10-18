"""Pure unit tests: override the parent's dataset-importing database fixture."""
import pytest


@pytest.fixture(autouse=True)
def clean_test_database():
    # No connection, database reset, Excel import or external request is needed.
    yield
