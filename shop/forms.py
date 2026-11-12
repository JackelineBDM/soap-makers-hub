"""Forms for the shop app."""
from django import forms


class CartQuantityForm(forms.Form):
    """Checks a quantity typed into an add-to-cart or update form."""

    quantity = forms.IntegerField(min_value=1, max_value=99)
