from django.urls import path
from . import views

urlpatterns = [
    path("", views.product_list, name="product-list"),
    path("<int:pk>/", views.product_detail, name="product-detail"),
    path("<int:pk>/add/", views.add_to_cart, name="add-to-cart"),
    path("cart/", views.cart_view, name="cart"),
]
