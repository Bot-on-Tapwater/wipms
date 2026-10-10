# Ijenga

Monorepo for the Ijenga works and payments platform.

| Folder      | What it holds                                   |
|-------------|-------------------------------------------------|
| `backend/`  | FastAPI API (see below)                         |
| `frontend/` | Next.js web app (see `frontend/README.md`)      |
| `docs/`     | Design decisions and open questions             |

## Configuration

All secrets and settings are read from a `.env` file through
`backend/app/core/config.py`. Never commit `.env`.

```bash
cp .env.example .env    # then fill in real values
```

`.env.example` lists every setting with a comment. With
`ENVIRONMENT=production` the API refuses to start unless `SECRET_KEY` is at
least 32 characters long.

## Running with Docker

There are two compose files at the root. Both run the frontend, the
backend and PostgreSQL.

| File                      | Use               | Traefik |
|---------------------------|-------------------|---------|
| `docker-compose.yml`      | Local development | No      |
| `docker-compose.prod.yml` | Production        | Yes (HTTPS with Let's Encrypt) |

```bash
# Local: app on http://localhost:3000, API on http://localhost:8000,
# Swagger on http://localhost:8000/docs
docker compose up --build

# Production: set ENVIRONMENT=production, real secrets, BACKEND_DOMAIN,
# FRONTEND_DOMAIN, ACME_EMAIL and CORS_ORIGINS=https://FRONTEND_DOMAIN first
docker compose -f docker-compose.prod.yml up -d --build
```

On start the backend container runs the database migrations
(`alembic upgrade head`) and loads the default role permissions.

In production Traefik sends `FRONTEND_DOMAIN` to the frontend and
`BACKEND_DOMAIN` to the backend, with HTTPS certificates from Let's Encrypt.

Each app has two Dockerfiles:

| App      | Local (`docker-compose.yml`)     | Production (`docker-compose.prod.yml`)        |
|----------|----------------------------------|-----------------------------------------------|
| Backend  | `backend/Dockerfile` (auto reload) | `backend/Dockerfile.prod` (gunicorn, non-root user, `WEB_CONCURRENCY` workers) |
| Frontend | `frontend/Dockerfile` (`npm run dev`, live reload) | `frontend/Dockerfile.prod` (built app, non-root user) |

The frontend reads the backend address (`NEXT_PUBLIC_API_URL`) when it is
built, so rebuild it (`--build`) after changing `BACKEND_DOMAIN`.

> Note: Docker was not available on the machine this was written on, so the
> compose files have not been run yet. The app, migrations and tests were
> checked without Docker (see below).

## Running without Docker

Needs Python 3.12 and a PostgreSQL database. In `.env` point
`DATABASE_URL` at `localhost` instead of the `db` service, e.g.
`postgresql+psycopg://ijenga:password@localhost:5432/ijenga`.

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate            # Windows (Linux/macOS: source .venv/bin/activate)
pip install -r requirements-dev.txt
cp ../.env .env                   # settings are read from the current folder
alembic upgrade head
python -m app.scripts.seed_permissions
uvicorn app.main:app --reload
```

Then start the frontend in a second terminal (needs Node.js 22):

```bash
cd frontend
npm ci
npm run dev                       # http://localhost:3000
```

## First super admin

```bash
python -m app.scripts.create_superuser --email admin@example.com \
    --first-name Jane --last-name Doe --phone 254700000000
```

The password is asked for at the prompt (or read from `SUPERUSER_PASSWORD` in `.env`).
With Docker, prefix the command with `docker compose exec backend`.

## Permissions

Permissions live in the database (`permissions` and `role_permissions`
tables), not in code. The frontend calls `GET /api/v1/permissions/me` after
login and shows or hides buttons, menu items and sections based on the
codes it gets back. The backend still checks every permission itself.

Roles: `super-admin`, `main-contractor`, `contractors-supervisor`,
`consultants-supervisor`, `subcontractor`.

Change them from the command line:

```bash
python -m app.scripts.manage_permissions list
python -m app.scripts.manage_permissions list --role subcontractor
python -m app.scripts.manage_permissions grant subcontractor reports.view
python -m app.scripts.manage_permissions revoke subcontractor reports.view
python -m app.scripts.manage_permissions reset     # back to the defaults
```

or through the API as a super admin:
`POST /api/v1/permissions/roles/{role}/grant` and `/revoke`.

Every permission code and its default roles are listed in
`backend/app/constants/permissions.py`. For example, `projects.view_wallet`
(wallet deposits and payouts) is not given to subcontractors by default.

## Logging in

Login returns an access token and a refresh token. A refresh token can be
used once (`POST /api/v1/auth/refresh` returns a new pair) and
`POST /api/v1/auth/logout` cancels it. Changing or resetting a password
cancels every older token, so other devices are logged out;
`POST /api/v1/auth/change-password` returns a new token pair for the
current device.

## Payments

Payments are mocked (`PAYMENT_PROVIDER=mock`) until the bank API is
available. Set `MOCK_PAYMENT_FAILURE_RATE` (for example `0.2`) to simulate
failed payments. The bank integration will be a new provider class in
`backend/app/services/payment_provider.py`; nothing else needs to change.

## Reports

`GET /api/v1/reports/payments`, `/labourers`, `/works` and `/projects`.
Each takes `format=json|html|pdf`: `html` is a printable page and `pdf` is a
download. Payment reports can be filtered to successful or failed payments.
`POST /api/v1/reports/email` emails a report as a PDF to the logged in user.

## API documentation

Swagger UI is at `/docs` and ReDoc at `/redoc`. All endpoints are under
`/api/v1`.

## Tests and linting

```bash
cd backend
python -m pytest -q     # unit tests on an in-memory SQLite database
flake8                  # style check (settings in backend/.flake8)

cd ../frontend
npx tsc --noEmit        # type check
npm run lint            # eslint
npm run build           # production build
```

## Database migrations

```bash
cd backend
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```
