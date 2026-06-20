from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Invitation
from .models import LoginHistory
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
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
    list_display = ("user", "timestamp", "ip_address")
    search_fields = ("user__email", "ip_address")
    readonly_fields = ("user", "timestamp", "ip_address", "user_agent")
    date_hierarchy = "timestamp"
