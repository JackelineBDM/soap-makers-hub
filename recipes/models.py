"""Models for recipes, their categories and premium purchases."""
from django.contrib.auth.models import User
from django.db import models


class Category(models.Model):
    """A group of recipes, such as 'Beginner' or 'Gift ideas'."""

    name = models.CharField(max_length=100, unique=True)
    friendly_name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """A soap recipe. Premium recipes must be paid for to read."""

    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    ingredients = models.TextField()
    instructions = models.TextField()
    is_premium = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    image = models.ImageField(upload_to="recipes/", blank=True, null=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class RecipePurchase(models.Model):
    """Records that a customer paid to unlock one premium recipe."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="recipe_purchases"
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.PROTECT, related_name="purchases"
    )
    stripe_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"], name="one_purchase_per_recipe"
            )
        ]

    def __str__(self):
        return f"{self.user.username} unlocked {self.recipe.title}"
