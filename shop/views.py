"""Views for browsing products and managing the cart."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import CartQuantityForm
from .models import Cart, Product

def product_list(request):
    """Show every product."""
    products = Product.objects.all()
    return render(request, "shop/list.html", {"products": products})

def product_detail(request, pk):
    """Show one product with its reviews."""
    product = get_object_or_404(Product, pk=pk)
    reviews = product.reviews.select_related("user")
    average = reviews.aggregate(Avg("rating"))["rating__avg"]
    user_review = None
    if request.user.is_authenticated:
        user_review = reviews.filter(user=request.user).first()
    return render(request, "shop/detail.html", {
        "product": product,
        "reviews": reviews,
        "average_rating": average,
        "user_review": user_review,
    })

@login_required
@require_POST
def add_to_cart(request, pk):
    """Add the chosen quantity of a product to the user's cart."""
    product = get_object_or_404(Product, pk=pk)
    form = CartQuantityForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please choose a quantity from 1 to 99.")
        return redirect("product-detail", pk=product.pk)
    cart_item, _ = Cart.objects.get_or_create(
        user=request.user, product=product, defaults={"quantity": 0}
    )
    new_quantity = cart_item.quantity + form.cleaned_data["quantity"]
    if new_quantity > product.stock:
        messages.error(
            request, f"Sorry, only {product.stock} of {product.name} left."
        )
        if cart_item.quantity == 0:
            cart_item.delete()
        return redirect("product-detail", pk=product.pk)
    cart_item.quantity = new_quantity
    cart_item.save()
    messages.success(
        request, f"{form.cleaned_data['quantity']} x {product.name} "
                 "added to your cart."
    )
    return redirect("cart")

@login_required
def cart_view(request):
    """Show the user's cart with line totals and a grand total."""
    items = list(
        Cart.objects.filter(user=request.user).select_related("product")
    )
    grand_total = 0
    for item in items:
        item.line_total = item.quantity * item.product.price
        grand_total += item.line_total
    return render(
        request, "shop/cart.html",
        {"items": items, "grand_total": grand_total},
    )

@login_required
@require_POST
def update_cart_item(request, pk):
    """Change the quantity of one of the user's own cart lines."""
    try:
        item = Cart.objects.get(pk=pk)
    except Cart.DoesNotExist:
        raise Http404
    if item.user != request.user:
        raise Http404
    form = CartQuantityForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please choose a quantity from 1 to 99.")
    elif form.cleaned_data["quantity"] > item.product.stock:
        messages.error(
            request, f"Sorry, only {item.product.stock} in stock."
        )
    else:
        item.quantity = form.cleaned_data["quantity"]
        item.save()
        messages.success(request, "Cart updated.")
    return redirect("cart")

@login_required
@require_POST
def remove_cart_item(request, pk):
    """Remove one of the user's own cart lines."""
    try:
        item = Cart.objects.get(pk=pk)
    except Cart.DoesNotExist:
        raise Http404
    if item.user != request.user:
        raise Http404
    item.delete()
    messages.success(request, f"{item.product.name} removed from your cart.")
    return redirect("cart")
