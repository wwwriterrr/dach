from django.shortcuts import render

from .sample import SAMPLE_DOG


def sample_dog(request):
    """
    Карточка собаки на образце данных.

    ВРЕМЕННАЯ ВЬЮХА для согласования вёрстки: моделей ещё нет.
    Заменяется на DetailView по слагу, когда схема будет готова.
    """
    return render(request, "pedigree/dog_detail.html", {"dog": SAMPLE_DOG})
