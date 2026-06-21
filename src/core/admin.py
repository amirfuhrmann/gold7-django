from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Invitation
from .models import LoginHistory
from .models import User


class LoginHistoryInline(admin.TabularInline):
    """Recent login/logout activity shown on a user's admin page."""

    model = LoginHistory
    extra = 0
    can_delete = False
    fields = ("timestamp", "logged_out_at", "ip_address", "user_agent")
    readonly_fields = fields
    ordering = ("-timestamp",)
    verbose_name_plural = "Login history"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [LoginHistoryInline]
    list_display = ("email", "name", "phone", "role", "is_staff", "is_active", "is_suspended")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    search_fields = ("email", "name", "phone", "username")
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("name", "email", "phone", "phone_verified", "profile_picture")}),
        (_("Preferences"), {"fields": ("timezone", "preferred_theme")}),
        (_("Role & permissions"), {
            "fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
        }),
        (_("Suspension"), {"fields": ("suspended_at", "suspended_until", "suspension_reason")}),
        (_("Invitation"), {"fields": ("invited_by", "invitation_sent_at")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "name", "phone", "password1", "password2"),
        }),
    )

    @admin.display(boolean=True, description="Suspended")
    def is_suspended(self, obj):
        return obj.is_suspended


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "role", "is_staff", "invited_by", "created_at", "expires_at", "accepted_at")
    list_filter = ("role", "is_staff")
    search_fields = ("email", "name", "phone")
    readonly_fields = ("token", "created_at", "accepted_at")


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "timestamp", "logged_out_at", "duration_display", "ip_address")
    list_filter = ("timestamp",)
    search_fields = ("user__email", "user__name", "ip_address")
    readonly_fields = ("user", "timestamp", "logged_out_at", "session_key", "ip_address", "user_agent")
    date_hierarchy = "timestamp"

    @admin.display(description="Duration")
    def duration_display(self, obj):
        delta = obj.duration
        if delta is None:
            return "— (active / expired)"
        total = int(delta.total_seconds())
        hours, rem = divmod(total, 3600)
        minutes, seconds = divmod(rem, 60)
        if hours:
            return f"{hours}h {minutes}m"
        if minutes:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False  # view-only audit trail
