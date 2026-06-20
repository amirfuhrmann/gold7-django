import pytest

from core.models import User


@pytest.fixture
def password():
    return "test-pass-12345"


@pytest.fixture
def user(db, password):
    return User.objects.create_user(
        username="alice",
        email="alice@example.com",
        password=password,
        name="Alice",
        phone="+15550100",
    )
