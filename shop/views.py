from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from .models import Product, Cart

def product_list(request):
    products = Product.objects.all()
    return render(request, "shop/list.html", {"products": products})

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, "shop/detail.html", {"product": product})

@login_required
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product,
        defaults={"quantity": 1},
    )
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    messages.success(request, f"{product.name} added to cart.")
    return redirect("product-detail", pk=product.pk)


@login_required
def cart_view(request):
    items = list(Cart.objects.filter(user=request.user))
    grand_total = 0
    for item in items:
        item.line_total = item.quantity * item.product.price
        grand_total += item.line_total
    return render(request, "shop/cart.html", {"items": items, "grand_total": grand_total})
