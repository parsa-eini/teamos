# Team Management Product — AI Build Specification

**Status:** Phase 1 / MVP
**Document Version:** 1.0
**Primary Purpose:** Source of truth for AI coding agents
**Architecture:** Modular monolith
**Backend:** Python + FastAPI
**Frontend:** React + TypeScript
**Database:** PostgreSQL
**Cache:** Redis
**Containerization:** Docker Compose

---

# 1. Product Vision

The product is a lightweight team-management platform designed to help engineering managers and team leads manage:

* Organizations
* Teams
* Team members
* Projects
* Tasks
* Goals
* Regular check-ins
* Team activity
* Basic management dashboards

The MVP should solve one central problem:

> Give managers a single place to understand what their team is working on, what they committed to, what progress they have made, and where attention is needed.

The MVP is NOT intended to compete feature-for-feature with Jira, Linear, Lattice, 15Five, or Notion.

The initial product should focus on:

1. Team visibility
2. Lightweight task/project management
3. Goals and progress
4. Regular check-ins
5. Manager dashboard

---

# 2. Phase 1 Goals

The MVP must allow the following flow:

```text
User
  ↓
Create account
  ↓
Create organization
  ↓
Invite/create team members
  ↓
Create team
  ↓
Create project
  ↓
Create tasks
  ↓
Assign tasks to team members
  ↓
Track task progress
  ↓
Create goals
  ↓
Record check-ins
  ↓
View manager dashboard
```

---

# 3. Explicit Non-Goals

Do NOT implement the following in Phase 1 unless explicitly requested:

* SSO
* OAuth
* Slack integration
* Microsoft Teams integration
* Google Workspace integration
* Jira integration
* GitHub integration
* GitLab integration
* AI-generated performance reviews
* AI employee scoring
* Payroll
* HRIS integration
* Time tracking
* Attendance tracking
* Complex permissions
* Custom workflow engines
* Custom fields
* Kanban customization
* Advanced reporting
* Billing/subscriptions
* Multi-region deployment
* Microservices
* Kubernetes
* Event sourcing
* CQRS
* GraphQL

The architecture should not prevent these features later, but they should not complicate Phase 1.

---

# 4. Architecture Principles

## 4.1 Modular Monolith

The backend must be a modular monolith.

Do NOT create microservices.

Logical modules:

```text
auth
organizations
teams
users
projects
tasks
goals
checkins
dashboard
notifications
```

They live in one FastAPI application and one PostgreSQL database.

---

# 5. Repository Structure

```text
team-management/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   ├── database.py
│   │   │   ├── redis.py
│   │   │   └── logging.py
│   │   │
│   │   ├── common/
│   │   │   ├── exceptions.py
│   │   │   ├── pagination.py
│   │   │   ├── responses.py
│   │   │   └── dependencies.py
│   │   │
│   │   ├── modules/
│   │   │   ├── auth/
│   │   │   ├── users/
│   │   │   ├── organizations/
│   │   │   ├── teams/
│   │   │   ├── projects/
│   │   │   ├── tasks/
│   │   │   ├── goals/
│   │   │   ├── checkins/
│   │   │   ├── dashboard/
│   │   │   └── notifications/
│   │   │
│   │   └── tests/
│   │
│   ├── alembic/
│   ├── alembic.ini
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── README.md
│
├── website/
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── Dockerfile
│   └── README.md
│
├── panel/
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── Dockerfile
│   └── README.md
│
├── docs/
│   ├── architecture.md
│   ├── database.md
│   ├── api.md
│   └── decisions/
│
├── .cursor/
│   └── rules/
│
├── docker-compose.yml
├── .env.example
├── AI_BUILD_SPEC.md
├── IMPLEMENTATION_PLAN.md
└── DEFINITION_OF_DONE.md
```

---

# 6. Backend Technology

Use:

* Python 3.12+
* FastAPI
* SQLAlchemy 2.x
* Alembic
* PostgreSQL
* Redis
* Pydantic v2
* pytest
* httpx
* Ruff
* mypy where practical

