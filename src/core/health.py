"""Health check endpoint for external monitoring."""
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone
from django.views import View


class HealthCheckView(View):
    """GET /health/ — 200 if healthy, 503 if a core dependency is down.

    Add ?detail=true for per-check status.
    """

    def get(self, request):
        show_detail = request.GET.get("detail", "").lower() == "true"

        checks = {
            "database": self.check_database(),
            "redis": self.check_redis(),
        }
        healthy = all(c["status"] == "ok" for c in checks.values())

        data = {"healthy": healthy, "timestamp": timezone.now().isoformat()}
        if show_detail:
            data["checks"] = checks

        return JsonResponse(data, status=200 if healthy else 503)

    def check_database(self) -> dict:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return {"status": "ok"}
        except Exception as e:  # noqa: BLE001
            return {"status": "error", "message": str(e)}

    def check_redis(self) -> dict:
        try:
            from django_redis import get_redis_connection

            get_redis_connection("default").ping()
            return {"status": "ok"}
        except Exception as e:  # noqa: BLE001
            return {"status": "error", "message": str(e)}
