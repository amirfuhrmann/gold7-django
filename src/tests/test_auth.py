"""Auth: email/phone login, invitation flow, and JWT token issuance."""
import pytest
from django.urls import reverse

from core.models import Invitation
from core.models import User

pytestmark = pytest.mark.django_db


def test_login_with_email(client, user, password):
    resp = client.post(reverse("account:login"), {"identifier": user.email, "password": password})
    assert resp.status_code == 302
    assert resp.url == reverse("home")


def test_login_with_phone(client, user, password):
    resp = client.post(reverse("account:login"), {"identifier": user.phone, "password": password})
    assert resp.status_code == 302


def test_login_with_wrong_password(client, user):
    resp = client.post(reverse("account:login"), {"identifier": user.email, "password": "nope"})
    assert resp.status_code == 200
    assert b"Invalid credentials" in resp.content


def test_suspended_user_cannot_login(client, user, password):
    user.suspend(reason="testing")
    resp = client.post(reverse("account:login"), {"identifier": user.email, "password": password})
    assert resp.status_code == 200
    assert b"suspended" in resp.content


def test_jwt_token_with_email(client, user, password):
    resp = client.post(
        reverse("token-obtain"),
        data={"username": user.email, "password": password},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert "access" in resp.json()


def test_invitation_acceptance_creates_user(client):
    invite = Invitation.objects.create(email="bob@example.com", name="Bob", role=User.ROLE_MEMBER)
    url = reverse("account:accept-invitation", kwargs={"token": invite.token})

    resp = client.post(url, {
        "name": "Bob",
        "phone": "+15550111",
        "password": "s3cure-pass-99",
        "confirm_password": "s3cure-pass-99",
    })
    assert resp.status_code == 302
    bob = User.objects.get(email="bob@example.com")
    assert bob.name == "Bob"
    assert bob.role == User.ROLE_MEMBER
    invite.refresh_from_db()
    assert invite.is_accepted


def test_expired_invitation_rejected(client):
    from django.utils import timezone
    invite = Invitation.objects.create(email="late@example.com")
    invite.expires_at = timezone.now() - timezone.timedelta(days=1)
    invite.save(update_fields=["expires_at"])

    url = reverse("account:accept-invitation", kwargs={"token": invite.token})
    resp = client.get(url)
    assert resp.status_code == 410


def test_auth_me_endpoint(client, user, password):
    client.force_login(user)
    resp = client.get(reverse("auth-me"))
    assert resp.status_code == 200
    assert resp.json()["email"] == user.email


def test_health_endpoint(client):
    resp = client.get(reverse("health"))
    assert resp.status_code in (200, 503)
    assert "healthy" in resp.json()
