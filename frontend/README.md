# Frontend

Next.js (App Router) + TypeScript + Tailwind CSS. Every page talks to the
FastAPI backend in `../backend`; there is no other server code here.

## Running it

Needs Node.js 22 and the backend running (see the root README).

```bash
cd frontend
npm ci
npm run dev          # http://localhost:3000
```

The backend address comes from `NEXT_PUBLIC_API_URL` (default
`http://localhost:8000`). It is read when the app is **built**, so set it
before `npm run dev` / `npm run build`, not afterwards:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

The backend must allow the frontend address in `CORS_ORIGINS`.

With Docker, `docker compose up --build` at the repo root starts the
frontend, backend and database together (see the root README).

## Checks

```bash
npx tsc --noEmit     # type check
npm run lint         # eslint
npm run build        # production build (also type checks)
```

## Folders

| Folder                 | What it holds                                              |
|------------------------|------------------------------------------------------------|
| `src/app/(auth)/`      | Pages for logged out users: login, register, password reset |
| `src/app/(app)/`       | Pages for logged in users (dashboard, projects, works, ...) |
| `src/components/ui/`   | Small building blocks: buttons, cards, forms, tables, modal |
| `src/components/<area>/` | Pieces of one area, e.g. `works/PaymentsTab.tsx`         |
| `src/lib/`             | API client, login state, types, formatting, hooks          |

## How things work

**Talking to the API.** Use `api` from `src/lib/api.ts`
(`api.get`, `api.post`, `api.patch`, `api.put`, `api.delete`, `api.upload`,
`api.blob`, `api.text`). It adds the login token, refreshes it when it has
expired and turns `{"detail": ...}` errors into readable messages.

To load data in a page use `useApi`:

```tsx
const works = useApi<Work[]>("/works", { project_id: projectId });
// works.data, works.loading, works.error, works.reload()
```

**Toasts.** Wrap an action in `notify` to show a success or error toast:

```tsx
const saved = await notify(api.post<Project>("/projects", form.values), "Project created");
```

Buttons that only call the API can use `ActionButton`, which also asks for
confirmation when given `confirm="..."`.

**Permissions.** After login the app calls `GET /api/v1/permissions/me`.
Hide anything the user is not allowed to do:

```tsx
const { can } = useAuth();
{can("works.create") && <Button>New work</Button>}

// or
<Can permission="works.create"><Button>New work</Button></Can>
```

The permission codes are listed in `src/lib/permissions.ts` so TypeScript
catches typos. They must match `backend/app/constants/permissions.py`. The
backend checks every permission again, so hiding a button is only for a
cleaner screen, not for security.

**Dropdown values** (roles, work categories, labourer titles) come from
`GET /api/v1/metadata/choices` through `useChoices()`, so they are never
typed twice.

**Forms** use `useForm` from `src/lib/useForm.ts`:
`<Input label="Name" {...form.field("name")} />`.

## Adding a page

1. Create `src/app/(app)/<name>/page.tsx` starting with `"use client";`.
2. Load data with `useApi`, show `Loading`, `ErrorState` and `EmptyState`
   from `components/ui/States.tsx`.
3. Add it to the menu in `src/components/AppShell.tsx`, with a
   `permission` if only some roles should see it.

## Docker

| File              | Used by                    | What it does                                     |
|-------------------|----------------------------|--------------------------------------------------|
| `Dockerfile`      | `docker-compose.yml`       | `npm run dev` with the source mounted (live reload) |
| `Dockerfile.prod` | `docker-compose.prod.yml`  | Builds the app and runs the small standalone server as a non-root user |

`Dockerfile.prod` takes `NEXT_PUBLIC_API_URL` as a build argument;
`docker-compose.prod.yml` sets it to `https://BACKEND_DOMAIN`.
