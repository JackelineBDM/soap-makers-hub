"""Models for product reviews."""
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from shop.models import Product


class Review(models.Model):
    """A customer's rating and comment about one product."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "user"],
                name="one_review_per_user_per_product",
            )
        ]

    def __str__(self):
        return f"{self.user.username} on {self.product.name}: {self.rating}"

    @property
    def stars(self):
        """Filled and empty stars, for example 4 -> four filled, one empty."""
        return "★" * self.rating + "☆" * (5 - self.rating)
