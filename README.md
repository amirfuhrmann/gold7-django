# Gold7

Django backend with an HTML/JS front end, scaffolded for Docker-based development.

## Stack

- **Python 3.12 / Django 5.1**
- **PostgreSQL 16 + TimescaleDB** (time-series ready)
- **Redis 7 + Celery** (worker + beat) for background and scheduled tasks
- **Django REST Framework** with JWT auth (SimpleJWT) and OpenAPI docs (drf-spectacular)
- **Tailwind CSS v4** for the UI
- **Docker Compose** for local development

## Quick start

```bash
cp .env.example .env
make setup      # build images, start db/redis, run migrations
make up         # start all services
```

Then open:

- App: <http://localhost:7777>
- API docs: <http://localhost:7777/api/v1/docs/>
- Django admin: <http://localhost:7777/admin/>
- Health check: <http://localhost:7777/health/>

A superuser is auto-created on first boot from `DJANGO_SUPERUSER_EMAIL` /
`DJANGO_SUPERUSER_PASSWORD` (defaults: `admin@gold7.local` / `admin`).

## Authentication

- **Login** is by **email or phone number + password** (`core.backends.EmailOrPhoneBackend`).
- **Signup is invitation-only.** Create an invitation and share the acceptance link:

  ```bash
  make bash
  python manage.py invite_user bob@example.com --name "Bob" --role manager
  # prints: Acceptance URL: /account/invite/<token>/
  ```

  Invitations can also be created in the Django admin.

## REST API

Base path: `/api/v1/`

| Endpoint                       | Purpose                                  |
| ------------------------------ | ---------------------------------------- |
| `POST /auth/token/`            | Obtain JWT (send email or phone as `username`) |
| `POST /auth/token/refresh/`    | Refresh access token                     |
| `GET  /auth/me/`               | Current authenticated user               |
| `GET  /users/`                 | User directory (staff only)              |
| `GET  /schema/` · `/docs/`     | OpenAPI schema & Swagger UI              |

## Common commands

```bash
make up / down / restart     # control services
make logs                    # tail all logs
make shell                   # Django shell_plus
make migrate / makemigrations
make test                    # pytest
make css-watch               # rebuild Tailwind on change
make lint / format           # ruff
```

## Versioning & releases

Semantic versioning driven by git tags and conventional commits (see `.commitlintrc.yml`).

```bash
make release-status          # current version + recent tags
make release-patch           # 1.2.3 -> 1.2.4-rc.1
make release-minor           # 1.2.3 -> 1.3.0-rc.1
make release-fix             # bump RC only
make release                 # promote RC -> stable, generate changelog + GitHub release
make deploy                  # PR main -> deploy (CI builds & pushes the container image)
```

`scripts/release.py` computes versions; `scripts/generate_changelog.py` writes
`src/CHANGELOG.md`. The current version lives in the top-level `VERSION` file and
is stamped into the production image at build time.

## Project layout

```
.
├── docker-compose.yml              # local dev (db, redis, web, celery worker + beat)
├── docker-compose.production.yml   # production (pulls pre-built image)
├── Makefile                        # dev + release commands
├── VERSION                         # current semantic version
├── deploy/                         # init-timescaledb.sql, prod env template
├── scripts/                        # release.py, generate_changelog.py
├── .github/workflows/              # commitlint + container build/push
└── src/                            # Django project root
    ├── config/                     # settings (base/local/docker/production/test), urls, celery, wsgi
    ├── core/                       # custom User, email/phone auth, invitations, REST API
    ├── templates/                  # base, home, account/, error pages
    ├── static/                     # css (Tailwind), js, img
    └── tests/                      # pytest suite
```
