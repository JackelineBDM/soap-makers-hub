"""URLs for recipes."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.recipe_list, name="recipe-list"),
    path("<int:pk>/", views.recipe_detail, name="recipe-detail"),
    path("<int:pk>/buy/", views.recipe_buy, name="recipe-buy"),
    path("<int:pk>/unlocked/", views.recipe_success, name="recipe-success"),
]
