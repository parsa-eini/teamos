# Definition of Done

A feature is NOT considered complete simply because the code works locally.

Every feature must satisfy the following checklist.

## 1. Requirements

* [ ] Requirement is explicitly defined.
* [ ] No product assumptions were invented.
* [ ] Acceptance criteria are satisfied.

## 2. Database

If database changes are required:

* [ ] SQLAlchemy model implemented.
* [ ] Alembic migration created.
* [ ] Foreign keys defined.
* [ ] Required indexes defined.
* [ ] Unique constraints defined.
* [ ] Database constraints added where appropriate.
* [ ] Migration tested.

## 3. Backend

* [ ] Pydantic schemas implemented.
* [ ] Service/use-case implemented.
* [ ] Repository implemented where appropriate.
* [ ] API endpoint implemented.
* [ ] Authentication enforced.
* [ ] Authorization enforced.
* [ ] Organization isolation verified.
* [ ] Error handling implemented.
* [ ] Pagination implemented where required.

## 4. Testing

* [ ] Happy path tested.
* [ ] Validation errors tested.
* [ ] Authentication tested.
* [ ] Authorization tested.
* [ ] Cross-organization access tested.
* [ ] Regression tests added for bugs.

## 5. Frontend

If the feature has UI:

* [ ] API integration implemented.
* [ ] Loading state implemented.
* [ ] Error state implemented.
* [ ] Empty state implemented.
* [ ] Success state implemented.
* [ ] Permission-aware UI implemented.
* [ ] Responsive behavior checked.
* [ ] User-friendly validation implemented.

## 6. Security

* [ ] No secrets committed.
* [ ] No sensitive information logged.
* [ ] User input validated.
* [ ] Authorization cannot be bypassed through API calls.
* [ ] Organization isolation verified.

## 7. Quality

* [ ] Ruff passes.
* [ ] Tests pass.
* [ ] Type checking passes where configured.
* [ ] No obvious N+1 queries.
* [ ] No unnecessary abstractions.
* [ ] No unrelated files modified.

## 8. Documentation

* [ ] API documentation updated if necessary.
* [ ] Architecture documentation updated if necessary.
* [ ] README updated if necessary.

## 9. Final Verification

Run:

```bash
docker compose up --build
```

Then verify:

```text
Application starts
Database connects
Redis connects
Backend responds
Website loads
Panel loads
Authentication works
Critical feature workflow works
Tests pass
```

A feature is DONE only when all applicable items above are satisfied.
