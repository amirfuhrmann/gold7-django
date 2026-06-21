"""Login history: a row per session with login and logout times."""
import pytest
from django.urls import reverse

from core.models import LoginHistory

pytestmark = pytest.mark.django_db


def test_login_creates_open_history_row(client, user, password):
    client.post(reverse("account:login"), {"identifier": user.email, "password": password})
    row = LoginHistory.objects.filter(user=user).latest("timestamp")
    assert row.logged_out_at is None
    assert row.is_active
    assert row.session_key  # captured for pairing the logout


def test_logout_stamps_logout_time(client, user, password):
    client.post(reverse("account:login"), {"identifier": user.email, "password": password})
    client.get(reverse("account:logout"))

    row = LoginHistory.objects.filter(user=user).latest("timestamp")
    assert row.logged_out_at is not None
    assert not row.is_active
    assert row.duration is not None
    assert row.duration.total_seconds() >= 0


def test_each_login_is_a_separate_row(client, user, password):
    # First session: log in then out.
    client.post(reverse("account:login"), {"identifier": user.email, "password": password})
    client.get(reverse("account:logout"))
    # Second session.
    client.post(reverse("account:login"), {"identifier": user.email, "password": password})

    rows = LoginHistory.objects.filter(user=user).order_by("timestamp")
    assert rows.count() == 2
    assert rows[0].logged_out_at is not None   # first session closed
    assert rows[1].logged_out_at is None       # second still open