Do not introduce Django.

Do not introduce another ORM.

Do not introduce another database.

---

# 7. Frontend Technology

Use:

* React
* TypeScript
* Vite
* React Router
* TanStack Query
* Axios or fetch
* Tailwind CSS

The website and panel are separate React applications.

Do not combine them into one frontend application.

---

# 8. Website vs Panel

## Website

The website is the public-facing application.

Initial pages:

```text
/
 /login
 /register
 /features
 /pricing
 /about
```

The website should remain lightweight.

Do not put authenticated management functionality here.

---

## Panel

The panel is the authenticated application.

Pages:

```text
/login

/dashboard

/organization
/organization/members

/teams
/teams/:id

/projects
/projects/:id

/tasks

/goals

/checkins

/settings
```

The panel is the primary MVP application.

---

# 9. Authentication

Phase 1 uses:

```text
Email + password
```

Passwords must never be stored in plaintext.

Use a modern password hashing algorithm such as Argon2id.

Authentication should use access tokens.

The implementation should allow refresh-token support without requiring major architectural changes.

Do not implement OAuth in Phase 1.

---

# 10. Authorization

Phase 1 roles:

```text
OWNER
ADMIN
MANAGER
MEMBER
```

Basic permissions:

### OWNER

Can:

* Manage organization
* Manage members
* Manage teams
* Manage projects
* Manage goals
* Manage check-ins
* View all dashboards

### ADMIN

Can:

* Manage members
* Manage teams
* Manage projects
* View dashboards

### MANAGER

Can:

* Manage assigned teams
* Manage projects
* Assign tasks
* Create goals
* Conduct check-ins
* View team dashboard

### MEMBER

Can:

* View own teams
* View assigned projects
* View assigned tasks
* Update own tasks
* View own goals
* Submit check-ins

Authorization must be enforced on the backend.

Frontend hiding a button is NOT authorization.

---

# 11. Multi-Tenancy

The application is organization-based.

Every organization-owned entity must ultimately belong to an organization.

Conceptually:

```text
Organization
    │
    ├── Users
    ├── Teams
    ├── Projects
    ├── Goals
    └── Check-ins
```

Never return another organization's data.

Every authenticated request must be evaluated within the user's organization context.

---

# 12. Core Database Model

## User

```text
users
-----
id UUID PK
email VARCHAR UNIQUE
password_hash VARCHAR
first_name VARCHAR
last_name VARCHAR
is_active BOOLEAN
created_at TIMESTAMP
updated_at TIMESTAMP
```

---

## Organization

```text
organizations
-------------
id UUID PK
name VARCHAR
slug VARCHAR UNIQUE
created_at TIMESTAMP
updated_at TIMESTAMP
```

---

## Organization Membership

Do not put `organization_id` directly on users.

Use membership.

```text
organization_memberships
------------------------
id UUID PK
organization_id UUID FK
user_id UUID FK
role ENUM
created_at TIMESTAMP
```

Unique:

```text
organization_id + user_id
```

---

# 13. Team

```text
teams
-----
id UUID PK
organization_id UUID FK
name VARCHAR
description TEXT NULL
created_at TIMESTAMP
updated_at TIMESTAMP
```

---

# 14. Team Membership

```text
team_memberships
----------------
id UUID PK
team_id UUID FK
user_id UUID FK
created_at TIMESTAMP
```

Unique:

```text
team_id + user_id
```

---

# 15. Project

```text
projects
--------
id UUID PK
organization_id UUID FK
team_id UUID FK NULL
name VARCHAR
description TEXT NULL
status ENUM
start_date DATE NULL
end_date DATE NULL
created_by UUID FK
created_at TIMESTAMP
updated_at TIMESTAMP
```

Project statuses:

```text
PLANNED
ACTIVE
COMPLETED
ARCHIVED
```

---

# 16. Task

