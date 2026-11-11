"""Show reviews in the admin site."""
from django.contrib import admin

from .models import Review

admin.site.register(Review)
