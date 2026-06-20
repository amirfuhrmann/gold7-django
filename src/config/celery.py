"""Celery configuration for Gold7."""

import os

from celery import Celery
from celery.signals import task_postrun

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("gold7")

# Using a string here means the worker doesn't have to serialize the
# configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@task_postrun.connect
def close_db_connections_after_task(**kwargs):
    """Close stale DB connections after each Celery task."""
    from django.db import close_old_connections

    close_old_connections()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task that prints request information."""
    print(f"Request: {self.request!r}")  # noqa: T201
