"""Общие переменные шаблонов."""

from django.core.cache import cache

from apps.pedigree.models import Dog


def site_stats(request):
    """
    Счётчик собак в шапке. Считается запросом, а не зашит в шаблон:
    зашитое число либо врёт сейчас, либо соврёт потом.

    Кешируем — COUNT(*) на каждый показ любой страницы не нужен.
    """
    total = cache.get("dogs_total")
    if total is None:
        total = Dog.objects.count()
        cache.set("dogs_total", total, 600)
    return {"dogs_total": total}
