# Doxa CRM

Doxa CRM is a full-stack CRM workspace for sales, marketing, and customer-success teams. It includes lead management, contacts, accounts, sales pipeline, activities, tasks, campaigns, projects, reports, settings, and a public project portal.

## Repository Structure

```text
Doxa-CRM/
  Frontend/   Next.js CRM application and BetterAuth server routes
  Backend/    FastAPI API, Celery workers, migrations, and Docker Compose
```

## Stack

- Frontend: Next.js 15, React 19, TypeScript, Tailwind CSS, BetterAuth, TanStack Query, Recharts
- Backend: FastAPI, SQLAlchemy async ORM, Alembic, PostgreSQL or Supabase Postgres
- Background services: Redis, Celery worker, Celery Beat, Meilisearch
- Local orchestration: Docker Compose from `Backend/docker-compose.yml`

## Local URLs

When running the Docker Compose stack from `Backend/`:

```text
Frontend:       http://localhost:3000
Backend API:    http://localhost:8001
Swagger docs:   http://localhost:8001/docs
ReDoc:          http://localhost:8001/redoc
Health check:   http://localhost:8001/health
Meilisearch:    http://localhost:7700
```

## Setup

Create environment files:

```powershell
copy Backend\.env.example Backend\.env
copy Frontend\.env.local.example Frontend\.env
```

Fill in both files before starting the app:

- `Backend/.env` uses `postgresql+asyncpg://...` for `DATABASE_URL`
- `Frontend/.env` uses a normal `postgresql://...` URL for BetterAuth
- `Backend SECRET_KEY` and `Frontend BETTER_AUTH_SECRET` must match
- Keep `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, and `BETTER_AUTH_DB_POOL_MAX` small for Supabase session-pool development

This repo does not start a Postgres container. Use Supabase Postgres or another reachable PostgreSQL database.

## Run With Docker

From the backend folder:

```powershell
cd Backend
docker compose up -d --build
```

Check services:

```powershell
docker compose ps
```

View logs:

```powershell
docker compose logs -f api
docker compose logs -f frontend
```

Stop services:

```powershell
docker compose down
```

## Run Locally Without Docker

Backend:

```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

Frontend:

```powershell
cd Frontend
npm install --legacy-peer-deps
npm run dev
```

Run Redis and Meilisearch separately if you are not using Docker.

## Seed Demo Data

Apply migrations first:

```powershell
cd Backend
python -m alembic upgrade head
python scripts\seed_default_pipeline.py
python scripts\seed_demo_data.py
```

Seed BetterAuth users:

```powershell
cd ..\Frontend
node scripts\seed-auth-users.mjs
```

Demo password:

```text
DoxaDemo123!
```

Demo users:

```text
admin@doxa.local              super_admin
sales.manager@doxa.local      sales_manager
alex.rep@doxa.local           sales_rep
maya.rep@doxa.local           sales_rep
marketing.manager@doxa.local  marketing_manager
marketing.rep@doxa.local      marketing_rep
success@doxa.local            customer_success
readonly@doxa.local           read_only
```

## Main App Areas

- `/dashboard`
- `/leads`
- `/contacts`
- `/accounts`
- `/deals`
- `/deals`
- `/activities`
- `/tasks`
- `/campaigns`
- `/projects`
- `/reports`
- `/search`
- `/settings`
- `/portal/{portal_token}`

Backend API routes are mounted under `/api/v1`.

## Product Design Answers

This section answers the main CRM design questions from the project brief and reflects the current implementation.

### Lead Management

- Lead records store name, email, phone, company, source, score, status, assignee, campaign link, UTM source, UTM campaign, UTM medium, conversion date, and active state.
- Duplicate leads are detected by exact email or phone matches, plus fuzzy matching on name and company. The lead page includes duplicate review and merge flows.
- Converting a lead means marking the lead as converted, creating or linking a contact, optionally creating or linking an account, and optionally creating a deal. The created contact or account stores the conversion origin internally, but the UI hides that technical ID from users.

### Contact And Account Management

- A contact can belong to one account through `account_id`; an account can have many contacts. Contacts may also exist without an account until the team links one later.
- Communication history is tracked through activities, tasks, deal timelines, and contact timeline views. Activities and tasks can be linked to leads, contacts, accounts, or deals.
- Flexible data is handled with tags and `custom_fields` on contacts and accounts. Custom field definitions support text, number, date, boolean, select, and JSON values.

### Sales Pipeline

- The default pipeline is `New Business` with stages: Prospecting, Qualification, Proposal Sent, Negotiation, Closed Won, and Closed Lost.
- The pipeline is represented visually as a Kanban board. Users can click a card to open the deal detail page and drag a card to move the deal to another stage.
- Forecast is calculated from open deals using weighted value: `deal value * probability / 100`. Stage probability is copied to the deal when it moves stages.

### Activities And Tasks

- Tasks can link to leads, contacts, accounts, and deals. They store title, description, due date, priority, status, owner, and related record IDs.
- Overdue work is surfaced through the dashboard overdue task widget, task filters, reports, and scheduled Celery overdue checks.
- Outbound emails can be logged as activity records linked to the contact, lead, account, or deal. Real sent, opened, clicked, replied, and converted email metrics require email delivery/tracking integration data.

### Marketing Campaigns

- Campaigns store name, type, status, start/end dates, target segment, budget, owner, sequence steps, enrollments, and metrics.
- Multi-step sequences are modeled as ordered steps with channel, subject, body, delay days, and optional variant. Steps can be reordered.
- Leads connect back to campaigns through `campaign_id` and UTM fields. Reports can group lead volume and conversion by campaign/source.

### Customer Projects

- Project records store name, account, optional source deal, status, start/end dates, health, owner, portal token, milestones, and documents.
- A project can be created from a closed-won deal and keeps the `deal_id` link back to the sale that created it.
- The customer portal uses a project `portal_token` and shows the customer-facing project state, milestones, and documents without exposing the full CRM.

### Reporting And Analytics

- Dashboard and reports aggregate data through backend report services, SQL queries, and report endpoints instead of computing everything in the browser.
- Reports support CSV and PDF exports, and custom reports support spreadsheet export for selected data.
- The custom report builder lets users choose entity, fields, filters, date range, grouping, and sorting without writing SQL.

### Roles And Permissions

- `super_admin` can manage everything, including users.
- Sales managers and sales reps can work sales records such as leads, contacts, accounts, deals, activities, and tasks.
- Marketing managers and marketing reps can manage leads, contacts, campaigns, activities, and tasks.
- Customer success can manage contacts, accounts, projects, activities, and tasks.
- Read-only users can view allowed CRM areas without write actions.

## Checks

Frontend:

```powershell
cd Frontend
npm run typecheck
npm run build
```

Backend:

```powershell
cd Backend
python -m pytest -q
python -m compileall app alembic tests scripts
```

## Documentation

- Frontend details: `Frontend/readme.md`
- Backend details: `Backend/README.md`
- Load testing notes: `Backend/load_tests/README.md`

## Troubleshooting

If login fails with database pool errors, make sure old local servers or Docker containers are not holding extra database sessions. For Supabase session-pool development, keep these values low:

```env
DB_POOL_SIZE=1
DB_MAX_OVERFLOW=1
BETTER_AUTH_DB_POOL_MAX=2
```

If the frontend can load but backend requests fail, confirm:

```env
NEXT_PUBLIC_API_URL=http://localhost:8001
API_INTERNAL_URL=http://localhost:8001
```

If Docker server-side calls are used, `API_INTERNAL_URL` can be:

```env
API_INTERNAL_URL=http://api:8000
```

Never commit `.env` files or real secrets.
