"""Profile page: edit ancillary details, picture, and change password."""
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

pytestmark = pytest.mark.django_db


def _png_upload(name="avatar.png", size=(20, 20)):
    buf = io.BytesIO()
    Image.new("RGB", size, "red").save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def test_profile_requires_login(client):
    resp = client.get(reverse("core:profile"))
    assert resp.status_code == 302
    assert reverse("account:login") in resp.url


def test_profile_page_loads(client, user):
    client.force_login(user)
    resp = client.get(reverse("core:profile"))
    assert resp.status_code == 200
    assert b"Your details" in resp.content


def test_update_profile_changes_phone_and_name(client, user):
    client.force_login(user)
    resp = client.post(reverse("core:profile"), {
        "update_profile": "1",
        "name": "Alice Updated",
        "email": user.email,
        "phone": "+15559999",
        "timezone": "America/New_York",
        "preferred_theme": "dark",
    })
    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.name == "Alice Updated"
    assert user.phone == "+15559999"
    assert user.timezone == "America/New_York"


def test_duplicate_phone_rejected(client, user, django_user_model):
    other = django_user_model.objects.create_user(
        username="bob", email="bob@example.com", password="x", phone="+15558888",
    )
    client.force_login(user)
    resp = client.post(reverse("core:profile"), {
        "update_profile": "1",
        "name": user.name,
        "email": user.email,
        "phone": other.phone,
        "timezone": user.timezone,
        "preferred_theme": user.preferred_theme,
    })
    assert resp.status_code == 200  # re-rendered with errors
    assert b"already in use" in resp.content
    user.refresh_from_db()
    assert user.phone != other.phone


def test_upload_profile_picture(client, user, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    client.force_login(user)
    resp = client.post(reverse("core:profile"), {
        "update_profile": "1",
        "name": user.name,
        "email": user.email,
        "phone": "",
        "timezone": user.timezone,
        "preferred_theme": user.preferred_theme,
        "profile_picture": _png_upload(),
    })
    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.profile_picture
    assert str(user.uuid) in user.profile_picture.name


def test_reject_non_image_upload(client, user, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    client.force_login(user)
    bad = SimpleUploadedFile("notes.txt", b"not an image", content_type="text/plain")
    resp = client.post(reverse("core:profile"), {
        "update_profile": "1",
        "name": user.name,
        "email": user.email,
        "phone": "",
        "timezone": user.timezone,
        "preferred_theme": user.preferred_theme,
        "profile_picture": bad,
    })
    assert resp.status_code == 200
    user.refresh_from_db()
    assert not user.profile_picture


def test_clear_profile_picture(client, user, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    user.profile_picture = _png_upload()
    user.save()
    assert user.profile_picture

    client.force_login(user)
    resp = client.post(reverse("core:profile"), {
        "update_profile": "1",
        "name": user.name,
        "email": user.email,
        "phone": "",
        "timezone": user.timezone,
        "preferred_theme": user.preferred_theme,
        "clear_profile_picture": "on",
    })
    assert resp.status_code == 302
    user.refresh_from_db()
    assert not user.profile_picture


def test_change_password_keeps_user_logged_in(client, user, password):
    client.force_login(user)
    resp = client.post(reverse("core:profile"), {
        "change_password": "1",
        "old_password": password,
        "new_password1": "brand-new-pass-77",
        "new_password2": "brand-new-pass-77",
    })
    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.check_password("brand-new-pass-77")
    # Still authenticated (session hash was updated).
    assert client.get(reverse("core:profile")).status_code == 200