```text
tasks
-----
id UUID PK
organization_id UUID FK
project_id UUID FK
title VARCHAR
description TEXT NULL
status ENUM
priority ENUM
assignee_id UUID FK NULL
created_by UUID FK
due_date DATE NULL
created_at TIMESTAMP
updated_at TIMESTAMP
```

Statuses:

```text
TODO
IN_PROGRESS
DONE
CANCELLED
```

Priorities:

```text
LOW
MEDIUM
HIGH
URGENT
```

---

# 17. Goal

```text
goals
-----
id UUID PK
organization_id UUID FK
team_id UUID FK NULL
user_id UUID FK NULL
title VARCHAR
description TEXT NULL
status ENUM
progress INTEGER
start_date DATE NULL
due_date DATE NULL
created_by UUID FK
created_at TIMESTAMP
updated_at TIMESTAMP
```

Progress:

```text
0 - 100
```

Statuses:

```text
NOT_STARTED
IN_PROGRESS
COMPLETED
CANCELLED
```

---

# 18. Check-in

A check-in is a periodic management interaction.

```text
checkins
--------
id UUID PK
organization_id UUID FK
manager_id UUID FK
member_id UUID FK
period_start DATE
period_end DATE
status ENUM
wins TEXT NULL
challenges TEXT NULL
next_steps TEXT NULL
manager_notes TEXT NULL
created_at TIMESTAMP
updated_at TIMESTAMP
```

Statuses:

```text
DRAFT
SUBMITTED
REVIEWED
```

Phase 1 does not need a complex questionnaire system.

---

# 19. Notification

Implement a minimal notification system.

```text
notifications
-------------
id UUID PK
user_id UUID FK
type VARCHAR
title VARCHAR
message TEXT
is_read BOOLEAN
created_at TIMESTAMP
```

Notifications can initially be generated synchronously.

Redis can later support asynchronous notification processing.

---

# 20. Database Rules

Use UUIDs for primary keys.

Use UTC timestamps.

Every timestamp should be timezone-aware.

Use database constraints where appropriate.

Examples:

```text
UNIQUE(email)

UNIQUE(organization_id, user_id)

UNIQUE(team_id, user_id)

CHECK(progress >= 0 AND progress <= 100)
```

Use foreign keys.

Do not rely exclusively on application-level validation.

---

# 21. SQLAlchemy Rules

Use SQLAlchemy 2.x style.

Prefer:

```python
class User(Base):
    ...
```

with typed mappings.

Avoid legacy SQLAlchemy APIs.

Do not put business logic inside ORM models.

Business logic belongs in service/use-case layers.

---

# 22. Module Architecture

Every backend module should follow:

```text
module/
├── router.py
├── schemas.py
├── models.py
├── service.py
├── repository.py
└── dependencies.py
```

For example:

```text
tasks/
├── router.py
├── schemas.py
├── models.py
├── service.py
├── repository.py
└── dependencies.py
```

Not every module must contain every file if unnecessary.

Do not create abstractions without a concrete need.

---

# 23. API Structure

All API endpoints use:

```text
/api/v1/
```

Examples:

```text
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh

GET    /api/v1/users/me

GET    /api/v1/organizations/current
PATCH  /api/v1/organizations/current

GET    /api/v1/teams
POST   /api/v1/teams
GET    /api/v1/teams/{id}
PATCH  /api/v1/teams/{id}
DELETE /api/v1/teams/{id}

GET    /api/v1/projects
POST   /api/v1/projects
GET    /api/v1/projects/{id}
PATCH  /api/v1/projects/{id}

GET    /api/v1/tasks
POST   /api/v1/tasks
GET    /api/v1/tasks/{id}
PATCH  /api/v1/tasks/{id}

GET    /api/v1/goals
POST   /api/v1/goals
PATCH  /api/v1/goals/{id}

GET    /api/v1/checkins
POST   /api/v1/checkins
PATCH  /api/v1/checkins/{id}

GET    /api/v1/dashboard
```

---

# 24. API Response Conventions

Successful single resource:

```json
{
  "data": {}
}
```

Collection:

