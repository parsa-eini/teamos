# Documentation

Per `AI_BUILD_SPEC.md` section 5 this directory holds:

```text
<<<<<<< Updated upstream
architecture.md    System architecture
database.md        Database model and constraints
api.md             API surface and conventions
=======
quality.md         Coverage, security, and performance review
>>>>>>> Stashed changes
decisions/         Architecture decision records
```

`AI_BUILD_SPEC.md` remains the source of truth for scope, the data model, and the API surface.
It covers the areas that changed most recently:

- Tasks carry several assignees through `task_assignees` (section 16).
- Goals link to teams, owners, and tasks, and derive progress from linked tasks (section 17).
- Check-ins are generalized into meetings with a type enum (section 18).
- Feedback is written about a colleague and read by their management line (section 18.1).
- Organization memberships carry `reports_to_user_id`, which forms the reporting tree
  (section 12).

Further documents are written as the corresponding stages of `IMPLEMENTATION_PLAN.md` are
implemented.
