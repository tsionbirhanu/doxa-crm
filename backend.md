# Doxa CRM Backend Guide

This document explains the backend one piece at a time. It is written from the current backend code in `Backend/` and is meant to help you understand what every important file is for, how the parts connect, and why tools like Alembic, Redis, Celery, Meilisearch, and BetterAuth are used.

## 1. Big Picture

The backend is a FastAPI application for a CRM system. It exposes REST APIs under `/api/v1`, stores CRM data in PostgreSQL, validates requests with Pydantic, maps tables with SQLAlchemy async ORM, runs database migrations with Alembic, runs background jobs with Celery and Redis, supports search through Meilisearch, and integrates with the Next.js frontend authentication through BetterAuth JWT tokens.

The main runtime flow is:

```text
Frontend request
  -> FastAPI router
  -> dependency authentication and role checks
  -> Pydantic request schema validation
  -> service function
  -> SQLAlchemy model and database session
  -> optional search/webhook/background-task side effects
  -> Pydantic response schema
  -> JSON response
```

The backend keeps files separated by responsibility:

```text
Backend/
  app/main.py          FastAPI app setup
  app/config.py        Environment settings
  app/database.py      Async database engine and sessions
  app/models/          SQLAlchemy database models
  app/schemas/         Pydantic request and response models
  app/routers/         API endpoints
  app/services/        Business logic
  app/workers/         Celery background tasks
  app/middleware/      Audit logging and rate limiting
  app/utils/           Shared helper utilities
  alembic/             Database migration system
  scripts/             Seed data scripts
  tests/               Pytest test suite
  load_tests/          Async HTTP load test runner
```

## 2. Backend Technology Stack

- FastAPI: web framework for defining routes, validation, OpenAPI docs, and dependency injection.
- Pydantic: request and response validation.
- SQLAlchemy async ORM: Python models mapped to PostgreSQL tables.
- PostgreSQL or Supabase Postgres: main relational database.
- Alembic: database migration tool that versions schema changes.
- Redis: Celery broker/result backend and API Redis health dependency.
- Celery: background jobs and scheduled jobs.
- Meilisearch: search engine for contacts, accounts, deals, and leads.
- python-jose: JWT decoding and verification for BetterAuth tokens.
- SlowAPI: rate limiting.
- httpx: outgoing HTTP calls for search, webhooks, email API, and tests.
- boto3: R2/S3-compatible document storage.
- reportlab: richer PDF report export, with a fallback if unavailable.
- Pytest and pytest-asyncio: automated tests.
- Docker Compose: local multi-service runtime.

## 3. Important Runtime Services

When running with Docker Compose, these services are defined:

- `frontend`: Next.js frontend from `Frontend/`.
- `api`: FastAPI backend served by Uvicorn.
- `celery_worker`: Celery worker process for background jobs.
- `celery_beat`: Celery Beat scheduler process.
- `redis`: Redis used by Celery.
- `meilisearch`: local search engine.

PostgreSQL is not started by this Docker Compose file. The backend expects a `DATABASE_URL`, usually Supabase/Postgres.

## 4. Environment Settings

Settings are loaded from environment variables and `Backend/.env` by `app/config.py`.

Required settings:

```env
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://redis:6379/0
SECRET_KEY=change-me-to-a-random-32-byte-or-longer-secret-key
ENVIRONMENT=development
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
DB_POOL_SIZE=1
DB_MAX_OVERFLOW=1
WEBHOOK_SECRET=change-me-webhook-secret-at-least-32-chars
```

Optional settings:

```env
MEILISEARCH_URL=http://meilisearch:7700
MEILISEARCH_API_KEY=local-development-master-key
RESEND_API_KEY=
RESEND_FROM_EMAIL=crm@example.com
R2_ENDPOINT_URL=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
R2_REGION_NAME=auto
```

Important details:

- `SECRET_KEY` must be at least 32 characters.
- `SECRET_KEY` must match the frontend BetterAuth secret because backend JWT validation uses the same shared secret.
- In development, CORS allows `http://localhost:3000` and `http://127.0.0.1:3000`.
- In non-development environments, docs and ReDoc are disabled by default through `docs_url=None` and `redoc_url=None`.
- Supabase pooler URLs are adjusted in `app/database.py` to handle SSL and prepared statement cache settings.

## 5. Authentication and Authorization

The frontend authenticates users with BetterAuth. The backend does not log users in directly. Instead, the frontend sends:

```http
Authorization: Bearer <jwt>
```

The backend:

1. Decodes the JWT in `app/auth/jwt.py`.
2. Uses `SECRET_KEY` and HS256.
3. Reads user identity from token fields like `sub`, `user_id`, `userId`, `id`, or `email`.
4. Finds the matching backend `User` record in the database.
5. Rejects inactive or missing users.
6. Applies role restrictions through `require_role`.

Roles are defined in `UserRoleName`:

- `super_admin`
- `sales_manager`
- `sales_rep`
- `marketing_manager`
- `marketing_rep`
- `customer_success`
- `read_only`

Role groups in `app/auth/permissions.py` decide who can write to which modules.

## 6. Why Alembic Is Used

Alembic is used because the database schema changes over time. SQLAlchemy models describe the desired Python-side structure, but PostgreSQL still needs real SQL changes such as `CREATE TABLE`, `ADD COLUMN`, `CREATE INDEX`, and enum changes.

Without Alembic, every developer or deployment would need to manually update the database, which is risky. Alembic gives the project:

- Versioned database history.
- Repeatable schema upgrades.
- Downgrade scripts when possible.
- Team-safe migrations committed with the code.
- Autogeneration from SQLAlchemy models.
- A clear record of when tables, columns, indexes, and constraints were added.

Typical commands:

```powershell
cd Backend
python -m alembic current
python -m alembic upgrade head
python -m alembic revision --autogenerate -m "describe change"
```

In Docker, `docker-entrypoint.sh` runs `alembic upgrade head` when `RUN_MIGRATIONS=true`.

## 7. Request Lifecycle

Example: creating a contact.

1. Request hits `POST /api/v1/contacts/`.
2. `contacts.py` router requires one of `CONTACT_WRITE_ROLES`.
3. FastAPI validates JSON against `ContactCreate`.
4. Router calls `contacts_service.create_contact`.
5. Service applies ownership rules, creates `Contact`, commits to DB.
6. Service builds a `ContactResponse`.
7. Service syncs contact to Meilisearch.
8. Audit middleware/listeners create an `audit_logs` row for the write.
9. API returns JSON to the frontend.

This same pattern appears across most modules.

## 8. File-by-File Reference

The sections below explain each backend file or file group.

## 9. Backend Root Files

### `Backend/README.md`

Human-facing backend instructions. It explains the stack, local URLs, environment variables, Docker commands, local run commands, migrations, seed data, APIs, background jobs, search, tests, troubleshooting, and production notes.

