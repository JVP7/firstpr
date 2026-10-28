"""Postgres connection pool and helpers for running the files in sql/."""

import logging
import os
import re
from functools import cache
from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
# `:name` placeholders as used with psql; the lookbehind skips `::type` casts.
PLACEHOLDER = re.compile(r"(?<!:):([A-Za-z_]\w*)")
# SQL_LOG=1 prints every sql/ file the API runs, so a live demo can show the SQL behind each click.
SQL_LOG = os.getenv("SQL_LOG") == "1"
HIDDEN_PARAMS = {"email", "password_hash"}
log = logging.getLogger("starpull.sql")

pool = ConnectionPool(
    os.environ["DATABASE_URL"],
    min_size=1,
    max_size=int(os.getenv("DB_POOL_SIZE", "10")),
    # prepare_threshold=None keeps this working through Supabase's transaction pooler.
    # sslmode=require refuses an unencrypted fallback; set DB_SSLMODE=disable for a local Postgres.
    kwargs={"prepare_threshold": None, "row_factory": dict_row, "sslmode": os.getenv("DB_SSLMODE", "require")},
    # Test each connection before handing it out: Supabase drops idle ones, which otherwise
    # surface as a 500 on the next request.
    check=ConnectionPool.check_connection,
    open=False,
)


@cache
def sql_text(name):
    """sql/<name>.sql without its comment lines, placeholders left as written."""
    lines = (SQL_DIR / f"{name}.sql").read_text().splitlines()
    return "\n".join(line for line in lines if not line.lstrip().startswith("--")).strip()


@cache
def load_sql(name):
    """Read sql/<name>.sql and convert it to psycopg's %(name)s style."""
    return PLACEHOLDER.sub(r"%(\1)s", sql_text(name).replace("%", "%%"))


def run_file(conn, file, /, **params):
    """Run a sql/ file and return all rows (empty for statements without RETURNING)."""
    cur = conn.execute(load_sql(file), params)
    rows = cur.fetchall() if cur.description else []
    if SQL_LOG:
        log.info(describe_run(file, params, len(rows) if cur.description else cur.rowcount))
    return rows


def describe_run(file, params, count):
    shown = ", ".join(f"{k}={'<hidden>' if k in HIDDEN_PARAMS else v!r}" for k, v in params.items())
    return f"sql/{file}.sql  ({shown})  -> {count} row(s)\n{sql_text(file)}\n"


def get_conn():
    """FastAPI dependency: one pooled connection per request, committed on success."""
    with pool.connection() as conn:
        yield conn
