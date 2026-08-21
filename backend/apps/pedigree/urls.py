from django.urls import path

from . import views

app_name = "pedigree"

urlpatterns = [
    # Временный адрес для показа вёрстки; настоящий будет /dog/<slug>/
    path("dog/sample/", views.sample_dog, name="sample-dog"),
]