### `Backend/requirements.txt`

Pinned Python dependencies. Important packages include FastAPI, SQLAlchemy async, asyncpg, Alembic, Pydantic settings, python-jose, boto3, SlowAPI, ReportLab, Celery, Redis, httpx, pytest, pytest-asyncio, and pytest-cov.

### `Backend/.env.example`

Example environment file. It documents required database, Redis, Supabase, Meilisearch, secret, and webhook settings.

### `Backend/.gitignore`

Git ignore rules for backend-only local files. It excludes secrets such as `.env`, Python caches, pytest/coverage output, virtual environments, Celery Beat schedule files, SQLite/db artifacts, and editor/OS noise. It explicitly allows `.env.example` to stay committed.

### `Backend/alembic.ini`

Alembic configuration file. It points Alembic to the `alembic/` folder and sets logging. The placeholder `sqlalchemy.url` is replaced at runtime by `alembic/env.py`, which reads the real `DATABASE_URL`.

### `Backend/Dockerfile`

Two-stage Python Docker build:

- Builder stage installs dependencies into `/install`.
- Runtime stage copies installed packages and source code.
- Uses non-root `appuser`.
- Exposes port `8000`.
- Uses `docker-entrypoint.sh`.

### `Backend/docker-compose.yml`

Defines local services:

- frontend
- api
- celery worker
- celery beat
- redis
- meilisearch

The API maps host port `8001` to container port `8000`.

### `Backend/docker-entrypoint.sh`

Shell entrypoint. If `RUN_MIGRATIONS=true`, it runs:

```sh
alembic upgrade head
```

Then it starts the container command.

### `Backend/pytest.ini`

Pytest config:

- Enables async test mode.
- Sets test folder to `tests`.
- Finds files named `test_*.py`.

### Generated or local-only files

These are not core source files:

- `Backend/.env`: local secrets/settings. Do not commit.
- `Backend/.coverage`: coverage output.
- `Backend/.pytest_cache/`: pytest cache.
- `__pycache__/`: Python bytecode cache folders.

## 10. App Core Files

### `Backend/app/__init__.py`

Marks `app` as a Python package. It has no current runtime logic.

### `Backend/app/main.py`

FastAPI application entrypoint.

Main responsibilities:

- Reads settings.
- Installs SQLAlchemy audit listeners.
- Creates the FastAPI app.
- Configures API title, description, version, docs, ReDoc, and OpenAPI tags.
- Opens Redis and checks database connection during app lifespan.
- Closes Redis and database connections on shutdown.
- Adds CORS middleware.
- Adds audit context middleware.
- Applies rate limiting.
- Installs consistent exception handlers.
- Includes all `/api/v1` routers.
- Defines `/health`.

Important functions:

- `lifespan`: startup/shutdown resource management.
- `create_app`: app factory, useful for tests.
- `_error_code`: maps status codes to stable error codes.
- `app = create_app()`: Uvicorn imports this.

### `Backend/app/config.py`

Centralized settings.

Main class:

- `Settings`

Important behavior:

- Uses Pydantic `BaseSettings`.
- Loads `.env`.
- Requires `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `SUPABASE_URL`, and `SUPABASE_KEY`.
- Validates `SECRET_KEY` length.
- Provides `is_development`.
- Provides `cors_origins`.
- Caches settings with `get_settings()`.

Why cached settings matter:

- Environment variables are parsed once.
- Every module gets the same settings object.
- Tests can set environment variables before importing app modules.

### `Backend/app/database.py`

Async SQLAlchemy setup.

Important objects:

- `engine`: async SQLAlchemy engine.
- `AsyncSessionLocal`: async session factory.

Important functions:

- `build_async_database_url`: normalizes PostgreSQL/Supabase database URLs.
- `get_db_session`: yields an `AsyncSession`.
- `check_database_connection`: runs `SELECT 1`.
- `close_database_connections`: disposes the engine.

Important Supabase behavior:

- Converts `postgresql://` to `postgresql+asyncpg://`.
- Converts `sslmode` query param to asyncpg `ssl`.
- Adds SSL for Supabase hosts.
- Disables prepared statement cache for Supabase transaction pooler on port `6543`.

### `Backend/app/dependencies.py`

FastAPI dependency helpers.

Important functions:

- `get_db`: wraps `get_db_session`.
- `get_current_user`: validates bearer JWT and returns active `User`.
- `require_role`: factory for role-based dependencies.
- `_get_user_from_token_payload`: finds user by UUID-like subject or email.

How role checks work:

```python
current_user: Annotated[User, Depends(require_role(*CONTACT_WRITE_ROLES))]
```

If the current user's role is not in the allowed role group, the dependency raises `403`.

## 11. Auth Files

### `Backend/app/auth/__init__.py`

Package marker for auth helpers.

### `Backend/app/auth/jwt.py`

JWT decoding.

Important behavior:

- Uses HS256.
- Uses `SECRET_KEY`.
- Ignores audience verification with `verify_aud=False`.
- Raises `401` for expired or invalid tokens.

Important function:

- `decode_access_token(token)`

### `Backend/app/auth/permissions.py`

Role constants and role groups.

Examples:

- `ADMIN_ROLES`: super admin only.
- `SETTINGS_ROLES`: super admin and sales manager.
- `SALES_WRITE_ROLES`: super admin, sales manager, sales rep.
- `CAMPAIGN_WRITE_ROLES`: marketing roles and super admin.
- `PROJECT_EDITOR_ROLES`: super admin, sales manager, customer success.

Important functions:

- `role_value(user)`: returns a normalized string role.
- `is_manager(user)`: true for super admin or sales manager.

## 12. Middleware Files

### `Backend/app/middleware/audit.py`

Automatic audit logging.

Main idea:

- For write requests (`POST`, `PATCH`, `DELETE`), the middleware stores user ID, IP address, method, and path in a context variable.
- SQLAlchemy session listeners inspect new, dirty, and deleted ORM objects before flush.
- The listener creates `AuditLog` rows for changes.

Important classes/functions:

- `AuditContext`
- `AuditContextMiddleware`
- `install_audit_listeners`
- `_create_audit_entries`

Skipped table:

- `audit_logs`, to avoid auditing the audit log itself.

The audit row records:

- user
- action such as `POST /api/v1/contacts/`
- entity type/table
- entity id
- old value
- new value
- IP address

### `Backend/app/middleware/rate_limit.py`

Rate limiting wrapper around SlowAPI.

Limits:

- Global: `100/minute`
- Auth-related constant: `10/minute`
- Public portal: `60/minute`

If SlowAPI is unavailable, the file falls back to a no-op limiter so imports still work.

Important functions:

- `apply_rate_limiting(app)`
- `_rate_limit_handler`

## 13. Model Files

Models are SQLAlchemy ORM classes. They define database tables, columns, relationships, enums, and constraints.

