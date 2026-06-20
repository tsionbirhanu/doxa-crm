# Doxa CRM System Guide

This guide explains the project in simple language.

We will use **Doxa Technologies** as the example company. Imagine Doxa Technologies sells software services to other companies. This CRM helps Doxa manage the full customer journey:

1. A possible customer becomes a **lead**.
2. A sales person contacts the lead.
3. If the lead is real, it becomes a **contact**, **account**, and maybe a **deal**.
4. The deal moves through the sales **pipeline**.
5. If the deal is won, it can become a customer **project**.
6. The customer can see project progress through a public **portal** link.
7. Managers use **reports** and **dashboard** pages to understand what is happening.

In one sentence:

**Doxa CRM is a web system for tracking customers from first interest, through sales, into delivery and customer success.**

---

## 1. Big Picture

The project has two main parts:

| Part | Folder | Simple meaning |
| --- | --- | --- |
| Frontend | `Frontend/` | The screens people click: dashboard, leads, deals, projects, settings. |
| Backend | `Backend/` | The API, database rules, permissions, reports, search, background jobs. |

The frontend and backend talk like this:

```text
User clicks button in browser
        |
        v
Next.js frontend page/component
        |
        v
Frontend API client sends HTTP request
        |
        v
FastAPI backend route
        |
        v
Backend service applies business rules
        |
        v
PostgreSQL database stores or reads data
        |
        v
Backend returns JSON
        |
        v
Frontend updates the screen
```

Example:

Alex, a Doxa sales rep, clicks **Create Lead**.

```text
LeadForm.tsx
  -> api.post("/leads/")
  -> Backend /api/v1/leads/
  -> leads_service.create_lead()
  -> leads table in database
  -> response returns to frontend
  -> Leads page refreshes
```

---

## 2. Technology Stack

### Frontend

The frontend is built with:

| Technology | Used for |
| --- | --- |
| Next.js 15 | Website/app routing and pages. |
| React 19 | UI components. |
| TypeScript | Safer frontend code. |
| Tailwind CSS | Styling. |
| TanStack Query | Loading and refreshing API data. |
| Zustand | Small auth/session state store. |
| BetterAuth | Login/session handling. |
| Recharts | Charts in dashboard and reports. |
| Lucide React | Icons. |
| Drag and drop library | Deal Kanban board. |

Important frontend files:

| File/folder | Meaning |
| --- | --- |
| `Frontend/app/` | Next.js pages and layouts. |
| `Frontend/app/(auth)/login/page.tsx` | Login screen. |
| `Frontend/app/(app)/` | Main logged-in CRM pages. |
| `Frontend/app/portal/[token]/page.tsx` | Public customer project portal. |
| `Frontend/components/` | Reusable UI and feature components. |
| `Frontend/hooks/useApi.ts` | React Query hooks for backend data. |
| `Frontend/lib/api.ts` | Low-level API client that sends requests to FastAPI. |
| `Frontend/lib/permissions.ts` | Frontend role/permission checks. |
| `Frontend/middleware.ts` | Protects logged-in routes. |
| `Frontend/types/api.ts` | TypeScript shapes for backend data. |

### Backend

The backend is built with:

| Technology | Used for |
| --- | --- |
| FastAPI | API server. |
| SQLAlchemy async ORM | Database models and queries. |
| Alembic | Database migrations. |
| PostgreSQL / Supabase Postgres | Main database. |
| Redis | Job queue/cache backend. |
| Celery | Background jobs. |
| Meilisearch | Fast global search. |
| Pytest | Backend tests. |
| Docker Compose | Runs frontend, backend, Redis, Meilisearch, workers. |

Important backend files:

| File/folder | Meaning |
| --- | --- |
| `Backend/app/main.py` | Creates the FastAPI app. |
| `Backend/app/routers/` | API endpoints. |
| `Backend/app/services/` | Business logic. |
| `Backend/app/models/` | Database tables. |
| `Backend/app/schemas/` | Request/response data shapes. |
| `Backend/app/auth/permissions.py` | Backend role rules. |
| `Backend/app/dependencies.py` | Auth and database dependencies. |
| `Backend/app/workers/` | Celery background jobs. |
| `Backend/alembic/versions/` | Database migrations. |
| `Backend/tests/` | Automated tests. |

