# Panel

Authenticated management application for the team management product. This is the primary MVP
application.

Stack: React, TypeScript, Vite, React Router, TanStack Query, Tailwind CSS.

## Pages

- `/login`
- `/dashboard`
- `/organization`
- `/organization/members`
- `/teams`, `/teams/:id`
- `/projects`, `/projects/new`, `/projects/:id`
- `/tasks`
- `/goals`
- `/checkins`
- `/settings`

Registration lives on the public website. After a website login or register, the browser is
sent to `/auth/callback` with the access token in the URL hash.

## Local development

Copy `.env.example` to `.env` if you run Vite outside Docker. The browser calls the backend at
`VITE_API_BASE_URL` (default `http://localhost:8000`).

```bash
npm install
npm run dev
npm test
npm run typecheck
```

Authorization and organization isolation remain server-side. Hidden UI is not a permission check.
