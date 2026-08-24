from django.urls import path

from . import views

app_name = "pedigree"

urlpatterns = [
    path("dogs/", views.dog_list, name="dog-list"),
    # JSON для острова поиска. Отдельным адресом, а не через DRF:
    # ответ простой, схема своя, тащить сериализаторы незачем.
    path("api/dogs/", views.dog_search_api, name="dog-search-api"),
    path("api/dog/<slug:slug>/pedigree/", views.pedigree_api, name="pedigree-api"),
    path("dog/<slug:slug>/", views.dog_detail, name="dog-detail"),
]