---

## 3. Main Business Objects

These are the main nouns in the CRM.

### Lead

A **lead** is a possible customer who showed interest.

Doxa example:

> Sarah from BrightMart fills out a website form asking about Doxa Technologies' CRM implementation service.

That person is not yet a customer. She is a lead.

Lead fields include:

| Field | Meaning |
| --- | --- |
| `full_name` | Lead person's name. |
| `email` | Lead email. |
| `phone` | Lead phone. |
| `company` | Company they work for. |
| `source` | Where the lead came from: website, referral, event, campaign, etc. |
| `score` | How valuable or ready the lead seems. |
| `status` | `new`, `contacted`, `qualified`, `disqualified`, or `converted`. |
| `assigned_to` | The Doxa user responsible for the lead. |

Important files:

```text
Frontend/components/leads/
Backend/app/models/leads.py
Backend/app/routers/leads.py
Backend/app/services/leads.py
```

### Contact

A **contact** is a real person Doxa wants to keep in the CRM.

Doxa example:

> Sarah from BrightMart becomes a real contact after Alex confirms she is the correct decision maker.

A contact can belong to an account.

Important files:

```text
Frontend/components/contacts/
Backend/app/models/contacts.py
Backend/app/routers/contacts.py
Backend/app/services/contacts.py
```

### Account

An **account** is a company or customer organization.

Doxa example:

> BrightMart is the account. Sarah is a contact inside BrightMart.

An account can have many contacts, deals, and projects.

Important files:

```text
Frontend/components/accounts/
Backend/app/models/contacts.py
Backend/app/routers/accounts.py
Backend/app/services/accounts.py
```

### Deal

A **deal** is a sales opportunity with money attached.

Doxa example:

> BrightMart may buy a $25,000 CRM setup package from Doxa Technologies. That opportunity is a deal.

Deal fields include:

| Field | Meaning |
| --- | --- |
| `title` | Deal name. |
| `value` | Possible money value. |
| `pipeline_id` | Which sales pipeline it belongs to. |
| `stage_id` | Current sales stage. |
| `probability` | Chance of closing. |
| `expected_close` | Expected close date. |
| `status` | `open`, `won`, or `lost`. |
| `owner_id` | Sales person responsible. |

Important files:

```text
Frontend/components/deals/
Backend/app/models/deals.py
Backend/app/routers/deals.py
Backend/app/services/deals.py
```

### Pipeline And Stage

A **pipeline** is the sales process.

A **stage** is one step in that process.

Doxa example pipeline:

```text
New Opportunity -> Discovery -> Proposal Sent -> Negotiation -> Closed Won
```

Deals move across these stages on the Kanban board.

Important files:

```text
Frontend/components/deals/KanbanBoard.tsx
Frontend/components/settings/PipelineSettingsClient.tsx
Backend/app/models/deals.py
Backend/app/routers/pipelines.py
Backend/app/services/pipeline.py
```

### Activity

An **activity** records something that happened.

Doxa example:

> Alex called Sarah for 20 minutes and discussed BrightMart's CRM needs.

Activity types:

```text
call
email
meeting
note
task
```

Important files:

```text
Frontend/components/activities/
Backend/app/models/activities.py
Backend/app/routers/activities.py
Backend/app/services/activities.py
```

### Task

A **task** is something someone must do.

Doxa example:

> Alex must send Sarah a proposal by Friday.

Task statuses:

```text
pending
in_progress
completed
cancelled
```

Task priorities:

```text
low
medium
high
urgent
```

Important files:

```text
Frontend/components/tasks/
Backend/app/models/activities.py
Backend/app/routers/tasks.py
Backend/app/services/tasks.py
```

### Campaign

A **campaign** is a marketing/sales outreach effort.

Doxa example:

> Doxa runs a "Retail CRM Upgrade Campaign" to contact 200 retail companies.

Campaigns can have:

| Thing | Meaning |
| --- | --- |
| Campaign | The overall marketing effort. |
| Enrollment | A contact added to the campaign. |
| Sequence step | A planned email, call, task, or social touch. |
| Metric | Sent, opened, clicked, replied, converted. |

