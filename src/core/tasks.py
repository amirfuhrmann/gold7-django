"""Celery tasks for the core app."""
from celery import shared_task


@shared_task
def ping() -> str:
    """Trivial task to verify the Celery worker is processing jobs."""
    return "pong"
