"""Signal handlers for the core app."""
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver
from django.utils import timezone

from .models import LoginHistory


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@receiver(user_logged_in)
def record_login(sender, user, request, **kwargs):
    """Open a login-history row and seed the session timezone."""
    if getattr(user, "timezone", ""):
        request.session["django_timezone"] = user.timezone

    LoginHistory.objects.create(
        user=user,
        ip_address=_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        session_key=request.session.session_key or "",
    )


@receiver(user_logged_out)
def record_logout(sender, user, request, **kwargs):
    """Stamp the logout time on the open row for this user's session.

    Only explicit logouts are captured here; sessions that simply expire don't
    fire this signal, so their `logged_out_at` stays null (shown as "active").
    """
    if user is None or request is None:
        return

    session_key = getattr(request.session, "session_key", "") or ""
    rows = LoginHistory.objects.filter(user=user, logged_out_at__isnull=True)
    if session_key:
        rows = rows.filter(session_key=session_key)

    row = rows.order_by("-timestamp").first()
    if row:
        row.logged_out_at = timezone.now()
        row.save(update_fields=["logged_out_at"])