Important files:

```text
Frontend/components/campaigns/
Backend/app/models/campaigns.py
Backend/app/routers/campaigns.py
Backend/app/services/campaigns.py
```

### Project

A **project** is work Doxa performs after a deal is won.

Doxa example:

> BrightMart signs the contract. Doxa creates a "BrightMart CRM Implementation" project.

Projects have:

| Thing | Meaning |
| --- | --- |
| Milestones | Major delivery steps. |
| Documents | Uploaded files for the project. |
| Health | `green`, `yellow`, or `red`. |
| Portal token | Public link for the customer portal. |

Important files:

```text
Frontend/components/projects/
Frontend/app/portal/[token]/page.tsx
Backend/app/models/projects.py
Backend/app/routers/projects.py
Backend/app/services/projects.py
Backend/app/services/project_health.py
```

### Report

A **report** shows business numbers.

Doxa example:

> Priya, the sales manager, checks pipeline value, win/loss rate, forecast, lead funnel, and overdue tasks.

Important files:

```text
Frontend/components/reports/
Backend/app/routers/reports.py
Backend/app/services/reports.py
```

### Search

Global search lets users search leads, contacts, accounts, and deals.

Doxa example:

> Alex presses Ctrl+K and searches "BrightMart" to find the account, deal, and contact quickly.

Important files:

```text
Frontend/components/search/
Backend/app/routers/search.py
Backend/app/services/search.py
```

---

## 4. The Real-World Story

This is the easiest way to understand the whole system.

### Step 1: Marketing creates interest

Zoe, a Doxa marketing rep, creates a campaign:

```text
Campaign name: Retail CRM Upgrade Campaign
Type: email
Budget: $5,000
Target: retail companies
```

She adds sequence steps:

```text
Day 1: Send intro email
Day 3: Follow-up email
Day 6: Create call task
```

Frontend:

```text
/campaigns
/campaigns/[id]
```

Backend:

```text
/api/v1/campaigns
```

### Step 2: A lead enters the system

Sarah from BrightMart fills out a Doxa website form.

The lead can enter by:

| Method | Backend support |
| --- | --- |
| Manual create | `POST /api/v1/leads/` |
| CSV import | `POST /api/v1/leads/import` |
| Lead-form webhook | `POST /api/v1/webhooks/lead-form` |

The lead appears on:

```text
/leads
```

### Step 3: The system checks lead quality

The backend can calculate a lead score.

Score examples:

| Signal | Effect |
| --- | --- |
| Company email instead of Gmail/Yahoo | Adds points. |
| Referral source | Adds points. |
| Company name exists | Adds points. |
| More activities | Adds points. |
| No recent activity | Removes points. |

Code:

```text
Backend/app/services/lead_scoring.py
```

### Step 4: The system checks duplicates

The duplicate checker compares:

| Duplicate check | Meaning |
| --- | --- |
| Same email | Definitely possible duplicate. |
| Same phone | Definitely possible duplicate. |
| Similar name + company | Fuzzy possible duplicate. |

Code:

```text
Frontend/components/leads/DuplicatesView.tsx
Backend/app/services/duplicate_detection.py
```

### Step 5: Sales works the lead

Alex, a Doxa sales rep, calls Sarah.

He can:

| Action | CRM object |
| --- | --- |
| Log the call | Activity |
| Schedule follow-up | Task |
| Update lead status | Lead |
| Recalculate score | Lead score |

Frontend:

```text
/leads/[id]
/activities
/tasks
```

### Step 6: Lead becomes contact, account, and deal

If Sarah is qualified, Alex converts the lead.

The conversion can create:

| Created thing | Example |
| --- | --- |
| Contact | Sarah Patel |
| Account | BrightMart |
| Deal | BrightMart CRM Implementation - $25,000 |

Backend:

```text
POST /api/v1/leads/{lead_id}/convert
```

Code:

```text
Backend/app/services/leads.py
```

### Step 7: Deal moves through pipeline

The deal appears on the Kanban board.

Alex drags it:

```text
Discovery -> Proposal Sent -> Negotiation -> Closed Won
```

Backend:

```text
POST /api/v1/deals/{deal_id}/stage
```