```json
{
  "data": [],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 100
  }
}
```

Errors:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Project not found"
  }
}
```

Do not expose stack traces to clients.

---

# 25. Pagination

All potentially large collections must support pagination.

Use:

```text
page
page_size
```

Default:

```text
page = 1
page_size = 20
```

Maximum:

```text
page_size = 100
```

---

# 26. Filtering and Sorting

Where appropriate:

```text
GET /tasks?status=IN_PROGRESS
GET /tasks?priority=HIGH
GET /tasks?assignee_id=...
GET /projects?status=ACTIVE
```

Sorting should use explicit allowed fields.

Never interpolate arbitrary query parameters into SQL.

---

# 27. Redis

Redis is used for:

1. Caching
2. Rate limiting where useful
3. Future background processing support

Do not cache everything.

Cache only expensive or frequently requested data.

Initial candidates:

```text
dashboard summary
organization summary
```

Cache keys must include organization/user context where relevant.

Example:

```text
dashboard:{organization_id}
```

Use explicit TTLs.

---

# 28. Docker Compose

Required services:

```text
backend
website
panel
postgres
redis
```

Optional development reverse proxy may be added later.

Example architecture:

```text
Browser
   │
   ├── Website
   │
   └── Panel
          │
          ▼
       Backend
        /    \
       /      \
 PostgreSQL   Redis
```

Each service must have its own Dockerfile where appropriate.

Environment configuration must come from environment variables.

Never commit secrets.

---

# 29. Environment Variables

Provide:

```text
DATABASE_URL
REDIS_URL

SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES

POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD

CORS_ORIGINS
```

Use `.env.example`.

Never commit `.env`.

---

# 30. Testing Strategy

Backend:

```text
unit tests
integration tests
API tests
authorization tests
```

Minimum requirement:

Every service/use-case must have tests.

Every API endpoint must have at least one happy-path test.

Every authorization-sensitive endpoint must have:

```text
authorized test
unauthorized test
cross-organization access test
```

---

# 31. Security Requirements

Must implement:

* Password hashing
* Authentication
* Authorization
* Organization isolation
* Input validation
* SQL injection protection through ORM
* CORS configuration
* Secure secret management
* No sensitive data in logs

Never log:

```text
password
password_hash
access_token
refresh_token
authorization header
```

---

# 32. Observability

Every request should have:

```text
request_id
method
path
status_code
duration
```

Application logs should be structured where practical.

Expose:

```text
/health
```

Health endpoint should verify application health.

A deeper readiness endpoint may verify:

```text
PostgreSQL
Redis
```

---

# 33. Frontend Architecture

Use feature-oriented organization.

Example:

```text
src/
├── app/
├── components/
├── features/
│   ├── auth/
│   ├── dashboard/
│   ├── teams/
│   ├── projects/
│   ├── tasks/
│   ├── goals/
│   └── checkins/
├── hooks/
├── lib/
├── services/
├── types/
└── routes/
```

Do not create one enormous `components/` directory.

---

# 34. Frontend State

Use:

* TanStack Query for server state
* React state for local UI state

Do not put server data into a global state manager unless there is a demonstrated need.

---

# 35. UI Principles

The MVP UI should be:

* clean
* professional
* responsive
* desktop-first for the management panel
* accessible
* consistent

The panel should prioritize information density over visual decoration.

The manager should be able to understand team status quickly.

---

# 36. Dashboard

The initial dashboard should show:

```text
Team members
Active projects
Open tasks
Overdue tasks
Goals
Goal progress
Recent check-ins
Recent activity
```

Example:

```text
---------------------------------------------
 Team Overview
---------------------------------------------

 Members        Active Projects
 12             4

 Open Tasks     Overdue
 47             6

---------------------------------------------
 Goals
---------------------------------------------

 Product Launch       ███████░░░ 70%
 Q3 Growth            █████░░░░░ 50%

---------------------------------------------
 Recent Activity
---------------------------------------------
 Ali completed "API redesign"
 Sara submitted weekly check-in
 Reza created a new project
