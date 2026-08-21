from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render


def home(request):
    """Временная страница-заглушка. Показывает, что связка Django + Vite жива."""
    return render(request, "core/home.html")


def healthz(request):
    """Проба для docker healthcheck и мониторинга VPS."""
    checks = {"database": "unknown"}
    status = 200
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 — health-check не должен падать сам
        checks["database"] = f"error: {exc.__class__.__name__}"
        status = 503
    return JsonResponse({"status": "ok" if status == 200 else "degraded", "checks": checks}, status=status)
