from django.urls import path
from . import views

urlpatterns = [
    path("create/", views.create_checkout_session, name="create-checkout"),
    path("success/", views.success, name="checkout-success"),
    path("cancel/", views.cancel, name="checkout-cancel"),
]
