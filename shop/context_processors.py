"""Make the number of cart items available to every page."""
from django.db.models import Sum

from .models import Cart


def cart_count(request):
    """Return how many items the logged-in customer has in the cart."""
    if request.user.is_authenticated:
        total = Cart.objects.filter(user=request.user).aggregate(
            total=Sum("quantity")
        )["total"] or 0
        return {"cart_count": total}
    return {"cart_count": 0}