### `Backend/app/models/base.py`

Shared model base.

Important code:

- `Base`: SQLAlchemy declarative base.
- `NAMING_CONVENTION`: stable names for constraints and indexes. This helps Alembic generate predictable migrations.
- `UUIDPrimaryKeyMixin`: UUID primary key with `gen_random_uuid()` database default.
- `TimestampMixin`: `created_at` and `updated_at`.

### `Backend/app/models/__init__.py`

Imports and exports all model classes and enums. Alembic imports `Base` from here so it can see all registered tables through `Base.metadata`.

### `Backend/app/models/users.py`

User and RBAC models.

Tables/classes:

- `UserRoleName`: role enum.
- `User`: backend CRM user profile.
- `Role`: role catalog.
- `UserRole`: join table for user-role assignments.

Important point:

- The `users.role` enum is used directly by permission checks.
- `UserRole` exists for normalized role assignment history/relationships.

### `Backend/app/models/contacts.py`

Accounts, contacts, tags, and custom fields.

Tables/classes:

- `Account`: company/account record.
- `Contact`: person linked optionally to an account.
- `ContactTag`: reusable tag catalog.
- `CustomField`: configurable field definition.

Enums:

- `AccountTier`
- `CustomFieldEntityType`
- `CustomFieldType`

Important columns:

- `Account.custom_fields`: JSONB for flexible account metadata.
- `Contact.tags`: PostgreSQL array.
- `Contact.custom_fields`: JSONB for flexible contact metadata.
- `is_active`: soft-delete flag.

### `Backend/app/models/leads.py`

Lead management.

Tables/classes:

- `LeadSource`: website, referral, social, cold outreach, event, campaign.
- `LeadStatus`: new, contacted, qualified, disqualified, converted.
- `Lead`: prospect record before conversion.

Important columns:

- `score`: rule-based lead score.
- `assigned_to`: user responsible for the lead.
- `campaign_id`: optional marketing campaign link.
- `utm_source`, `utm_campaign`, `utm_medium`: campaign attribution.
- `converted_at`: conversion timestamp.
- `is_active`: soft-delete flag.

### `Backend/app/models/deals.py`

Sales pipeline and deal lifecycle.

Tables/classes:

- `Pipeline`: sales pipeline.
- `PipelineStage`: ordered stages with probabilities.
- `Deal`: opportunity.
- `DealCollaborator`: additional users on a deal.
- `DealStageHistory`: audit/history of stage moves.

Enum:

- `DealStatus`: open, won, lost.

Important behavior supported by the model:

- Deals belong to pipeline, stage, contact, account, and owner.
- Stage history records from/to stage and user.
- `type` supports values like `new_business` or `renewal`.
- `lost_reason` and `closed_at` support win/loss workflow.

### `Backend/app/models/activities.py`

Activity and task tracking.

Tables/classes:

- `Activity`: calls, emails, meetings, notes.
- `Task`: follow-up work item.

Enums:

- `ActivityType`: call, email, meeting, note, task.
- `TaskStatus`: pending, in progress, completed, cancelled.
- `TaskPriority`: low, medium, high, urgent.

Important point:

- Activity logs and tasks can link to leads, contacts, deals, and accounts.

### `Backend/app/models/campaigns.py`

Marketing campaigns.

Tables/classes:

- `Campaign`: campaign metadata.
- `CampaignEnrollment`: contact enrolled in a campaign.
- `CampaignSequenceStep`: ordered step in campaign sequence.
- `CampaignMetric`: sent/opened/clicked/replied/converted events.

Enums:

- `CampaignType`
- `CampaignStatus`
- `CampaignEnrollmentStatus`
- `CampaignSequenceChannel`
- `CampaignMetricEventType`

Important constraints:

- One enrollment per campaign/contact.
- One step index per campaign.

### `Backend/app/models/projects.py`

Customer success projects and portal.

Tables/classes:

- `Project`: customer project.
- `Milestone`: project milestone.
- `ProjectDocument`: uploaded project document metadata.

Enum:

- `ProjectHealth`: green, yellow, red.

Important fields:

- `portal_token`: public token for customer portal route.
- `health`: calculated from milestones.
- `storage_key`: R2/S3 storage object key.

### `Backend/app/models/reports.py`

Reporting support tables.

Tables/classes:

- `ReportSnapshot`: cached daily report data.
- `SalesQuota`: quota by user and date period.

Important constraints:

- Unique report snapshot per `report_type` and `date`.
- Unique quota per user and period.

### `Backend/app/models/task_logs.py`

Celery task logs.

Table/class:

- `TaskLog`

Tracks:

- Celery task id.
- task name.
- status.
- start/finish time.
- error.
- JSON details.

### `Backend/app/models/webhooks.py`

Webhook subscriptions and delivery logs.

Tables/classes:

- `WebhookSubscription`: outbound webhook target URL, events, secret, active flag.
- `WebhookLog`: inbound/outbound event log.

### `Backend/app/models/audit.py`

Audit log table.

Table/class:

- `AuditLog`

Stores write operation changes created by audit middleware/listeners.

## 14. Schema Files

Schemas are Pydantic models. They validate incoming API data and shape outgoing API data.

### `Backend/app/schemas/__init__.py`

Package marker for schema files.

### `Backend/app/schemas/users.py`

Schemas:

- `UserCreate`
- `UserUpdate`
- `UserResponse`

Special behavior:

- `NameAliasMixin` accepts `name` as an alias for `full_name`.

### `Backend/app/schemas/accounts.py`

Schemas:

- `AccountCreate`
- `AccountUpdate`
- `AccountResponse`
- `AccountDealResponse`

Important helper:

- `validate_custom_fields`: only allows scalar custom field values.

Response includes:

- owner name
- linked contact count
- total deal value

### `Backend/app/schemas/contacts.py`

Schemas:

- `ContactCreate`
- `ContactUpdate`
- `ContactTagsUpdate`
- `ContactResponse`
- timeline helper models
- `ContactTimelineItem`

Special behavior:

- Normalizes tags by trimming, removing empties, and deduplicating.
- Reuses custom-field validation from accounts.

### `Backend/app/schemas/leads.py`

Schemas:

- `LeadCreate`
- `LeadUpdate`
- `LeadAssignRequest`
- `LeadScoreResponse`
- `LeadConvertRequest`
- `LeadConvertResponse`
- `LeadMergeRequest`
- `LeadImportSummary`
- `DuplicateLeadPair`
- `LeadResponse`

Important workflows:

- assigning leads
- scoring leads
- importing CSV leads
- detecting duplicates
- merging leads
- converting lead to contact/account/deal

### `Backend/app/schemas/deals.py`

Schemas:

- `DealCreate`
- `DealUpdate`
- `DealMoveStageRequest`
- `DealLostRequest`
- `DealCollaboratorCreate`
- `DealResponse`
- `DealDetailResponse`
- `DealForecastResponse`
- `DealKanbanResponse`