```

---

# 37. Error Handling

Backend exceptions should map to stable error codes.

Examples:

```text
INVALID_CREDENTIALS
UNAUTHORIZED
FORBIDDEN
RESOURCE_NOT_FOUND
VALIDATION_ERROR
RESOURCE_ALREADY_EXISTS
ORGANIZATION_ACCESS_DENIED
```

Frontend should display user-friendly messages.

Do not expose internal exception messages.

---

# 38. Business Logic Rules

Business rules must live in services.

Example:

```text
router
   ↓
service
   ↓
repository
   ↓
database
```

The router should primarily:

* validate request
* authenticate user
* call service
* return response

Do not put complex business logic in routers.

---

# 39. Dependency Injection

Use FastAPI dependency injection for:

```text
database session
current user
organization context
authorization
```

Avoid global mutable state.

---

# 40. Database Transactions

Services own transaction boundaries.

A business operation that changes multiple records should happen inside one transaction.

Example:

Creating an organization:

```text
create organization
create owner membership
```

must be atomic.

---

# 41. API Documentation

FastAPI OpenAPI documentation must remain usable.

Every endpoint should have:

* summary
* description where needed
* request schema
* response schema
* status codes

---

# 42. Code Quality

Required:

```text
ruff
pytest
type checking where practical
```

Code should be:

* readable
* explicit
* boring
* maintainable

Avoid clever code.

Avoid premature abstractions.

Avoid unnecessary design patterns.

---

# 43. AI Agent Rules

AI agents must:

1. Read this specification before modifying code.
2. Read existing code before creating new code.
3. Never silently change architecture.
4. Never introduce a new dependency without justification.
5. Never modify unrelated files.
6. Never delete functionality without explicit approval.
7. Write tests with new functionality.
8. Run relevant tests after changes.
9. Run linting after changes.
10. Explain architectural deviations.
11. Never invent product requirements.
12. Never assume authorization rules.
13. Never bypass organization isolation.
14. Never commit secrets.
15. Prefer simple implementations.

---

# 44. Feature Implementation Rule

Every feature must be implemented vertically.

Example:

```text
Task Management

1. Database model
2. Migration
3. Repository
4. Service
5. Schemas
6. API
7. API tests
8. Frontend API integration
9. Frontend UI
10. Frontend tests
11. End-to-end verification
```

Do not build the entire backend first and frontend later.

---

# 45. Definition of "Implemented"

A feature is not complete when code compiles.

A feature is complete when:

```text
Database
✓

Migration
✓

Backend logic
✓

API
✓

Authorization
✓

Tests
✓

Frontend
✓

Error handling
✓

Loading states
✓

Empty states
✓

Documentation
✓
```

---

# 46. Architecture Decision Rule

When an AI agent encounters ambiguity:

```text
1. Check AI_BUILD_SPEC.md
2. Check docs/
3. Check existing implementation
4. Prefer existing project conventions
5. Choose the simplest solution
6. If the decision changes architecture, STOP and ask
```

Agents must not make major architecture decisions silently.

---

# 47. Phase 1 Success Criteria

The MVP is considered successful when a manager can:

```text
Register
↓
Create organization
↓
Manage members
↓
Create team
↓
Create project
↓
Create tasks
↓
Assign tasks
↓
Track progress
↓
Create goals
↓
Conduct check-ins
↓
View dashboard
```

The complete workflow must work in a fresh Docker Compose environment.

---

# 48. Future Extension Points

The architecture should allow later addition of:

```text
Slack
GitHub
GitLab
Jira
Linear
Google Calendar
Microsoft Teams
AI assistant
AI summaries
Performance management
1:1 meetings
OKRs
Feedback
Analytics
Notifications
Email
Mobile application
Billing
SSO
OAuth
```

Do not implement these now.

---

# 49. Final Principle

The MVP should be:

> Small, coherent, testable, understandable, and deployable.

Do not optimize for maximum feature count.

Optimize for a product that a real engineering manager can use every week.
