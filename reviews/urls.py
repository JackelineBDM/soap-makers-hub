"""URLs for product reviews."""
from django.urls import path

from . import views

urlpatterns = [
    path("product/<int:product_pk>/add/", views.review_add,
         name="review-add"),
    path("<int:pk>/edit/", views.review_edit, name="review-edit"),
    path("<int:pk>/delete/", views.review_delete, name="review-delete"),
]