Supports:

- Kanban board response
- forecast by stage
- stage history
- collaborators
- related activities/tasks

### `Backend/app/schemas/activities.py`

Schemas:

- `ActivityCreate`
- `ActivityUpdate`
- `ActivityResponse`
- `EmailLogCreate`
- `TaskCreate`
- `TaskUpdate`
- `TaskSnoozeRequest`
- `TaskResponse`

Important validation:

- `LinkedEntityMixin` requires at least one linked entity.
- Activity creation rejects `ActivityType.task` because tasks have their own `/tasks` API.

### `Backend/app/schemas/campaigns.py`

Schemas:

- `CampaignCreate`
- `CampaignUpdate`
- `CampaignResponse`
- `CampaignEnrollmentResponse`
- `CampaignEnrollRequest`
- `CampaignStepCreate`
- `CampaignStepUpdate`
- `CampaignStepResponse`
- `CampaignStepsReorderRequest`
- `CampaignMetricsResponse`
- `CampaignMetricResponse`

### `Backend/app/schemas/projects.py`

Schemas:

- `ProjectCreate`
- `ProjectUpdate`
- `MilestoneCreate`
- `MilestoneUpdate`
- `MilestoneResponse`
- `ProjectDocumentResponse`
- `ProjectResponse`
- `ProjectPortalResponse`

Portal response intentionally exposes fewer fields than authenticated project response.

### `Backend/app/schemas/pipelines.py`

Schemas:

- `PipelineCreate`
- `PipelineUpdate`
- `PipelineResponse`
- `PipelineStageCreate`
- `PipelineStageUpdate`
- `PipelineStageResponse`

### `Backend/app/schemas/reports.py`

Schemas for report rows and report requests:

- sales pipeline summary
- deal velocity
- win/loss
- forecast
- quota
- lead volume
- lead funnel
- lead response time
- activity volume
- overdue tasks
- sequence performance
- customer health
- renewal pipeline
- dashboard
- custom reports

Custom reports use whitelisted fields only, which prevents arbitrary SQL column access.

### `Backend/app/schemas/search.py`

Schemas:

- `SearchResult`
- `GlobalSearchResponse`

### `Backend/app/schemas/webhooks.py`

Schemas:

- `LeadFormPayload`
- `EmailInboundPayload`
- `CalendarEventPayload`
- `WebhookAck`
- `WebhookSubscriptionCreate`
- `WebhookSubscriptionResponse`

Also defines allowed outbound event types:

- `lead.created`
- `lead.converted`
- `deal.won`
- `deal.lost`
- `deal.stage_changed`
- `project.health_changed`

## 15. Router Files

Routers define HTTP endpoints. They should stay thin: validate inputs, check auth/roles, and call services.

### `Backend/app/routers/__init__.py`

Creates `api_router` and includes all routers:

- activities
- accounts
- campaigns
- contacts
- deals
- leads
- pipelines
- projects
- portal
- reports
- search
- tasks
- users
- webhooks

`app/main.py` mounts this router under `/api/v1`.

### `Backend/app/routers/users.py`

Endpoints:

- `GET /users/`: list users. Settings roles only.
- `POST /users/`: create user. Super admin only.
- `GET /users/me`: current user.
- `GET /users/{user_id}`: get user.
- `PATCH /users/{user_id}`: update user. Super admin only.
- `DELETE /users/{user_id}`: soft-delete user. Super admin only.

### `Backend/app/routers/accounts.py`

Endpoints:

- `GET /accounts/`
- `POST /accounts/`
- `GET /accounts/{account_id}`
- `PATCH /accounts/{account_id}`
- `DELETE /accounts/{account_id}`
- `GET /accounts/{account_id}/contacts`
- `GET /accounts/{account_id}/deals`

Supports pagination, tier filtering, owner filtering, and search.

### `Backend/app/routers/contacts.py`

Endpoints:

- `GET /contacts/`
- `POST /contacts/`
- `GET /contacts/{contact_id}`
- `PATCH /contacts/{contact_id}`
- `DELETE /contacts/{contact_id}`
- `GET /contacts/{contact_id}/export`
- `DELETE /contacts/{contact_id}/purge`
- `GET /contacts/{contact_id}/timeline`
- `POST /contacts/{contact_id}/tags`
- `DELETE /contacts/{contact_id}/tags/{tag}`

Special:

- Purge requires `super_admin` and a confirmation token.
- Timeline combines activities, tasks, notes, and deals.

### `Backend/app/routers/leads.py`

Endpoints:

- `GET /leads/`
- `POST /leads/`
- `POST /leads/import`
- `GET /leads/duplicates`
- `POST /leads/merge`
- `GET /leads/{lead_id}`
- `PATCH /leads/{lead_id}`
- `DELETE /leads/{lead_id}`
- `POST /leads/{lead_id}/convert`
- `POST /leads/{lead_id}/assign`
- `POST /leads/{lead_id}/score`

Special:

- Sales reps can only list their assigned leads.
- CSV import reads an uploaded file.

### `Backend/app/routers/pipelines.py`

Endpoints:

- `GET /pipelines/`
- `POST /pipelines/`
- `GET /pipelines/{pipeline_id}`
- `PATCH /pipelines/{pipeline_id}`
- `DELETE /pipelines/{pipeline_id}`
- `GET /pipelines/{pipeline_id}/stages`
- `POST /pipelines/{pipeline_id}/stages`
- `PATCH /pipelines/{pipeline_id}/stages/{stage_id}`
- `DELETE /pipelines/{pipeline_id}/stages/{stage_id}`

Pipeline admin roles are super admin and sales manager.

### `Backend/app/routers/deals.py`

Endpoints:

- `GET /deals/`
- `GET /deals/kanban`
- `GET /deals/forecast`
- `GET /deals/stale`
- `POST /deals/`
- `GET /deals/{deal_id}`
- `PATCH /deals/{deal_id}`
- `DELETE /deals/{deal_id}`
- `POST /deals/{deal_id}/stage`
- `POST /deals/{deal_id}/won`
- `POST /deals/{deal_id}/lost`
- `POST /deals/{deal_id}/collaborators`
- `DELETE /deals/{deal_id}/collaborators/{user_id}`

Special:

- Sales reps only see their own deals.
- Stage movement can update status and create stage history.

### `Backend/app/routers/activities.py`

Endpoints:

- `GET /activities/`
- `POST /activities/`
- `POST /activities/email-log`
- `GET /activities/export/csv`
- `GET /activities/{activity_id}`
- `PATCH /activities/{activity_id}`
- `DELETE /activities/{activity_id}`

Special:

- Non-manager users are forced to filter activities by their own owner ID.
- CSV export returns a file response.

### `Backend/app/routers/tasks.py`

Endpoints:

- `GET /tasks/`
- `GET /tasks/overdue`
- `POST /tasks/`
- `GET /tasks/{task_id}`
- `PATCH /tasks/{task_id}`
- `DELETE /tasks/{task_id}`
- `POST /tasks/{task_id}/complete`
- `POST /tasks/{task_id}/snooze`

Special:

- Non-manager users only see their own tasks.

### `Backend/app/routers/campaigns.py`

Endpoints:

- `GET /campaigns/`
- `POST /campaigns/`
- `GET /campaigns/{campaign_id}`
- `PATCH /campaigns/{campaign_id}`
- `DELETE /campaigns/{campaign_id}`
- `POST /campaigns/{campaign_id}/activate`
- `POST /campaigns/{campaign_id}/pause`
- `GET /campaigns/{campaign_id}/enrollments`
- `POST /campaigns/{campaign_id}/enroll`
- `DELETE /campaigns/{campaign_id}/enrollments/{contact_id}`
- `GET /campaigns/{campaign_id}/metrics`
- `GET /campaigns/{campaign_id}/steps`
- `POST /campaigns/{campaign_id}/steps`
- `POST /campaigns/{campaign_id}/steps/reorder`
- `PATCH /campaigns/{campaign_id}/steps/{step_id}`
- `DELETE /campaigns/{campaign_id}/steps/{step_id}`

Special:

- Activating a campaign requires at least one sequence step and one active enrollment.
- Active enrollment can queue Celery campaign-step processing.

### `Backend/app/routers/projects.py`

Authenticated project endpoints:

- `GET /projects/`
- `POST /projects/`
- `POST /projects/from-deal/{deal_id}`
- `GET /projects/{project_id}`
- `PATCH /projects/{project_id}`
- `DELETE /projects/{project_id}`
- `GET /projects/{project_id}/milestones`
- `POST /projects/{project_id}/milestones`
- `PATCH /projects/{project_id}/milestones/{milestone_id}`
- `POST /projects/{project_id}/milestones/{milestone_id}/complete`
- `DELETE /projects/{project_id}/milestones/{milestone_id}`
- `POST /projects/{project_id}/documents`
- `GET /projects/{project_id}/documents`
- `DELETE /projects/{project_id}/documents/{document_id}`

Public portal endpoint:

- `GET /portal/{portal_token}`

Special:

- Public portal route has rate limiting and does not require auth.
- Document upload uses `UploadFile`.

### `Backend/app/routers/reports.py`

Report endpoints:

- `GET /reports/pipeline-summary`
- `GET /reports/deal-velocity`
- `GET /reports/win-loss`
- `GET /reports/forecast`
- `GET /reports/quota`
- `GET /reports/lead-volume`
- `GET /reports/lead-funnel`
- `GET /reports/lead-response-time`
- `GET /reports/activity-volume`
- `GET /reports/overdue-tasks`
- `GET /reports/sequence-performance`
- `GET /reports/customer-health`
- `GET /reports/renewal-pipeline`
- `POST /reports/custom`
- `POST /reports/custom/export/xlsx`
- `GET /reports/dashboard`
- `GET /reports/export/csv`
- `GET /reports/export/xlsx`
- `GET /reports/export/pdf`

Special:

- Builds CSV and XLSX directly.
- Uses ReportLab for PDF when installed.
- Has a basic fallback PDF builder.

### `Backend/app/routers/search.py`

Endpoint:

- `GET /search/global?q=...`

Calls global Meilisearch search across contacts, deals, accounts, and leads.

### `Backend/app/routers/webhooks.py`

Inbound endpoints:

- `POST /webhooks/lead-form`
- `POST /webhooks/email-inbound`
- `POST /webhooks/calendar-event`

Subscription endpoints:

- `GET /webhooks/subscriptions`
- `POST /webhooks/subscriptions`
- `DELETE /webhooks/subscriptions/{subscription_id}`

Special:

- Inbound webhooks must be JSON.
- Inbound webhooks must have valid HMAC signature.
- Accepted inbound payloads are logged and sent to Celery workers.
- Subscription management is super-admin only.

## 16. Service Files

Services contain business logic and database operations.

### `Backend/app/services/__init__.py`

Package marker for service modules.

### `Backend/app/services/users.py`

User CRUD service.

Functions:

- list users
- get user
- create user
- update user
- soft-delete user by setting `is_active=False`

Handles duplicate email conflicts.

### `Backend/app/services/accounts.py`

Account logic.

Responsibilities:

- Pagination.
- Account visibility filter.
- Sales-rep ownership restrictions.
- Account create/update/delete.
- Enriched account responses with owner name, linked contact count, and total deal value.
- List contacts for account.
- List deals for account.
- Sync account search documents.

Sales reps can see owned accounts and accounts with contacts they own.

### `Backend/app/services/contacts.py`

Contact logic.

Responsibilities:

- Contact visibility filter.
- Pagination, filtering, search, and sorting.
- Contact create/update/soft-delete.
- Search sync.
- GDPR-style export.
- Hard purge with confirmation token.
- Timeline aggregation.
- Tag add/remove.

Important:

- `purge_contact_data` deletes related activities, tasks, campaign enrollments, deals, and the contact.
- The confirmation token must be an HMAC over the contact ID using `SECRET_KEY`.

### `Backend/app/services/leads.py`

Lead lifecycle logic.

Responsibilities:

- Lead CRUD.
- Status transition validation.
- Lead assignment.
- Lead scoring.
- Duplicate detection.
- CSV import.
- Lead merge.
- Lead conversion into contact, optional account, and optional deal.
- Search sync.

Important conversion behavior:

- Converted contact stores `converted_from_lead_id` in custom fields.
- Existing conversion is detected to prevent duplicate conversions.
- Creating a deal during conversion requires `pipeline_id`, `deal_title`, and `deal_value`.

### `Backend/app/services/duplicate_detection.py`

Duplicate lead detection.

Checks:

- exact email match
- exact phone match
- fuzzy full-name + company similarity using `SequenceMatcher`

Threshold:

- `0.85`

### `Backend/app/services/lead_assignment.py`

Lead assignment rules.

Methods:

- `manual`: requires explicit `user_id`.
- `round_robin`: rotates active sales reps in memory.
- `territory`: tries territory rules, then round robin.

Important:

- `ROUND_ROBIN_STATE` is in memory, so it resets when the process restarts.
- `TERRITORY_RULES` is currently an empty list.

### `Backend/app/services/lead_scoring.py`

Rule-based lead scoring.

Adds points for:

- company email
- referral source
- company present
- activities

Subtracts points when:

- no recent activity within 14 days

Final score is clamped from 0 to 100.

### `Backend/app/services/pipeline.py`

Pipeline and stage logic.

Responsibilities:

- Pipeline CRUD.
- Pipeline stage CRUD.
- Prevent deleting pipelines/stages referenced by deals.
- Move deals between stages.
- Set deal status when stage name contains `won` or `lost`.
- Require `lost_reason` when moving to a lost stage.
- Add `DealStageHistory`.
- Trigger follow-up task automation for configured stage names.

### `Backend/app/services/deals.py`

Deal logic.

Responsibilities:

- Deal CRUD and soft-delete.
- Sales-rep visibility.
- Enriched response with pipeline, stage, account, contact, owner names.
- Deal details with activities, tasks, collaborators, stage history.
- Stage move.
- Mark won/lost.
- Collaborator add/remove.
- Kanban grouping.
- Forecast calculations.
- Stale deal detection.
- Search sync.

### `Backend/app/services/activities.py`

Activity logging.

Responsibilities:

- List activities with filters.
- Create/update/delete activity.
- Log an email as activity by contact email.
- Build CSV export.
- Enrich owner name.

### `Backend/app/services/tasks.py`

Task logic.

Responsibilities:

- List tasks with display names for linked records.
- List overdue tasks.
- Create/update/delete.
- Complete task.
- Snooze task.

Important:

- Completing a task sets `completed_at`.
- Snoozing a completed task reopens it as pending.

### `Backend/app/services/task_automation.py`

Creates tasks automatically when a deal moves to configured stages.

Reads:

- `task_automation_rules.json`

Rules define:

- stage names or IDs
- task title
- description
- priority
- due date offset

### `Backend/app/services/task_automation_rules.json`

JSON rules for follow-up task creation.

Current rules:

- `Proposal Sent`: create high-priority proposal follow-up due in 2 days.
- `Negotiation`: create medium-priority negotiation task due in 3 days.

### `Backend/app/services/campaigns.py`

Campaign logic.

Responsibilities:

- Campaign CRUD.
- Campaign activation and pause.
- Enrollment listing and creation.
- Re-enrolling unsubscribed contacts.
- Unsubscribe contact.
- Metrics aggregation.
- Sequence step CRUD.
- Sequence reorder.
- Queue campaign step processing for active campaigns.

Important:

- Draft campaigns can be deleted.
- Non-draft campaigns cannot be deleted.
- Active campaigns queue `process_campaign_step` jobs.

### `Backend/app/services/projects.py`

Customer project logic.

Responsibilities:

- Project CRUD and soft-delete.
- Create project from won deal.
- Milestone CRUD.
- Complete milestone.
- Recalculate project health.
- Upload/list/delete documents.
- Build public portal response.

Important:

- Documents max size is 20 MB.
- `portal_token` is generated with UUID.
- Public portal only returns safe customer-facing project fields.

### `Backend/app/services/project_health.py`

Project health calculation.

Rules:

- Red if any open milestone is overdue.
- Yellow if any open milestone is due within 3 days.
- Green otherwise.

Also updates all active projects in scheduled jobs.

### `Backend/app/services/storage.py`

Project document storage.

Responsibilities:

- Sanitize filenames.
- Build storage keys.
- Upload to R2/S3-compatible storage if credentials exist.
- Return local placeholder URL if storage credentials are absent.
- Generate presigned download URLs when R2/S3 credentials exist.

### `Backend/app/services/notifications.py`

Notification support service.

Currently:

- Finds overdue tasks.
- Logs overdue-task messages to the audit logger.

Used by Celery notification tasks.

### `Backend/app/services/reports.py`

Reporting and export logic.

Responsibilities:

- Pipeline summary.
- Deal velocity.
- Win/loss.
- Forecast.
- Quota attainment.
- Lead volume.
- Lead funnel.
- Lead response time.
- Activity volume.
- Overdue tasks.
- Sequence performance.
- Customer health.
- Renewal pipeline.
- Dashboard.
- Custom report builder.
- Export rows for named reports.
- CSV generation.
- XLSX file generation.

Important implementation details:

- Uses SQLAlchemy Core table objects for aggregate queries.
- Uses snapshots for some reports when no filters are applied.
- Custom reports are restricted to whitelisted entities and fields.
- XLSX output is generated manually as zipped XML files.

### `Backend/app/services/search.py`

Search domain service.

Responsibilities:

- Convert contact/account/deal/lead responses into Meilisearch documents.
- Sync or delete documents in search indexes.
- Run global search across indexes.
- Apply sales-rep filters to search queries.
- Format Meilisearch hits into API responses.

Search indexes:

- contacts
- deals
- accounts
- leads

### `Backend/app/services/webhooks.py`

Webhook persistence service.

Responsibilities:

- Log inbound webhooks.
- Update webhook log status.
- List subscriptions.
- Create subscription.
- Delete subscription.

Subscription creation validates allowed event names.

### `Backend/app/services/webhook_dispatcher.py`

Outbound webhook dispatcher.

Responsibilities:

- Finds active subscriptions interested in an event.
- Queues `deliver_webhook_event` Celery tasks.
- Returns number of queued subscriptions.

## 17. Utility Files

### `Backend/app/utils/__init__.py`

Package marker.

### `Backend/app/utils/webhooks.py`

HMAC helpers.

Functions:

- `verify_hmac_signature(payload, signature, secret)`
- `build_hmac_signature(payload, secret)`

Supports signatures with or without `sha256=` prefix.

### `Backend/app/utils/search.py`

Low-level async Meilisearch client.

Important class:

- `AsyncMeilisearch`

Responsibilities:

- Create indexes.
- Update index settings.
- Add/replace documents.
- Delete documents.
- Search documents.

If `MEILISEARCH_URL` is not configured, client methods return without doing real search work.

### `Backend/app/utils/email.py`

Email sending helper.

Behavior:

- If `RESEND_API_KEY` is missing, logs a dry run and returns success.
- If configured, sends email through Resend API using `httpx`.

## 18. Worker Files

Celery workers run background jobs. Synchronous Celery task functions call async implementations through `execute_with_retry`.

### `Backend/app/workers/__init__.py`

Exports `celery_app`.

### `Backend/app/workers/celery_app.py`

Celery configuration.

Uses:

- Redis broker.
- Redis result backend.
- JSON serialization.
- UTC timezone.

Scheduled jobs:

- hourly overdue task checks
- daily stale deal alerts
- daily report snapshots
- daily project health updates
- daily lead score recalculation

### `Backend/app/workers/task_logging.py`

Shared Celery logging and retry helper.

Responsibilities:

- Creates `TaskLog` row at start.
- Marks success with result details.
- Marks error with exception details.
- Retries failures using exponential backoff.

### `Backend/app/workers/tasks.py`

Simple Celery health check task.

Task:

- `app.workers.tasks.health_check`

### `Backend/app/workers/campaign_tasks.py`

Campaign sequence processing.

Tasks:

- `process_campaign_step`
- `enroll_contact_in_campaign`

Important behavior:

- Sends campaign email.
- Records `sent` metric.
- Advances enrollment step.
- Schedules next step after `delay_days`.
- Completes enrollment when no next step exists.

### `Backend/app/workers/lead_tasks.py`

Lead scoring background jobs.

Tasks:

- `recalculate_lead_scores`
- `recalculate_lead_score`

### `Backend/app/workers/notification_tasks.py`

Notification background jobs.

Tasks:

- `check_overdue_tasks`
- `send_deal_stale_alert`

Important:

- Uses `TaskLog` rows to avoid duplicate daily notifications.
- Sends email through `utils.email.send_email`.

### `Backend/app/workers/project_tasks.py`

Project health scheduled job.

Task:

- `update_project_health`

### `Backend/app/workers/report_tasks.py`

Daily report snapshots.

Task:

- `generate_daily_snapshots`

Creates or updates snapshots for:

- pipeline summary
- lead volume
- activity volume

### `Backend/app/workers/search_tasks.py`

Search reindexing.

Task:

- `reindex_all`

It ensures indexes exist, then syncs active contacts, deals, accounts, and leads into Meilisearch.

### `Backend/app/workers/webhook_tasks.py`

Webhook background processing.

Tasks:

- `process_lead_form`
- `process_email_inbound`
- `process_calendar_event`
- `deliver_webhook_event`

Important behavior:

- Lead form creates a lead, assigns it round-robin, scores it, dispatches `lead.created`.
- Email inbound finds contact by sender email and creates an email activity.
- Calendar event finds contacts by attendees and creates meeting activities.
- Outbound webhook delivery signs payloads with subscription secret.

## 19. Alembic Files

### `Backend/alembic/env.py`

Alembic runtime setup.

Responsibilities:

- Imports app settings.
- Builds async DB URL.
- Imports `Base.metadata`.
- Runs migrations offline or online.
- Uses async SQLAlchemy engine for online migrations.
- Enables `compare_type=True` and `compare_server_default=True`.

Why `target_metadata = Base.metadata` matters:

- Alembic autogenerate compares SQLAlchemy models against the live database.

### `Backend/alembic/script.py.mako`

Template for new migration files. Alembic uses this when creating revisions.

### `Backend/alembic/versions/0001_initial_crm_models.py`

Initial schema.

Creates:

- PostgreSQL `pgcrypto` extension for `gen_random_uuid()`.
- All initial enums.
- users, roles, user_roles
- campaigns
- accounts
- contacts
- contact_tags
- custom_fields
- leads
- pipelines
- pipeline_stages
- deals
- deal_collaborators
- activities
- tasks
- campaign_enrollments
- campaign_sequence_steps
- projects
- milestones
- project_documents
- report_snapshots

### `Backend/alembic/versions/0002_update_user_roles_for_betterauth.py`

Changes `user_role` enum values from older names to BetterAuth/RBAC names.

Old examples:

- `admin`
- `manager`
- `marketing`
- `viewer`

New examples:

- `super_admin`
- `sales_manager`
- `marketing_manager`
- `read_only`

### `Backend/alembic/versions/0003_accounts_contacts_foundation.py`

Adds foundation fields:

- `accounts.custom_fields`
- `accounts.is_active`
- `contacts.is_active`

This enables flexible account metadata and soft deletion.

### `Backend/alembic/versions/0004_leads.py`

Adds:

- `leads.is_active`

This enables soft deletion for leads.

### `Backend/alembic/versions/0005_deals.py`

Adds deal lifecycle fields:

- `deals.closed_at`
- `deals.is_active`
- `deal_stage_history` table and indexes

### `Backend/alembic/versions/0006_campaigns.py`

Adds campaign attribution and metrics:

- `campaign_sequence_steps.variant`
- `leads.utm_source`
- `leads.utm_campaign`
- `leads.utm_medium`
- `campaign_metric_event_type` enum
- `campaign_metrics` table

### `Backend/alembic/versions/0007_projects.py`

Adds project portal/document improvements:

- Makes `projects.deal_id` nullable.
- Adds `projects.is_active`.
- Adds document `filename`, `file_size`, `mime_type`, and `storage_key`.

### `Backend/alembic/versions/0008_reports.py`

Adds reporting fields:

- `deals.type`
- index on `deals.type`
- `report_snapshots.date`
- nullable `report_snapshots.generated_by`
- `sales_quotas` table

### `Backend/alembic/versions/0009_task_logs.py`

Adds:

- unique constraint on report snapshots by report type and date
- `task_logs` table and indexes

### `Backend/alembic/versions/0010_webhooks.py`

Adds:

- `webhook_subscriptions`
- `webhook_logs`
- webhook log indexes

### `Backend/alembic/versions/0011_audit_logs.py`

Adds:

- `audit_logs`
- indexes by action, entity, and user

## 20. Script Files

### `Backend/scripts/seed_default_pipeline.py`

Creates a default `New Business` pipeline if it does not exist.

Stages:

- Prospecting
- Qualification
- Proposal Sent
- Negotiation
- Closed Won
- Closed Lost

### `Backend/scripts/seed_demo_data.py`

Large idempotent demo data seeder.

It creates or updates:

- roles
- users
- accounts
- contacts
- contact tags
- custom fields
- pipelines and stages
- campaigns and sequence steps
- campaign enrollments and metrics
- leads
- converted lead contacts
- deals
- deal collaborators and stage history
- activities
- tasks
- projects
- milestones
- project documents
- sales quotas
- report snapshots
- webhook subscriptions/logs
- task logs
- audit logs

The helper `upsert_one` makes the seed script safe to rerun by updating existing rows instead of blindly duplicating all data.

## 21. Load Test Files

### `Backend/load_tests/README.md`

Instructions for running load tests.

Scenarios:

- health
- crm-read
- reports

### `Backend/load_tests/api_load_test.py`

Async HTTP load test runner using `httpx`.

Features:

- configurable base URL
- configurable bearer token
- configurable users, duration, ramp-up, and timeout
- status-code counting
- exception counting
- p50, p95, p99 latency reporting
- failure thresholds for error rate and p95 latency

## 22. Test Files

### `Backend/tests/conftest.py`

Shared test setup.

Responsibilities:

- Sets default environment variables for tests.
- Provides fake user fixtures.
- Provides `make_test_user`.

### `Backend/tests/__init__.py`

Marks `tests` as a Python package. It currently only defines an empty `__all__`.

### `Backend/tests/test_auth.py`

Tests:

- JWT decode success.
- Invalid JWT rejection.
- Role dependency allow/deny behavior.

### `Backend/tests/test_users.py`

Tests:

- JWT handling.
- Current user lookup.
- Inactive user rejection.
- User route permissions.
- User creation/update behavior.

### `Backend/tests/test_contacts_accounts.py`

Tests:

- Account listing filters.
- Account details with contact count and deal value.
- Custom field validation.
- Contact listing/search/sort.
- Contact creation and detail.
- Contact timeline.

