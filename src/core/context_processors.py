"""Template context processors for Gold7."""
from django.conf import settings


def platform_settings(request):
    """Expose branding / version info to all templates."""
    return {
        "PLATFORM_NAME": getattr(settings, "PLATFORM_NAME", "Gold7"),
        "COMPANY_NAME": getattr(settings, "COMPANY_NAME", "Gold7"),
        "APP_VERSION": getattr(settings, "APP_VERSION", "dev"),
        "ENVIRONMENT_NAME": getattr(settings, "ENVIRONMENT_NAME", ""),
        "ADMIN_URL": getattr(settings, "ADMIN_URL", "admin/"),
    }
