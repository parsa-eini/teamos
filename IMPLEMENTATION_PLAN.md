# Team Management Product — Phase 1 Implementation Plan

## Stage 0 — Repository Foundation

### Task 0.1 — Initialize repository

Create:

```text
backend/
website/
panel/
docs/
.cursor/rules/
```

Create:

```text
AI_BUILD_SPEC.md
IMPLEMENTATION_PLAN.md
DEFINITION_OF_DONE.md
.env.example
.gitignore
README.md
```

Acceptance criteria:

- Repository structure exists.
- README explains local development.
- No secrets committed.

---

## Stage 1 — Docker Infrastructure

### Task 1.1 — Docker Compose

Create services:

```text
backend
website
panel
postgres
redis
```

Acceptance criteria:

```bash
docker compose up
```

starts the entire development environment.

PostgreSQL must persist data.

Redis must be reachable from backend.

---



## Stage 2 — Backend Foundation



### Task 2.1 — FastAPI application

Implement:

```text
app/main.py
app/core/
app/common/
```

Add:

```text
/health
```

Acceptance:

```text
GET /health
```

returns healthy status.

---



### Task 2.2 — Database

Implement:

- SQLAlchemy engine
- session management
- declarative base
- PostgreSQL connection
- Alembic

Create initial migration infrastructure.

---



### Task 2.3 — Redis

Implement:

- Redis connection
- dependency/helper
- basic get/set abstraction

Do not build a complex caching framework.

---



### Task 2.4 — Error handling

Implement:

- application exceptions
- HTTP exception mapping
- consistent error response format

---



## Stage 3 — Authentication



### Task 3.1 — User model

Implement User.

---



### Task 3.2 — Registration

Implement:

```text
POST /api/v1/auth/register
```

Requirements:

- validate email
- hash password
- prevent duplicate email
- create user

---



### Task 3.3 — Login

Implement:

```text
POST /api/v1/auth/login
```

Return access token.

---



### Task 3.4 — Current user

Implement:

```text
GET /api/v1/users/me
```

---



### Task 3.5 — Authentication tests

Cover:

- registration
- duplicate email
- invalid password
- login
- authenticated request
- unauthenticated request

---



## Stage 4 — Organizations



### Task 4.1 — Organization model

Implement:

- Organization
- OrganizationMembership

---



### Task 4.2 — Organization creation

During registration, allow creation of the user's initial organization.

Create:

```text
organization
owner membership
```

atomically.

---



### Task 4.3 — Organization API

Implement:

```text
GET /api/v1/organizations/current
PATCH /api/v1/organizations/current
```

---



### Task 4.4 — Organization authorization

Verify cross-organization isolation.

---



## Stage 5 — Team Management



### Task 5.1 — Team model

Implement:

- Team
- TeamMembership

---



### Task 5.2 — Team CRUD

Implement:

```text
GET /teams
POST /teams
GET /teams/{id}
PATCH /teams/{id}
DELETE /teams/{id}
```

---



### Task 5.3 — Team members

Implement adding/removing members.

Ensure members belong to the same organization.

---



## Stage 6 — Projects



### Task 6.1 — Project model

Implement Project.

---



### Task 6.2 — Project CRUD

Implement:

```text
GET /projects
POST /projects
GET /projects/{id}
PATCH /projects/{id}
DELETE /projects/{id}
```

---



### Task 6.3 — Project authorization

Only users with appropriate organization/team permissions may modify projects.

---



## Stage 7 — Tasks



### Task 7.1 — Task model

Implement Task.

---



### Task 7.2 — Task CRUD

Implement:

```text
GET /tasks
POST /tasks
GET /tasks/{id}
PATCH /tasks/{id}
DELETE /tasks/{id}
```

---



### Task 7.3 — Assignment

Allow assigning tasks to organization members.

---



### Task 7.4 — Filtering

Support:

```text
status
priority
assignee_id
project_id
```

---



### Task 7.5 — Task tests

Test:

- creation
- assignment
- status changes
- filtering
- authorization
- organization isolation

---



## Stage 8 — Goals



### Task 8.1 — Goal model

Implement Goal.

---



### Task 8.2 — Goal CRUD

Implement creation and modification.

---



### Task 8.3 — Goal progress

Allow progress:

```text
0-100
```

Validate at database and application level.

---



## Stage 9 — Check-ins



### Task 9.1 — Check-in model

Implement CheckIn.

---



### Task 9.2 — Check-in workflow

Implement:

```text
DRAFT
SUBMITTED
REVIEWED
```

workflow.

---



### Task 9.3 — Check-in API

Implement creation, submission, review.

---



## Stage 10 — Dashboard



### Task 10.1 — Dashboard service

Calculate:

```text
member_count
active_projects
open_tasks
overdue_tasks
goal_summary
recent_checkins
recent_activity
```

---



### Task 10.2 — Dashboard API

Implement:

```text
GET /api/v1/dashboard
```

---



### Task 10.3 — Dashboard caching

Use Redis.

Cache only expensive aggregate queries.

Invalidate cache after relevant writes.

---



## Stage 11 — Notifications



### Task 11.1 — Notification model

Implement Notification.

---



### Task 11.2 — Notification API

Implement:

```text
GET /notifications
PATCH /notifications/{id}/read
```

---



## Stage 12 — Panel



### Task 12.1 — React foundation

Implement:

- routing
- API client
- authentication
- layout
- error handling

---



### Task 12.2 — Login

Implement login page.

---



### Task 12.3 — Dashboard

Implement dashboard.

---



### Task 12.4 — Teams

Implement:

- team list
- team details
- members

---



### Task 12.5 — Projects

Implement:

- project list
- project details
- project creation

---



### Task 12.6 — Tasks

Implement:

- task list
- filters
- task creation
- task editing
- assignment

---



### Task 12.7 — Goals

Implement goals UI.

---



### Task 12.8 — Check-ins

Implement check-in workflow UI.

---



### Task 12.9 — Settings

Implement basic organization settings.

---



## Stage 13 — Website



### Task 13.1 — Landing page

Implement:

```text
Hero
Problem
Solution
Features
CTA
Footer
```

---



### Task 13.2 — Authentication pages

Implement:

```text
/login
/register
```

---



## Stage 14 — Quality



### Task 14.1 — Backend test coverage

Review all modules.

---



### Task 14.2 — Frontend tests

Test critical workflows.

---



### Task 14.3 — Security review

Review:

- authentication
- authorization
- organization isolation
- secrets
- CORS
- input validation

---



### Task 14.4 — Performance review

Review:

- N+1 queries
- dashboard queries
- indexes
- Redis usage
- pagination

---



### Task 14.5 — Docker fresh-start test

Verify:

```bash
docker compose down -v
docker compose up --build
```

produces a working application.

---



# Final MVP Workflow

The following must work from start to finish:

```text
Register
    ↓
Create Organization
    ↓
Login
    ↓
Create Team
    ↓
Add Members
    ↓
Create Project
    ↓
Create Tasks
    ↓
Assign Tasks
    ↓
Update Tasks
    ↓
Create Goal
    ↓
Update Goal
    ↓
Submit Check-in
    ↓
Review Check-in
    ↓
Open Dashboard
```

Only after this workflow works should Phase 1 be considered complete.