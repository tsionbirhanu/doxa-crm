# Doxa CRM - Short Project Status

Last checked: 2026-06-15

## What exists now

- The project currently has a strong backend foundation.
- The frontend folder only has this README right now. No frontend app code is built yet.
- The backend is a FastAPI API with PostgreSQL/Supabase support, Redis, Celery workers/Beat, Meilisearch, Docker, Alembic migrations, JWT auth, users, accounts, contacts, leads, pipelines, deals, activities, tasks, campaigns, customer projects, reporting, global search, webhooks, audit logging, rate limiting, and GDPR contact export/purge.

## Backend summary

- `app/main.py` creates the FastAPI app and exposes `/health`.
- `app/config.py` loads environment variables from `.env`.
- `app/database.py` creates the async SQLAlchemy database engine.
- `app/models/` contains the CRM database models.
- `alembic/versions/0001_initial_crm_models.py` creates the first database schema.
- `app/workers/` sets up Celery with Redis and has a simple health-check task.
- `app/routers/users.py` adds user management routes.
- `app/routers/accounts.py` adds account CRUD, account contacts, and account deals routes.
- `app/routers/contacts.py` adds contact CRUD, tags, filters, and timeline routes.
- `app/routers/leads.py` adds lead CRUD, CSV import, scoring, assignment, duplicates, merge, and conversion routes.
- `app/routers/pipelines.py` adds pipeline and stage management routes.
- `app/routers/deals.py` adds deal CRUD, Kanban, forecast, stale deals, stage movement, won/lost, and collaborators.
- `app/routers/activities.py` adds activity logging, filtering, detail/update/delete, and email drop-box logging.
- `app/routers/tasks.py` adds task CRUD, overdue tasks, complete, and snooze routes.
- `app/routers/campaigns.py` adds campaign CRUD, enrollments, sequence steps, metrics, activation, pause, and unsubscribe routes.
- `app/routers/projects.py` adds project CRUD, from-deal creation, milestones, documents, and a public customer portal route.
- `app/routers/reports.py` adds sales, lead, activity, customer, dashboard, custom builder, CSV export, and PDF export report routes.
- `app/routers/search.py` adds global full-text search across contacts, deals, accounts, and leads.
- `app/routers/webhooks.py` adds signed inbound lead, email, calendar webhooks plus outbound webhook subscriptions.
- `app/middleware/audit.py` adds automatic audit logging for database writes during POST/PATCH/DELETE work.
- `app/middleware/rate_limit.py` adds SlowAPI rate limiting: global 100/min/IP and portal 60/min/IP.
- `app/models/audit.py` stores audit log rows with user, action, entity, old/new values, IP, and timestamp.
- `app/routers/contacts.py` now includes GDPR export and super-admin purge endpoints.
- `Backend/Dockerfile` is now a multi-stage production build with a non-root user, `/health` health check, and Alembic upgrade on container startup.
- `app/workers/` has Celery tasks for campaigns, notifications, reports, projects, lead scoring, retries, and task logs.

## CRM data already modeled

- Users, roles, and user role assignments.
- Leads and lead status/source tracking.
- Accounts, contacts, tags, and custom fields.
- Pipelines, pipeline stages, deals, and deal collaborators.
- Activities and tasks.
- Campaigns, campaign enrollments, and sequence steps.
- Projects, milestones, project documents, and report snapshots.
- Sales quotas and daily report snapshots.
- Celery task logs for background job start/success/error tracking.
- Meilisearch indexes for contacts, deals, accounts, and leads.
- Webhook subscriptions and webhook logs for inbound/outbound integrations.
- Audit logs for create/update/delete database changes.

## What is not built yet

- More frontend UI and end-to-end reporting integrations are still needed.
- Some folders such as `utils` are still placeholders.
- No frontend UI exists yet.
- The test suite passes, but coverage is currently below the requested 80% target.

## What I did in this scan

- Checked the project folder structure.
- Read the backend settings, database, API startup, Docker, worker, migration, and model files.
- Added BetterAuth JWT validation, user management, accounts/contacts, lead management, sales pipeline/deals, activity/task management, marketing campaigns, customer projects, reporting/analytics, the complete Celery background job system, Meilisearch full-text search, signed webhooks/external integrations, audit logging, rate limiting, GDPR contact export/purge, OpenAPI metadata, test fixtures, and Docker production hardening.

## Latest verification

- `python -m compileall app alembic tests scripts` passes.
- `python -m pytest -q` passes.
- `python -m pytest --cov=app --cov-report=term-missing -q` runs, but current coverage is about 62%, not yet 80%.
