# Gold7 Dockerfile
# Multi-stage build supporting both local development and production.

# =============================================================================
# Stage 1: Python Builder - Install Python dependencies
# =============================================================================
FROM python:3.12-slim-bookworm AS builder

ARG BUILD_ENV=production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements/ /tmp/requirements/
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements/${BUILD_ENV}.txt && \
    rm -rf /tmp/requirements/

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.12-slim-bookworm

ARG BUILD_ENV=production
ARG VERSION=dev

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.docker

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    libjpeg62-turbo \
    libfreetype6 \
    libwebp7 \
    libffi8 \
    curl \
    netcat-traditional \
    procps \
    ca-certificates \
    gnupg && \
    # Install Node.js 20 (Tailwind CSS v4 requires >= 20)
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create app user
RUN groupadd -r -g 1000 django && \
    useradd -r -u 1000 -g django -d /app -s /sbin/nologin django && \
    mkdir -p /app/staticfiles /app/media && \
    chown -R django:django /app

WORKDIR /app

# Copy application code
COPY --chown=django:django . /app/

# Stamp the release version into the image so APP_VERSION reflects the build tag
RUN echo "$VERSION" > /app/VERSION && chown django:django /app/VERSION

# Ensure entrypoint is executable
RUN chmod +x /app/docker-entrypoint.sh

# Production: build Tailwind CSS and collectstatic at image build time
RUN if [ "$BUILD_ENV" = "production" ]; then \
      npm ci --no-audit --no-fund && \
      npm run css:build && \
      rm -rf node_modules && \
      DJANGO_SECRET_KEY=build-placeholder \
      DJANGO_SETTINGS_MODULE=config.settings.production \
      DATABASE_URL=sqlite:///dev/null \
      REDIS_URL=redis://localhost:6379/0 \
      python manage.py collectstatic --noinput; \
    fi

USER django

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command — gunicorn for production, overridden by docker-compose for dev.
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
