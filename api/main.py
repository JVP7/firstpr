"""Starpull API. Run locally with: uvicorn api.main:app --reload"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from api.db import pool  # noqa: E402
from api.routes import auth, issues, me, saved, teams  # noqa: E402
from api.security import security_middleware  # noqa: E402


@asynccontextmanager
async def lifespan(app):
    pool.open()
    yield
    pool.close()


# Interactive docs are off unless ENABLE_DOCS=1 (they load scripts from a CDN and map the API).
docs = os.getenv("ENABLE_DOCS") == "1"
app = FastAPI(title="Starpull API", lifespan=lifespan, docs_url="/docs" if docs else None,
              redoc_url=None, openapi_url="/openapi.json" if docs else None)
# No CORS: the frontend reaches the API through a same-origin /api proxy (Vite in dev, Vercel in prod).
app.middleware("http")(security_middleware)
for module in (auth, me, issues, saved, teams):
    app.include_router(module.router)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # FastAPI echoes the rejected value ("input") by default, which would send passwords back
    # in response bodies; keep only where and why.
    errors = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse({"detail": errors}, status_code=422)


@app.get("/health")
def health():
    with pool.connection() as conn:
        conn.execute("SELECT 1")
    return {"ok": True}
