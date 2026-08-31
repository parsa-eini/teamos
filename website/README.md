# Website

Public-facing application for the team management product.

Stack: React, TypeScript, Vite, React Router, TanStack Query, Tailwind CSS.

## Pages

- `/` landing (hero, problem, solution, features, CTA, footer)
- `/login`
- `/register`
- `/features`
- `/pricing`
- `/about`

Authenticated management functionality belongs in `panel/`, not here. Successful login and
registration redirect to the panel.

## Local development

Copy `.env.example` to `.env` if you run Vite outside Docker.

```bash
npm install
npm run dev
npm test
npm run typecheck
```
