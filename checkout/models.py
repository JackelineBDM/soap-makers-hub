"""Models for orders. Order rules live here, not in the views."""
from django.contrib.auth.models import User
from django.db import models, transaction
from django.db.models import F
from django.db.models.functions import Greatest

from shop.models import Cart, Product


class Order(models.Model):
    """One purchase made by one customer."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    paid = models.BooleanField(default=False)
    stripe_id = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"

    @classmethod
    def create_from_cart(cls, user, cart_items):
        """Save an unpaid order (and its lines) from the user's cart."""
        with transaction.atomic():
            order = cls.objects.create(
                user=user,
                total=sum(i.quantity * i.product.price for i in cart_items),
            )
            OrderItem.objects.bulk_create([
                OrderItem(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price,
                )
                for item in cart_items
            ])
        return order

    def mark_as_paid(self):
        """Mark paid, reduce stock and empty the cart, exactly once.

        Returns True the first time and False if it was already done, so
        refreshing the success page can never take stock twice.
        """
        with transaction.atomic():
            locked = Order.objects.select_for_update().get(pk=self.pk)
            if locked.paid:
                return False
            for item in locked.items.all():
                Product.objects.filter(pk=item.product_id).update(
                    stock=Greatest(F("stock") - item.quantity, 0)
                )
            Cart.objects.filter(user=locked.user).delete()
            locked.paid = True
            locked.save(update_fields=["paid"])
        self.paid = True
        return True


class OrderItem(models.Model):
    """One product line inside an order, with the price at purchase time."""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def line_total(self):
        """Price multiplied by quantity."""
        return self.price * self.quantity