When a deal moves to some stages, the backend can create automatic tasks.

Current automation rules:

| Stage | Automatic task |
| --- | --- |
| Proposal Sent | Send proposal follow-up. |
| Negotiation | Prepare negotiation next steps. |

Code:

```text
Backend/app/services/task_automation.py
Backend/app/services/task_automation_rules.json
```

### Step 8: Deal is won or lost

If BrightMart signs:

```text
POST /api/v1/deals/{deal_id}/won
```

If BrightMart says no:

```text
POST /api/v1/deals/{deal_id}/lost
```

Lost deals store a lost reason.

### Step 9: Won deal becomes a project

After winning the deal, Doxa can create a project from it.

Example:

```text
Project: BrightMart CRM Implementation
Account: BrightMart
Owner: Lina from customer success
Health: green
```

Backend:

```text
POST /api/v1/projects/from-deal/{deal_id}
```

### Step 10: Customer success manages delivery

Lina, a customer success user, manages the project.

She can:

| Action | Example |
| --- | --- |
| Add milestones | Kickoff, Data Migration, Training, Go Live. |
| Complete milestones | Mark Training as complete. |
| Upload documents | Project plan PDF, requirements doc. |
| Share portal link | BrightMart sees read-only progress. |

Project health:

| Health | Meaning |
| --- | --- |
| Green | No open milestone is overdue or due very soon. |
| Yellow | A milestone is due within 3 days. |
| Red | A milestone is overdue. |

Code:

```text
Backend/app/services/project_health.py
```

### Step 11: Customer sees portal

BrightMart can open:

```text
/portal/{portal_token}
```

They do not need to log in.

They only see:

| Portal shows | Portal does not show |
| --- | --- |
| Project name | Internal notes |
| Account name | Deals |
| Project status | Sales data |
| Health | User management |
| Milestones | Private CRM pages |

### Step 12: Managers use reports

Priya, the sales manager, uses reports:

| Report area | Meaning |
| --- | --- |
| Sales | Pipeline summary, win/loss, forecast, velocity. |
| Leads | Lead volume, lead funnel, response time. |
| Activity | Activity volume and overdue tasks. |
| Customers | Customer health and renewal pipeline. |

Frontend:

```text
/reports
```

Backend:

```text
/api/v1/reports/*
```

---

## 5. Frontend Page Map

These are the main pages users see.

| URL | What it is for |
| --- | --- |
| `/login` | User login. |
| `/dashboard` | Business overview: stats, pipeline chart, lead funnel, overdue tasks, stale deals. |
| `/leads` | Lead list, filters, create/edit, import, duplicates, assignment. |
| `/leads/[id]` | One lead detail page. |
| `/contacts` | Contact list and filters. |
| `/contacts/[id]` | Contact detail and timeline. |
| `/accounts` | Company/account list. |
| `/accounts/[id]` | Account detail with contacts, deals, and activity. |
| `/deals` | Sales pipeline Kanban and forecast. |
| `/pipeline` | Redirects to `/deals`. |
| `/deals/[id]` | Deal detail, activities, tasks, collaborators, won/lost actions. |
| `/activities` | Activity log. |
| `/tasks` | My tasks and all tasks. |
| `/campaigns` | Marketing/sales campaigns list. |
| `/campaigns/[id]` | Campaign detail, sequence steps, enrollments, metrics. |
| `/projects` | Customer projects list. |
| `/projects/[id]` | Project detail, milestones, documents, portal link. |
| `/reports` | Sales, leads, activity, and customer reports. |
| `/search` | Full search page. |
| `/settings` | Settings home. |
| `/settings/users` | User management. |
| `/settings/pipeline` | Pipeline and stage setup. |
| `/settings/integrations` | Integrations placeholder. |
| `/settings/billing` | Billing placeholder. |
| `/portal/[token]` | Public customer project portal. |

### Frontend layout

The logged-in app uses:

| Component | Meaning |
| --- | --- |
| `Sidebar.tsx` | Left navigation. |
| `Topbar.tsx` | Page title, search button, current user. |
| `SearchModal.tsx` | Ctrl+K search modal. |
| `DataTable.tsx` | Reusable table. |
| `StatusPill.tsx` | Reusable status label. |
| `ActivityTimeline.tsx` | Reusable timeline. |

