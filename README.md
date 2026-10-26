# Starpull

Finds open, beginner-friendly issues in open-source projects that use the same packages you already do. Formerly FirstPR.

Live: https://starpull.vercel.app

## Run locally with Docker

Needs Docker Desktop. From a fresh clone:

```
docker compose up --build
```

This starts Postgres 17 (schema applied automatically from `sql/schema/`) and the API at http://localhost:8000 (`/health`, `/docs`). The local database starts empty; to load a few real repos, put a `GITHUB_TOKEN` in `.env` (see `.env.example`) and run:

```
docker compose run --rm api python -m ingest.seed_load --limit 10
```

For the website, run `npm install && npm run dev` in `web/` and open http://localhost:5173. Signing up goes through GitHub, so the website also needs `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` in `.env` (an OAuth app with the callback `http://localhost:5173/api/auth/github/callback`). Without them you can still try every endpoint at http://localhost:8000/docs. `docker compose down -v` stops everything and wipes the local database.
