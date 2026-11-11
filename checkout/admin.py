"""Show orders, with their lines, in the admin site."""
from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    """Show an order's lines on the order page."""

    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """List orders with the most useful columns."""

    list_display = ("id", "user", "total", "paid", "created_at")
    list_filter = ("paid",)
    inlines = [OrderItemInline]
