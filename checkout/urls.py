"""URLs for checkout."""
from django.urls import path

from . import views

urlpatterns = [
    path("create/", views.create_checkout_session, name="create-checkout"),
    path("success/", views.success, name="checkout-success"),
    path("cancel/", views.cancel, name="checkout-cancel"),
    path("orders/", views.order_history, name="order-history"),
    path("orders/<int:pk>/", views.order_detail, name="order-detail"),
    path("webhook/", views.stripe_webhook, name="stripe-webhook"),
]
