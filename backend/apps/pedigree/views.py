from django.contrib.postgres.search import TrigramSimilarity
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .models import Coat, Dog, DogTitle, HealthTest, Registration, Sex, Size

PAGE_SIZE = 24


def search_dogs(params):
    """
    Общая выборка для страницы и для JSON: одна логика на оба входа,
    иначе серверная выдача и остров рано или поздно разойдутся.

    Поиск по кличке идёт через триграммы pg_trgm, а не по вхождению
    подстроки. Причина в данных: клички транслитерированы кто во что
    горазд, и «Ludde» против «Lude» обычным LIKE не найдётся.
    """
    qs = Dog.objects.select_related("color", "kennel").order_by("name")

    query = (params.get("q") or "").strip()
    if query:
        qs = (
            qs.annotate(similarity=TrigramSimilarity("name", query))
            .filter(Q(name__icontains=query) | Q(similarity__gt=0.25))
            .order_by("-similarity", "name")
        )

    for field, choices in (("size", Size), ("coat", Coat), ("sex", Sex)):
        value = params.get(field)
        if value in choices.values:
            qs = qs.filter(**{field: value})

    if params.get("has_photo") == "1":
        qs = qs.filter(photos__isnull=False).distinct()
    if params.get("verified") == "1":
        qs = qs.filter(provenance="verified")

    return qs


def serialize_dog(dog):
    """Одна форма записи для JSON-выдачи и для начальных данных острова."""
    return {
        "name": dog.name,
        "url": dog.get_absolute_url(),
        "sex": dog.sex,
        "size": dog.get_size_display(),
        "coat": dog.get_coat_display(),
        "color": dog.color.name if dog.color else "",
        "kennel": dog.kennel.name if dog.kennel else "",
        "born": dog.date_born.isoformat() if dog.date_born else None,
        "verified": dog.provenance == "verified",
    }


def dog_list(request):
    """
    Список собак. Рендерится сервером целиком — на нём держится
    поисковый трафик справочника. Остров подключается поверх готовой
    разметки и только ускоряет фильтрацию.
    """
    qs = search_dogs(request.GET)
    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))

    total = qs.count()
    return render(request, "pedigree/dog_list.html", {
        "page": page,
        "total": total,
        "query": request.GET.get("q", ""),
        # Остров получает готовую выдачу первым же рендером: без этого
        # он мигнёт пустотой, пока сходит за данными.
        "island_props": {
            "endpoint": reverse("pedigree:dog-search-api"),
            "initial": {
                "total": total,
                "page": page.number,
                "pages": page.paginator.num_pages,
                "results": [serialize_dog(d) for d in page],
            },
            "query": request.GET.get("q", ""),
            "filters": {
                "size": request.GET.get("size", ""),
                "coat": request.GET.get("coat", ""),
                "sex": request.GET.get("sex", ""),
            },
            "choices": {
                "size": [{"value": v, "label": l} for v, l in Size.choices],
                "coat": [{"value": v, "label": l} for v, l in Coat.choices],
                "sex": [{"value": v, "label": l} for v, l in Sex.choices if v != "unknown"],
            },
        },
    })


def dog_search_api(request):
    """JSON для острова. Отдаёт то же, что и страница, — та же функция выборки."""
    qs = search_dogs(request.GET)
    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))

    return JsonResponse({
        "total": qs.count(),
        "page": page.number,
        "pages": page.paginator.num_pages,
        "results": [serialize_dog(dog) for dog in page],
    })


def dog_detail(request, slug):
    """Карточка собаки."""
    dog = get_object_or_404(
        Dog.objects.select_related(
            "sire", "dam", "color", "breeder", "breeder__kennel", "owner", "kennel", "litter"
        ).prefetch_related(
            Prefetch("dog_titles", queryset=DogTitle.objects.select_related("title")),
            Prefetch("health_tests", queryset=HealthTest.objects.select_related("disease")),
            Prefetch("registrations", queryset=Registration.objects.all()),
            "photos",
        ),
        slug=slug,
    )

    # Однопомётники: те же родители, но сама собака в список не входит.
    # Опираемся на помёт, а если его нет — на пару родителей: в легаси
    # помёты заведены далеко не у всех.
    siblings = Dog.objects.none()
    if dog.litter_id:
        siblings = Dog.objects.filter(litter_id=dog.litter_id)
    elif dog.sire_id or dog.dam_id:
        siblings = Dog.objects.filter(sire_id=dog.sire_id, dam_id=dog.dam_id)
    siblings = siblings.exclude(pk=dog.pk).order_by("name")

    offspring = Dog.objects.filter(Q(sire=dog) | Q(dam=dog))

    return render(request, "pedigree/dog_detail.html", {
        "dog": dog,
        "siblings": siblings,
        "siblings_stats": siblings.aggregate(
            total=Count("pk"),
            males=Count("pk", filter=Q(sex="male")),
            females=Count("pk", filter=Q(sex="female")),
        ),
        "offspring_total": offspring.count(),
        # Титулы разложены по типам: в легаси под них было три разных поля,
        # и заводчики их не смешивают.
        "show_titles": [t for t in dog.dog_titles.all() if t.title.kind == "show"],
        "field_titles": [t for t in dog.dog_titles.all() if t.title.kind == "field"],
        "other_titles": [t for t in dog.dog_titles.all() if t.title.kind == "other"],
    })
