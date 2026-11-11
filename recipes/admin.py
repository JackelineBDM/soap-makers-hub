"""Show recipes and purchases in the admin site."""
from django.contrib import admin

from .models import Category, Recipe, RecipePurchase

admin.site.register(Category)
admin.site.register(Recipe)
admin.site.register(RecipePurchase)
