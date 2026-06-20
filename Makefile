.PHONY: help setup build up down restart stop logs logs-web logs-celery logs-beat shell bash dbshell \
        migrate makemigrations createsuperuser collectstatic test check lint format \
        celery-purge celery-status clean clean-all css-build css-watch css-dev css-install \
        release-patch release-fix release-minor release release-status deploy _release-guard

# Default target
help:
	@echo "Gold7 Docker Commands"
	@echo "====================="
	@echo ""
	@echo "Setup:"
	@echo "  make setup          - Initial setup (build, migrate)"
	@echo "  make build          - Build Docker images"
	@echo ""
	@echo "Control:"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo ""
	@echo "Development:"
	@echo "  make logs           - View logs (all services)"
	@echo "  make logs-web       - View web container logs"
	@echo "  make logs-celery    - View celery worker logs"
	@echo "  make shell          - Django shell"
	@echo "  make bash           - Bash shell in web container"
	@echo ""
	@echo "Database:"
	@echo "  make migrate        - Run database migrations"
	@echo "  make makemigrations - Create new migrations"
	@echo "  make createsuperuser - Create Django superuser"
	@echo "  make dbshell        - PostgreSQL shell"
	@echo ""
	@echo "Django:"
	@echo "  make collectstatic  - Collect static files"
	@echo "  make test           - Run tests"
	@echo "  make check          - Run Django checks"
	@echo ""
	@echo "Frontend (Tailwind CSS):"
	@echo "  make css-build      - Build Tailwind CSS (production, minified)"
	@echo "  make css-watch      - Watch and rebuild CSS on changes"
	@echo ""
	@echo "Release:"
	@echo "  make release-patch  - Create patch RC tag (1.2.3 -> 1.2.4-rc.1)"
	@echo "  make release-fix    - Increment RC only  (1.2.4-rc.1 -> 1.2.4-rc.2)"
	@echo "  make release-minor  - Create minor RC tag (1.2.3 -> 1.3.0-rc.1)"
	@echo "  make release        - Promote RC to stable release"
	@echo "  make release-status - Show current version and recent tags"
	@echo "  make deploy         - Create PR: main -> deploy (triggers container builds)"

# Setup
setup:
	docker compose build
	docker compose up -d db redis
	@echo "Waiting for database..."
	@sleep 5
	docker compose run --rm web python manage.py migrate
	@echo "Setup complete! Run 'make up' to start all services"

build:
	docker compose build

# Control
up:
	docker compose up -d
	@echo "Services started"
	@echo "Web: http://localhost:7777"

down:
	docker compose down

restart:
	docker compose restart

stop:
	docker compose stop

# Logs
logs:
	docker compose logs -f

logs-web:
	docker compose logs -f web

logs-celery:
	docker compose logs -f celery_worker

logs-beat:
	docker compose logs -f celery_beat

# Shell access
shell:
	docker compose exec web python manage.py shell_plus

bash:
	docker compose exec web bash

dbshell:
	docker compose exec db psql -U gold7 -d gold7

# Database
migrate:
	docker compose exec web python manage.py migrate

makemigrations:
	docker compose exec web python manage.py makemigrations

createsuperuser:
	docker compose exec web python manage.py createsuperuser

# Django commands
collectstatic:
	docker compose exec web python manage.py collectstatic --noinput

test:
	docker compose exec web pytest

check:
	docker compose exec web python manage.py check

# Code quality
lint:
	docker compose exec web ruff check .

format:
	docker compose exec web ruff format .

# Celery
celery-purge:
	docker compose exec celery_worker celery -A config purge

celery-status:
	docker compose exec celery_worker celery -A config inspect active

# Cleanup
clean:
	docker compose down -v
	@echo "Containers and volumes removed"

clean-all:
	docker compose down -v --rmi all
	@echo "Everything removed (containers, volumes, images)"

# Frontend (Tailwind CSS) - runs in Docker
css-build:
	@echo "Building Tailwind CSS (production - minified)..."
	docker compose exec web npm run css:build

css-watch:
	@echo "Starting Tailwind CSS watch mode..."
	docker compose exec web npm run css:watch

css-dev:
	@echo "Building Tailwind CSS (development)..."
	docker compose exec web npm run css:dev