### Frontend data loading

Most pages use TanStack Query.

Simple meaning:

```text
useQuery = load data
useMutation = create/update/delete data
queryClient.invalidateQueries = reload data after a change
```

Important files:

```text
Frontend/hooks/useApi.ts
Frontend/lib/api.ts
```

---

## 6. Backend API Map

All main API routes start with:

```text
/api/v1
```

| API module | Main purpose |
| --- | --- |
| `/users` | Users and roles. |
| `/accounts` | Company records. |
| `/contacts` | People records. |
| `/leads` | Lead capture, scoring, import, duplicates, conversion. |
| `/pipelines` | Pipeline and stage settings. |
| `/deals` | Sales opportunities and Kanban movement. |
| `/activities` | Calls, emails, meetings, notes. |
| `/tasks` | Follow-up work. |
| `/campaigns` | Campaigns, sequence steps, enrollments, metrics. |
| `/projects` | Customer projects, milestones, documents. |
| `/portal/{token}` | Public customer project portal API. |
| `/reports` | Dashboard and report data. |
| `/search` | Global search. |
| `/webhooks` | Inbound webhooks and outbound subscriptions. |

Backend pattern:

```text
router = receives HTTP request
schema = validates request/response shape
service = business logic
model = database table
```

Example for leads:

```text
Backend/app/routers/leads.py
Backend/app/schemas/leads.py
Backend/app/services/leads.py
Backend/app/models/leads.py
```

---

## 7. Roles And Permissions

This project has these CRM roles:

```text
super_admin
sales_manager
sales_rep
marketing_manager
marketing_rep
customer_success
read_only
```

Demo users:

| Email | Role | Simple meaning |
| --- | --- | --- |
| `admin@doxa.local` | `super_admin` | Can manage the whole system. |
| `sales.manager@doxa.local` | `sales_manager` | Manages sales team, pipeline, reports. |
| `alex.rep@doxa.local` | `sales_rep` | Works assigned leads and own deals. |
| `maya.rep@doxa.local` | `sales_rep` | Works assigned leads and own deals. |
| `marketing.manager@doxa.local` | `marketing_manager` | Runs marketing operations and leads. |
| `marketing.rep@doxa.local` | `marketing_rep` | Helps create campaigns and leads. |
| `success@doxa.local` | `customer_success` | Manages customer projects and contacts. |
| `readonly@doxa.local` | `read_only` | Can view, but should not change records. |

### Role examples at Doxa Technologies

| Role | Real-world person | What they do |
| --- | --- | --- |
| `super_admin` | Doxa system owner | Creates users, controls global settings, can access everything. |
| `sales_manager` | Priya | Reviews pipeline, manages stages, sees team sales work. |
| `sales_rep` | Alex | Owns leads, contacts, accounts, and deals assigned to him. |
| `marketing_manager` | Noah | Plans campaigns and sees lead performance. |
| `marketing_rep` | Zoe | Creates campaigns, imports leads, enrolls contacts. |
| `customer_success` | Lina | Manages customer projects after deals are won. |
| `read_only` | Omar | Looks at data and reports without editing. |

### Permission matrix

The frontend hides buttons based on role, but the backend is the real security layer.

| Area | Who can write/change data |
| --- | --- |
| Users | Only `super_admin` can create, update, or delete users. `super_admin` and `sales_manager` can list users. |
| Settings | `super_admin`, `sales_manager`. |
| Pipeline setup | `super_admin`, `sales_manager`. |
| Leads | `super_admin`, `sales_manager`, `sales_rep`, `marketing_manager`, `marketing_rep`. |
| Contacts | `super_admin`, `sales_manager`, `sales_rep`, `marketing_manager`, `marketing_rep`, `customer_success`. |
| Accounts | `super_admin`, `sales_manager`, `sales_rep`, `customer_success`. |
| Deals | `super_admin`, `sales_manager`, `sales_rep`. |
| Activities | `super_admin`, `sales_manager`, `sales_rep`, `marketing_manager`, `marketing_rep`, `customer_success`. |
| Tasks | Same as activities. |
| Campaigns | `super_admin`, `marketing_manager`, `marketing_rep`. |
| Projects | `super_admin`, `sales_manager`, `customer_success`. |
| Webhook subscriptions | `super_admin`. |
| Reports | Logged-in users can read report data. |
| Search | Logged-in users can search, with visibility limits. |

