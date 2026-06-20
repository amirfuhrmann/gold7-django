import uuid
import zoneinfo

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as BaseUserManager
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

VALID_TIMEZONE_PREFIXES = (
    "Africa/", "America/", "Antarctica/", "Arctic/", "Asia/",
    "Atlantic/", "Australia/", "Europe/", "Indian/", "Pacific/",
)


def get_timezone_choices():
    """Return timezone choices compatible with PostgreSQL."""
    zones = [
        tz for tz in zoneinfo.available_timezones()
        if tz.startswith(VALID_TIMEZONE_PREFIXES) or tz == "UTC"
    ]
    return [(tz, tz) for tz in sorted(zones)]


def profile_picture_upload_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    return f"profile_pictures/{instance.uuid}/{instance.uuid}.{ext}"


class UserManager(BaseUserManager):
    """Custom manager — no behavioural change, kept for future overrides."""


class User(AbstractUser):
    """Custom user for Gold7.

    Authenticates by email OR phone number plus a password (see
    ``core.backends.EmailOrPhoneBackend``). ``username`` is retained as the
    Django ``USERNAME_FIELD`` so ``createsuperuser`` and the admin keep
    working, but end users sign in with email or phone.

    A ``role`` CharField is used for regular users; staff/superuser status is
    orthogonal to role.
    """

    objects = UserManager()

    # Single name field (replaces first_name / last_name)
    name = models.CharField(_("Name"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]

    # Email is unique and used as a login identifier.
    email = models.EmailField(_("Email address"), unique=True)

    # Public UUID (safe to expose in URLs / API).
    uuid = models.UUIDField(_("UUID"), default=uuid.uuid4, editable=False, unique=True)

    # Roles
    ROLE_MEMBER = "member"
    ROLE_MANAGER = "manager"
    ROLE_CHOICES = [
        (ROLE_MEMBER, _("Member")),
        (ROLE_MANAGER, _("Manager")),
    ]
    role = models.CharField(
        _("Role"), max_length=30, choices=ROLE_CHOICES, blank=True, default="",
        help_text=_("Role for regular users. Staff/superuser use is_staff/is_superuser."),
    )

    # Contact — phone is a secondary login identifier.
    phone = models.CharField(_("Phone number"), max_length=20, blank=True, default="")
    phone_verified = models.BooleanField(_("Phone verified"), default=False)

    # Profile
    profile_picture = models.ImageField(
        _("Profile picture"), upload_to=profile_picture_upload_path, blank=True, default="",
    )

    # Preferences
    timezone = models.CharField(
        _("Timezone"), max_length=50, blank=True,
        choices=get_timezone_choices, default="UTC",
    )
    THEME_LIGHT = "light"
    THEME_DARK = "dark"
    THEME_SYSTEM = "system"
    THEME_CHOICES = [
        (THEME_LIGHT, _("Light")),
        (THEME_DARK, _("Dark")),
        (THEME_SYSTEM, _("System (auto)")),
    ]
    preferred_theme = models.CharField(
        _("Preferred theme"), max_length=10, choices=THEME_CHOICES, default=THEME_SYSTEM,
    )

    # Invitation tracking
    invitation_sent_at = models.DateTimeField(_("Invitation sent at"), null=True, blank=True)
    invited_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="invited_users", verbose_name=_("Invited by"),
    )

    # Suspension
    suspended_at = models.DateTimeField(_("Suspended at"), null=True, blank=True)
    suspended_until = models.DateTimeField(_("Suspended until"), null=True, blank=True)
    suspension_reason = models.TextField(_("Suspension reason"), blank=True, default="")

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        constraints = [
            models.UniqueConstraint(
                fields=["phone"],
                name="unique_phone_when_set",
                condition=~models.Q(phone=""),
            ),
        ]

    def __str__(self):
        return self.email or self.username

    def get_full_name(self) -> str:
        return self.name.strip() if self.name else ""

    def get_absolute_url(self) -> str:
        return reverse("admin:core_user_change", args=[self.pk])

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old = User.objects.get(pk=self.pk)
                if old.profile_picture and old.profile_picture != self.profile_picture:
                    old.profile_picture.delete(save=False)
            except User.DoesNotExist:
                pass
        super().save(*args, **kwargs)
        if self.profile_picture:
            self._resize_profile_picture()

    def _resize_profile_picture(self, max_size=512):
        from PIL import Image

        try:
            img = Image.open(self.profile_picture.path)
        except FileNotFoundError:
            return
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.LANCZOS)
            img.save(self.profile_picture.path)

    @property
    def role_name(self) -> str | None:
        if self.is_superuser:
            return "Superuser"
        if self.is_staff:
            return "Staff"
        if self.role:
            return self.get_role_display()
        return None

    @property
    def is_suspended(self) -> bool:
        if not self.suspended_at:
            return False
        if self.suspended_until and timezone.now() > self.suspended_until:
            return False
        return True

    def suspend(self, by_user=None, reason: str = "", until=None) -> None:
        self.is_active = False
        self.suspended_at = timezone.now()
        self.suspension_reason = reason
        self.suspended_until = until
        self.save(update_fields=[
            "is_active", "suspended_at", "suspension_reason", "suspended_until",
        ])

    def unsuspend(self) -> None:
        self.is_active = True
        self.suspended_at = None
        self.suspension_reason = ""
        self.suspended_until = None
        self.save(update_fields=[
            "is_active", "suspended_at", "suspension_reason", "suspended_until",
        ])

    @property
    def invitation_status(self) -> str | None:
        if not self.invitation_sent_at:
            return None
        return "accepted" if self.last_login else "invited"


class LoginHistory(models.Model):
    """Records every user login."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="login_history")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "login history"
        verbose_name_plural = "login history"

    def __str__(self):
        return f"{self.user} @ {self.timestamp}"


class Invitation(models.Model):
    """Invitation for a new user to join the platform (invitation-only signup)."""

    email = models.EmailField(_("Email"))
    name = models.CharField(_("Name"), max_length=255, blank=True)
    phone = models.CharField(_("Phone number"), max_length=20, blank=True, default="")
    role = models.CharField(
        _("Role"), max_length=30, choices=User.ROLE_CHOICES, blank=True, default="",
    )
    is_staff = models.BooleanField(_("Staff status"), default=False)
    token = models.UUIDField(_("Token"), default=uuid.uuid4, unique=True, editable=False)
    invited_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sent_invitations", verbose_name=_("Invited by"),
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    expires_at = models.DateTimeField(_("Expires at"))
    accepted_at = models.DateTimeField(_("Accepted at"), null=True, blank=True)

    class Meta:
        verbose_name = _("Invitation")
        verbose_name_plural = _("Invitations")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invitation for {self.email}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            from django.conf import settings
            days = getattr(settings, "INVITATION_EXPIRY_DAYS", 7)
            self.expires_at = timezone.now() + timezone.timedelta(days=days)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_accepted(self):
        return self.accepted_at is not None

    @property
    def is_valid(self):
        return not self.is_expired and not self.is_accepted
