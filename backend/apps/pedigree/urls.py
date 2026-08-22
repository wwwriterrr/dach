from django.urls import path

from . import views

app_name = "pedigree"

urlpatterns = [
    path("dog/<slug:slug>/", views.dog_detail, name="dog-detail"),
]