### `Backend/tests/test_leads.py`

Tests:

- Lead creation.
- Read-only write rejection.
- Lead conversion.
- CSV import.
- Duplicate detection.
- Lead scoring.

### `Backend/tests/test_deals_pipelines.py`

Tests:

- Deal creation route.
- Stage movement.
- Stage history.
- Forecast grouping.
- Kanban grouping.

### `Backend/tests/test_activities_tasks.py`

Tests:

- Activity creation validation.
- Owner-name enrichment.
- Activity CSV export.
- Task completion.
- Overdue task listing.
- Email logging.

### `Backend/tests/test_campaigns.py`

Tests:

- Campaign route creation.
- Enrollments.
- Idempotent enrollment behavior.
- Re-enrollment of unsubscribed contacts.
- Draft campaign scheduling behavior.
- Sequence step CRUD.
- Campaign step worker processing.

### `Backend/tests/test_projects.py`

Tests:

- Project creation from won deal.
- Milestone completion.
- Health calculation.
- Public portal auth behavior.

### `Backend/tests/test_reports.py`

Tests:

- Pipeline summary.
- Lead funnel.
- Forecast.
- Custom report field whitelist.
- Export filtering and hidden internal IDs.
- PDF export.
- CSV/XLSX export routes.

### `Backend/tests/test_search.py`

Tests:

- Search sync on create/update/delete.
- Global search route formatting.
- Sales-rep search filters.

### `Backend/tests/test_webhooks.py`

Tests:

- HMAC verification.
- Lead form webhook validation/logging/queueing.
- Inbound email worker contact/deal matching.

### `Backend/tests/test_celery_tasks.py`

Tests:

- Celery task wrappers.
- Task scheduling config.
- Health check task.

### `Backend/tests/test_hardening.py`

Tests:

- Audit log listener behavior.
- Contact purge confirmation token rejection.
- Validation error response shape.

### `Backend/tests/test_rbac.py`

Tests:

- Read-only user cannot write modules.
- Sales manager cannot create users.

## 23. Main Data Relationships

Important relationships:

- User owns accounts, contacts, leads, deals, tasks, activities, campaigns, and projects.
- Account has many contacts, deals, and projects.
- Contact may belong to an account.
- Lead can convert into contact/account/deal.
- Deal belongs to account, contact, owner, pipeline, and stage.
- Deal has collaborators and stage history.
- Activity and Task can link to lead/contact/deal/account.
- Campaign has sequence steps, enrollments, and metrics.
- Project belongs to account and optional deal.
- Project has milestones and documents.
- Report snapshots cache report data.
- Task logs track Celery jobs.
- Webhook logs track inbound and outbound webhooks.
- Audit logs track write changes.

## 24. Important Backend Concepts

### Soft Delete

Many domain records are not physically deleted. Instead, services set `is_active=False`.

Used by:

- users
- accounts
- contacts
- leads
- deals
- projects

Why:

- keeps history
- avoids breaking foreign keys
- allows auditability

### Hard Delete

Some records are physically deleted:

- activities
- tasks
- campaign steps
- milestones
- project documents
- webhook subscriptions

Contact purge is also a hard delete path for privacy/GDPR needs.

### Search Sync

After important create/update/delete operations, services call search sync helpers.

Examples:

- creating contact syncs to `contacts` index.
- deleting lead removes from `leads` index.
- `search_tasks.reindex_all` can rebuild indexes from database records.

### Background Jobs

Celery is used when work should happen outside the HTTP request:

- campaign sequence sending
- notification emails
- report snapshots
- project health updates
- lead scoring
- search reindexing
- webhook processing/delivery

### Audit Logging

Audit logs are automatic and database-level from SQLAlchemy session events, not manually written inside each service.

### Rate Limiting

SlowAPI adds a global rate limit. The public portal has an explicit lower limit.

### Reports

Reports use aggregate queries instead of loading all rows into Python. Some reports can use cached daily snapshots when no filters are provided.

### Webhooks

Inbound webhooks:

- must be signed
- must be JSON
- are logged
- are processed asynchronously

Outbound webhooks:

- are subscription-based
- are signed
- are delivered by Celery
- have logs for started/success/error

## 25. How to Run the Backend

Docker:

```powershell
cd Backend
docker compose up -d --build
```

Local without Docker:

```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

Celery worker:

```powershell
celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

Celery Beat:

```powershell
celery -A app.workers.celery_app.celery_app beat --loglevel=info
```

## 26. How to Add a New Backend Feature

Typical flow:

1. Add or update SQLAlchemy model in `app/models/`.
2. Add request/response schemas in `app/schemas/`.
3. Add business logic in `app/services/`.
4. Add endpoints in `app/routers/`.
5. Include router in `app/routers/__init__.py` if it is a new module.
6. Generate migration:

```powershell
python -m alembic revision --autogenerate -m "add feature"
```

7. Review the migration carefully.
8. Apply migration:

```powershell
python -m alembic upgrade head
```

9. Add tests in `tests/`.
10. Run tests:

```powershell
python -m pytest -q
```

## 27. How to Think About This Backend

Use this mental model:

- Models describe the database.
- Schemas describe API data shapes.
- Routers describe HTTP endpoints.
- Services do the real work.
- Dependencies provide database sessions and authenticated users.
- Middleware handles cross-cutting behavior like audit and rate limit.
- Workers do slow or scheduled work.
- Alembic keeps the database schema in sync with code.

If you are debugging a route, follow this path:

```text
router endpoint
  -> schema used by endpoint
  -> service function called by endpoint
  -> model/table touched by service
  -> side effects such as search sync, Celery job, webhook, audit log
  -> tests for that module
```

## 28. Current Backend API Summary

Base API prefix:

```text
/api/v1
```

Main groups:

```text
/users
/accounts
/contacts
/leads
/pipelines
/deals
/activities
/tasks
/campaigns
/projects
/portal
/reports
/search
/webhooks
```

Health check:

```text
/health
```

Authentication:

```http
Authorization: Bearer <BetterAuth JWT>
```

## 29. Most Important Files To Read First

If you want to understand the backend quickly, read in this order:

1. `Backend/app/main.py`
2. `Backend/app/config.py`
3. `Backend/app/database.py`
4. `Backend/app/dependencies.py`
5. `Backend/app/auth/permissions.py`
6. `Backend/app/models/base.py`
7. `Backend/app/models/__init__.py`
8. One domain model, for example `app/models/leads.py`
9. Matching schema, for example `app/schemas/leads.py`
10. Matching router, for example `app/routers/leads.py`
11. Matching service, for example `app/services/leads.py`
12. `Backend/alembic/env.py`
13. Latest migration in `Backend/alembic/versions/`
14. Matching tests in `Backend/tests/`

That path teaches the project structure faster than reading files alphabetically.