### Visibility rules

Some users can only see their own records.

| Area | Rule |
| --- | --- |
| Leads | Sales reps only see leads assigned to themselves. |
| Contacts | Sales reps only see contacts they own. |
| Accounts | Sales reps see accounts they own or accounts containing their contacts. |
| Deals | Sales reps only see deals they own. |
| Tasks | Non-managers see only their own tasks. |
| Activities | Non-managers see only their own activities. |
| Search | Sales reps search only their own contacts, accounts, deals, and leads. |

In this backend, "manager" for task/activity visibility means:

```text
super_admin
sales_manager
```

---

## 8. Authentication

Login is handled by BetterAuth in the frontend.

Then the frontend sends a bearer token to FastAPI:

```http
Authorization: Bearer <token>
```

The backend checks that token using:

```text
Backend/app/auth/jwt.py
Backend/app/dependencies.py
```

Important rule:

```text
Frontend BETTER_AUTH_SECRET must match Backend SECRET_KEY
```

If those do not match, login may work in the frontend, but backend API calls will fail.

---

## 9. Database Relationships

Think of the database like filing cabinets.

Here is the simple relationship map:

```text
User
  owns Leads
  owns Contacts
  owns Accounts
  owns Deals
  owns Tasks
  owns Activities
  owns Projects

Lead
  can become Contact
  can create Account
  can create Deal

Account
  has many Contacts
  has many Deals
  has many Projects

Contact
  belongs to Account
  can be linked to Deals
  can be enrolled in Campaigns

Deal
  belongs to Account
  belongs to Contact
  belongs to Pipeline
  belongs to Pipeline Stage
  can become Project when won

Campaign
  has many Sequence Steps
  has many Enrollments
  has many Metrics

Project
  belongs to Account
  may come from Deal
  has many Milestones
  has many Documents
  has one Portal Token
```

---

## 10. Background Jobs

Not everything happens when a user clicks.

Some work runs in the background using Celery.

| Job | Meaning |
| --- | --- |
| Check overdue tasks hourly | Finds tasks that need attention. |
| Send stale deal alert daily | Finds deals with no recent activity. |
| Generate daily report snapshots | Saves report data for faster reports/history. |
| Update project health daily | Recalculates green/yellow/red project health. |
| Recalculate lead scores daily | Refreshes lead scores. |

Important files:

```text
Backend/app/workers/celery_app.py
Backend/app/workers/*.py
```

---

## 11. Search

The system uses Meilisearch for global search.

Search indexes:

```text
contacts
accounts
deals
leads
```

When records are created or updated, backend services sync them to search.

Example:

```text
Create lead
  -> save in PostgreSQL
  -> sync lead to Meilisearch
  -> Ctrl+K can find it
```

Important file:

```text
Backend/app/services/search.py
```

---

## 12. Webhooks

Webhooks let outside systems send data into the CRM.

Supported inbound webhook examples:

| Webhook | Meaning |
| --- | --- |
| `/webhooks/lead-form` | Website lead form submits a new lead. |
| `/webhooks/email-inbound` | Email event becomes an activity. |
| `/webhooks/calendar-event` | Calendar event becomes an activity/meeting. |

The backend also supports outbound webhook subscriptions.

Only `super_admin` can manage webhook subscriptions.

Important files:

```text
Backend/app/routers/webhooks.py
Backend/app/services/webhooks.py
Backend/app/services/webhook_dispatcher.py
```

---

## 13. Reports And Dashboard

The dashboard is a quick summary.

Dashboard shows:

| Widget | Meaning |
| --- | --- |
| Open deals | Active sales opportunities. |
| Leads this month | New lead volume. |
| Overdue tasks | Work that is late. |
| Activities this week | Sales/customer activity. |
| Pipeline chart | Money by sales stage. |
| Lead funnel | Lead conversion shape. |
| Stale deals | Deals with no recent activity. |

Reports go deeper:

