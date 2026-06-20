"""Signal handlers for the core app."""
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import LoginHistory


@receiver(user_logged_in)
def record_login(sender, user, request, **kwargs):
    """Record each login and seed the session timezone."""
    if getattr(user, "timezone", ""):
        request.session["django_timezone"] = user.timezone

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")

    LoginHistory.objects.create(
        user=user,
        ip_address=ip,
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
    )
