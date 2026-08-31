# Quality review (Stage 14)

This document records the Stage 14 review of backend coverage, frontend critical
workflows, security, performance, and a Docker Compose fresh start.

## Backend test coverage

Every business module has API tests covering the happy path, validation, authentication,
authorization, and cross-organization isolation:

| Module | Tests |
| ------ | ----- |
| auth / users | `app/tests/test_auth.py`, `test_security.py` |
| organizations | `app/tests/test_organizations.py` |
| teams | `app/tests/test_teams.py` |
| projects | `app/tests/test_projects.py` |
| tasks | `app/tests/test_tasks.py` |
| goals | `app/tests/test_goals.py` |
| checkins | `app/tests/test_checkins.py` |
| dashboard | `app/tests/test_dashboard.py` |
| notifications | `app/tests/test_notifications.py` |

Supporting tests cover health and request logging, CORS, configuration, Redis, database
and Alembic, and the error envelope.

Stage 14 added coverage for:

- Inactive users presenting a still-valid access token
- Tokens signed with a different secret
- CORS allow-list behaviour
- Pagination `page_size` maximum of 100
- ADMIN role on members, teams, and projects
- Request logs never including passwords, tokens, or authorization headers

Run with coverage:

```bash
cd backend
pytest --cov=app --cov-report=term-missing
```

`fail_under` is configured in `backend/pyproject.toml`.

## Frontend tests

Critical panel workflows (login, dashboard, teams, projects, tasks, goals, check-ins,
settings, and route guards) are covered with Vitest and Testing Library. The public website
covers landing, register, and login validation.

```bash
cd panel && npm test
cd website && npm test
```

## Security review

Findings and the resulting controls:

| Area | Result |
| ---- | ------ |
| Authentication | Email + password. Passwords hashed with Argon2id. Access tokens are JWTs with an `type=access` claim. Inactive users cannot log in or use `/users/me`. |
| Authorization | Enforced in services from membership role. Frontend hiding a control is not treated as authorization. ADMIN coverage is tested for members, teams, and projects. |
| Organization isolation | Organization id is taken from membership, never from the client. Cross-organization access returns 404. |
| Secrets | `.env` is gitignored. `SECRET_KEY` must be at least 32 characters. `.env.example` contains placeholders only. |
| CORS | Explicit origin list from `CORS_ORIGINS`. Credentials are allowed only for those origins. Unlisted origins do not receive `Access-Control-Allow-Origin`. |
| Input validation | Pydantic request schemas. Pagination `page_size` is capped at 100. SQL is parameterized through SQLAlchemy. |
| Logging | Request logs include `request_id`, method, path, status, and duration only. Bodies, query strings, and headers are not logged. Unhandled errors do not expose internals. |

Login brute-force rate limiting is not implemented in Phase 1. Redis is available if it is
added later (`AI_BUILD_SPEC.md` section 27).

## Performance review

| Area | Result |
| ---- | ------ |
| N+1 queries | List and dashboard queries join related rows (members, activity) or use `COUNT` aggregates. They do not iterate and query per row. |
| Dashboard | Aggregates are computed with organization-scoped `COUNT`/`ORDER BY … LIMIT` queries and cached in Redis under `dashboard:{organization_id}` with a 60s TTL. Writes invalidate the cache. |
| Indexes | Besides primary keys, unique constraints, and foreign-key indexes, composite indexes cover dashboard and filter paths: tasks `(organization_id, status)` and `(organization_id, status, due_date)`, projects `(organization_id, status)`, goals and check-ins `(organization_id, updated_at)`, notifications `(user_id, created_at)`. |
| Redis | Used only for the dashboard summary, not as a general cache. |
| Pagination | Collections use `page` / `page_size` with defaults 1 / 20 and a maximum of 100. |

## Docker fresh start

The intended verification is:

```bash
docker compose down -v
docker compose up --build
```

That starts PostgreSQL, Redis, the backend, website, and panel from empty volumes.

The backend entrypoint runs `alembic upgrade head` before uvicorn so a new database is
migrated automatically. The backend service waits for healthy PostgreSQL and Redis.

Docker Desktop was not running in the environment where Stage 14 was implemented, so the
compose commands were not executed live. The entrypoint and Compose configuration are in
place for a local fresh start.