| Report | Meaning |
| --- | --- |
| Pipeline summary | Deal value by stage. |
| Deal velocity | How fast deals move. |
| Win/loss | Won vs lost performance. |
| Forecast | Expected future sales. |
| Lead volume | Lead count over time. |
| Lead funnel | New/contacted/qualified/converted shape. |
| Lead response time | How fast the team responds. |
| Activity volume | Calls, emails, meetings, notes. |
| Overdue tasks | Late work. |
| Campaign sequence performance | Marketing sequence results. |
| Customer health | Project/customer health. |
| Renewal pipeline | Customer renewal opportunities. |

Important files:

```text
Frontend/components/dashboard/
Frontend/components/reports/
Backend/app/services/reports.py
Backend/app/routers/reports.py
```

---

## 14. How To Read The Code

If you want to understand one feature, follow this path:

```text
Page
  -> Component
  -> Hook/API call
  -> Backend router
  -> Backend schema
  -> Backend service
  -> Backend model
```

Example: lead duplicates

```text
Frontend/components/leads/DuplicatesView.tsx
  -> api.get("/leads/duplicates")
  -> api.post("/leads/merge")
  -> Backend/app/routers/leads.py
  -> Backend/app/services/duplicate_detection.py
  -> Backend/app/services/leads.py
  -> Backend/app/models/leads.py
```

Example: project portal

```text
Frontend/app/portal/[token]/page.tsx
  -> GET /api/v1/portal/{token}
  -> Backend/app/routers/projects.py
  -> Backend/app/services/projects.py
  -> Backend/app/models/projects.py
```

Example: deal Kanban

```text
Frontend/components/deals/DealsPageClient.tsx
Frontend/components/deals/KanbanBoard.tsx
  -> GET /api/v1/deals/kanban
  -> POST /api/v1/deals/{deal_id}/stage
  -> Backend/app/routers/deals.py
  -> Backend/app/services/deals.py
  -> Backend/app/services/pipeline.py
  -> Backend/app/models/deals.py
```

---

## 15. How To Run Locally

The existing frontend and backend READMEs have detailed setup instructions.

Quick local URLs:

| Service | URL |
| --- | --- |
| Frontend | `http://localhost:3000` |
| Backend API | `http://localhost:8001` |
| Backend docs | `http://localhost:8001/docs` |
| Customer portal | `http://localhost:3000/portal/{portal_token}` |
| Meilisearch | `http://localhost:7700` |

Run with Docker Compose:

```powershell
cd Backend
docker compose up -d --build
```

Run frontend only:

```powershell
cd Frontend
npm install --legacy-peer-deps
npm run dev
```

Run backend only:

```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

---

## 16. Most Important Files For Learning

Start with these files in this order.

| Order | File | Why |
| --- | --- | --- |
| 1 | `Frontend/readme.md` | Frontend overview. |
| 2 | `Backend/README.md` | Backend overview. |
| 3 | `Frontend/components/layout/Sidebar.tsx` | Shows main navigation. |
| 4 | `Frontend/hooks/useApi.ts` | Shows what frontend calls. |
| 5 | `Frontend/types/api.ts` | Shows frontend data types. |
| 6 | `Backend/app/routers/__init__.py` | Shows all backend modules. |
| 7 | `Backend/app/auth/permissions.py` | Shows role rules. |
| 8 | `Backend/app/models/users.py` | Shows roles and users. |
| 9 | `Backend/app/models/leads.py` | First business object. |
| 10 | `Backend/app/services/leads.py` | Best end-to-end business workflow. |
| 11 | `Backend/app/models/deals.py` | Pipeline and sales opportunity structure. |
| 12 | `Backend/app/services/projects.py` | Won deal to customer project flow. |

---

## 17. Simple Mental Model

Use this sentence when the project feels confusing:

**Marketing creates demand, sales converts demand into revenue, customer success delivers the work, and managers watch the numbers.**

In this CRM:

```text
Marketing demand = Campaigns + Leads
Sales work = Contacts + Accounts + Deals + Pipeline
Daily follow-up = Activities + Tasks
Delivery work = Projects + Milestones + Documents + Portal
Management view = Dashboard + Reports + Search
System control = Users + Roles + Settings + Webhooks
```

That is the whole project.

