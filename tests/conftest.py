import pytest


# Session-wide because a closed psycopg pool can't be reopened by the next test module.
@pytest.fixture(scope="session")
def db():
    from api.db import pool
    pool.open()
    yield
    pool.close()