css-install:
	@echo "Installing Node.js dependencies..."
	docker compose exec web npm ci --no-audit --no-fund

# =============================================================================
# Release Management (semantic versioning via git tags)
# =============================================================================

_release-guard:
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo ""; \
		echo "ERROR: Working tree is dirty. Commit or stash changes first."; \
		echo ""; \
		git status --short; \
		exit 1; \
	fi
	@git fetch origin main --tags --force
	@LOCAL_HEAD=$$(git rev-parse HEAD); \
	ORIGIN_MAIN=$$(git rev-parse origin/main); \
	if [ "$$LOCAL_HEAD" != "$$ORIGIN_MAIN" ]; then \
		echo ""; \
		echo "ERROR: Local HEAD is not in sync with origin/main"; \
		echo "  Local HEAD:  $$LOCAL_HEAD"; \
		echo "  origin/main: $$ORIGIN_MAIN"; \
		exit 1; \
	fi

release-patch: _release-guard
	@echo "Creating PATCH version tag..."
	@VERSION=$$(python scripts/release.py --rc --bump-patch) || exit 1; \
	TAG="v$$VERSION"; \
	python scripts/generate_changelog.py --version "$$VERSION" --ref HEAD && \
	git add src/CHANGELOG.md && \
	git commit -m "docs: update changelog for v$$VERSION" && \
	git push origin main; \
	git tag -a "$$TAG" -m "Release $$VERSION" && git push origin "$$TAG" && \
	echo "Tag $$TAG pushed"

release-fix: _release-guard
	@echo "Creating FIX version tag (RC increment only)..."
	@VERSION=$$(python scripts/release.py --rc --rc-only) || exit 1; \
	TAG="v$$VERSION"; \
	python scripts/generate_changelog.py --version "$$VERSION" --ref HEAD && \
	git add src/CHANGELOG.md && \
	git commit -m "docs: update changelog for v$$VERSION" && \
	git push origin main; \
	git tag -a "$$TAG" -m "Release $$VERSION" && git push origin "$$TAG" && \
	echo "Tag $$TAG pushed"

release-minor: _release-guard
	@echo "Creating MINOR version tag..."
	@VERSION=$$(python scripts/release.py --rc --bump-minor) || exit 1; \
	TAG="v$$VERSION"; \
	python scripts/generate_changelog.py --version "$$VERSION" --ref HEAD && \
	git add src/CHANGELOG.md && \
	git commit -m "docs: update changelog for v$$VERSION" && \
	git push origin main; \
	git tag -a "$$TAG" -m "Release $$VERSION" && git push origin "$$TAG" && \
	echo "Tag $$TAG pushed"

release: _release-guard
	@echo "Promoting RC to stable release..."
	@VERSION=$$(python scripts/release.py --release) || exit 1; \
	TAG="v$$VERSION"; \
	python scripts/generate_changelog.py --version "$$VERSION" || exit 1; \
	git add src/CHANGELOG.md && \
	git commit -m "docs: update changelog for v$$VERSION" && \
	git push origin main; \
	git tag -a "$$TAG" -m "Release $$VERSION" && git push origin "$$TAG" && \
	echo "Tag $$TAG pushed"; \
	if command -v gh >/dev/null 2>&1; then \
		gh release create "$$TAG" --title "$$VERSION" --notes-file RELEASE_NOTES.md && rm -f RELEASE_NOTES.md; \
	fi

release-status:
	@git fetch origin main --tags --force 2>/dev/null
	@echo "Latest tag:   $$(git tag -l 'v*' --sort=-v:refname | head -1 || echo 'none')"
	@echo ""
	@echo "Recent tags:"
	@git tag -l 'v*' --sort=-v:refname | head -5

deploy:
	@echo "Creating PR to promote main -> deploy (container builds)..."
	@git fetch origin main deploy --tags --force 2>/dev/null || { echo "ERROR: Could not fetch origin/deploy. Does the 'deploy' branch exist?"; exit 1; }
	@gh pr create --base deploy --head main \
		--title "chore(deploy): build containers" \
		--body "Promotes main to deploy, triggering container image builds." \
		|| echo "PR may already exist. Check: gh pr list --base deploy"
