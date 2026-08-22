from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, render

from .models import Dog, DogTitle, HealthTest, Registration


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
