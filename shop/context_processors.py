from django.db.models import Sum
from .models import Cart

def cart_count(request):
    if request.user.is_authenticated:
        total = Cart.objects.filter(user=request.user).aggregate(total=Sum("quantity"))["total"] or 0
        return {"cart_count": total}
    return {"cart_count": 0}
