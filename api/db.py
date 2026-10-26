"""Postgres connection pool and helpers for running the files in sql/."""

import os
import re
from functools import cache
from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
# `:name` placeholders as used with psql; the lookbehind skips `::type` casts.
PLACEHOLDER = re.compile(r"(?<!:):([A-Za-z_]\w*)")

pool = ConnectionPool(
    os.environ["DATABASE_URL"],
    min_size=1,
    max_size=int(os.getenv("DB_POOL_SIZE", "5")),
    # prepare_threshold=None keeps this working through Supabase's transaction pooler.
    # sslmode=require refuses an unencrypted fallback; set DB_SSLMODE=disable for a local Postgres.
    kwargs={"prepare_threshold": None, "row_factory": dict_row, "sslmode": os.getenv("DB_SSLMODE", "require")},
    open=False,
)


@cache
def load_sql(name):
    """Read sql/<name>.sql and convert it to psycopg's %(name)s style."""
    text = (SQL_DIR / f"{name}.sql").read_text()
    lines = [line for line in text.splitlines() if not line.lstrip().startswith("--")]
    return PLACEHOLDER.sub(r"%(\1)s", "\n".join(lines).replace("%", "%%"))


def run_file(conn, file, /, **params):
    """Run a sql/ file and return all rows (empty for statements without RETURNING)."""
    cur = conn.execute(load_sql(file), params)
    return cur.fetchall() if cur.description else []


def get_conn():
    """FastAPI dependency: one pooled connection per request, committed on success."""
    with pool.connection() as conn:
        yield conn
