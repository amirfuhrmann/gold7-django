"""Authentication backends for Gold7."""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()


class EmailOrPhoneBackend(ModelBackend):
    """Authenticate by email, phone number, or username + password.

    The single ``username`` argument (as passed by the login form and by
    SimpleJWT's token endpoint) is matched, case-insensitively, against the
    ``username``, ``email``, and ``phone`` fields. Suspended users are denied
    even with valid credentials; the suspended user is stashed on the request
    so the login view can show a tailored message.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return None

        identifier = username.strip()
        try:
            user = User._default_manager.get(
                Q(username__iexact=identifier)
                | Q(email__iexact=identifier)
                | Q(phone=identifier),
            )
        except User.DoesNotExist:
            # Run the default password hasher to reduce timing differences
            # between existing and non-existing users.
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            user = User._default_manager.filter(
                Q(username__iexact=identifier)
                | Q(email__iexact=identifier)
                | Q(phone=identifier),
            ).order_by("id").first()

        if user.is_suspended:
            if request is not None:
                request._suspended_user = user
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
