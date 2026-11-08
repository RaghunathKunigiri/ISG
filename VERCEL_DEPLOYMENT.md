# Deploying ISG to Vercel

## Prerequisites

Vercel does not provide a persistent PostgreSQL database or Redis service for this application. Provision external services before deployment:

- A hosted PostgreSQL database such as Neon, Supabase, or Vercel Postgres.
- Optional Redis from Upstash or another hosted Redis provider.
- Object storage if file attachments are required.

## Import the repository

In Vercel, import `RaghunathKunigiri/ISG` and use this repository as the project root. The root `vercel.json` builds the React frontend and exposes the FastAPI application under `/api/*`.

## Environment variables

Configure these production environment variables:

```text
APP_ENV=production
SECRET_KEY=<long-random-secret>
DATABASE_URL=<hosted-postgresql-connection-url>
DATABASE_SYNC_URL=<same-postgresql-url>
REDIS_URL=<hosted-redis-url>
CELERY_BROKER_URL=<hosted-redis-url>/1
CELERY_RESULT_BACKEND=<hosted-redis-url>/2
CORS_ORIGINS=["https://your-project.vercel.app"]
```

For the frontend, `VITE_API_URL` can be empty for a same-domain Vercel deployment. For a separate backend deployment, set it to the backend origin or to a URL ending in `/api/v1`.

## Database setup

From a machine with PostgreSQL access:

```powershell
cd backend
$env:DATABASE_URL='<hosted-postgresql-url>'
$env:DATABASE_SYNC_URL='<hosted-postgresql-url>'
py -3 -m alembic upgrade head
```

Then seed data if needed:

```powershell
py -3 -m app.seed.seed_data
```

Celery workers, Celery Beat, Redis-backed scheduled jobs, and MinIO require a persistent worker runtime or separate hosted service. They are not run by the Vercel frontend/API deployment.
