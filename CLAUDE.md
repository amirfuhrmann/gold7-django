# Gold7

## Project
Django backend with HTML/JS front end. Scaffolded after the helix-django layout.

## Stack
- Python 3.12, Django 5.1, PostgreSQL 16 + TimescaleDB, Redis 7, Celery
- Tailwind CSS v4
- DRF + SimpleJWT (JWT auth), drf-spectacular (OpenAPI)
- Docker Compose for local dev

## Structure
- `src/` — Django project root (manage.py, config/, core/, templates, static)
- `src/config/settings/` — base, local, docker, production, test
- Apps: `core` (custom User, email/phone auth, invitations, REST API)

## Key concepts
- **Auth:** login by email OR phone + password (`core.backends.EmailOrPhoneBackend`).
  `username` is kept as Django's `USERNAME_FIELD` for `createsuperuser`/admin.
- **Signup:** invitation-only (`Invitation` model + `/account/invite/<token>/`).
  Create with `python manage.py invite_user <email>`.
- **Suspension:** `User.suspend()/unsuspend()`; suspended users are denied at the backend.
- **Versioning:** semantic versions via git tags; `VERSION` file + `scripts/release.py`.

## Commands
- `make up` / `make down` — start/stop Docker services
- `make shell` — Django shell_plus
- `make test` — pytest
- `make migrate` / `make makemigrations`
- `make css-build` / `make css-watch` — Tailwind

## Testing
- pytest with `--ds=config.settings.test`
- Run: `docker compose exec web pytest` (or `make test`)

## Code style
- Ruff for lint/format (target py312)
- Single-line imports (isort force-single-line)
- Conventional Commits enforced by commitlint (`.commitlintrc.yml`)
