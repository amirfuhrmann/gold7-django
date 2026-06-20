#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() { echo -e "${GREEN}[entrypoint]${NC} $1"; }
warn() { echo -e "${YELLOW}[entrypoint]${NC} $1"; }

# Wait for PostgreSQL (with timeout)
log "Waiting for PostgreSQL..."
timeout=30
while ! nc -z ${DATABASE_HOST:-db} ${DATABASE_INTERNAL_PORT:-5432} 2>/dev/null; do
  timeout=$((timeout - 1))
  if [ $timeout -le 0 ]; then
    warn "PostgreSQL connection timeout!"
    exit 1
  fi
  sleep 1
done
log "PostgreSQL ready"

# Wait for Redis (with timeout)
log "Waiting for Redis..."
timeout=30
while ! nc -z ${REDIS_HOST:-redis} ${REDIS_INTERNAL_PORT:-6379} 2>/dev/null; do
  timeout=$((timeout - 1))
  if [ $timeout -le 0 ]; then
    warn "Redis connection timeout!"
    exit 1
  fi
  sleep 1
done
log "Redis ready"

# Run migrations (web container only)
if [ "$DJANGO_MIGRATE" = "true" ]; then
  log "Running migrations..."
  python manage.py migrate --noinput

  # Create default superuser if no users exist
  log "Checking for existing users..."
  python manage.py shell -c "
from core.models import User
if not User.objects.exists():
    import os
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@gold7.local')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin')
    username = email.split('@')[0]
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Created superuser: {email}')
else:
    print(f'Users exist ({User.objects.count()}), skipping superuser creation')
"
fi

# Wait for migrations (celery containers)
if [ "$DJANGO_MIGRATE" = "wait" ]; then
  log "Waiting for migrations..."
  migration_timeout=${MIGRATION_WAIT_TIMEOUT:-300}
  migration_elapsed=0
  while true; do
    migration_output=$(python manage.py migrate --check 2>&1) && break
    migration_elapsed=$((migration_elapsed + 3))
    if [ $migration_elapsed -ge $migration_timeout ]; then
      warn "Migration wait timed out after ${migration_timeout}s!"
      warn "Last error: $migration_output"
      exit 1
    fi
    sleep 3
  done
  log "Migrations ready"
fi

# Build Tailwind CSS at startup (dev only — production builds at image build time)
if [ "$DJANGO_BUILD_CSS" = "true" ]; then
  log "Installing Node.js dependencies..."
  npm ci --no-audit --no-fund 2>&1 | tail -1
  log "Building Tailwind CSS..."
  npm run css:build 2>&1 | tail -1
  log "Tailwind CSS ready"
fi

# Run collectstatic at startup (belt-and-suspenders for production)
if [ "$DJANGO_COLLECTSTATIC" = "true" ]; then
  log "Collecting static files..."
  python manage.py collectstatic --noinput 2>&1 | tail -1
  log "Static files ready"
fi

log "Starting: $@"
exec "$@"
