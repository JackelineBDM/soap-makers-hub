import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import JsonResponse
from shop.models import Cart
from .models import Order, OrderItem

stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def create_checkout_session(request):
    cart_items = Cart.objects.filter(user=request.user)
    if not cart_items.exists():
        return redirect("cart")

    line_items = []
    total = 0
    for item in cart_items:
        line_items.append({
            "price_data": {
                "currency": "gbp",
                "product_data": {"name": item.product.name},
                "unit_amount": int(item.product.price * 100),
            },
            "quantity": item.quantity,
        })
        total += item.quantity * item.product.price

    session = stripe.checkout.Session.create(
        line_items=line_items,
        mode="payment",
        success_url=f"{request.scheme}://{request.get_host()}/checkout/success/",
        cancel_url=f"{request.scheme}://{request.get_host()}/checkout/cancel/",
    )
    return redirect(session.url, code=303)

@login_required
def success(request):
    # Create order and clear cart (simple version)
    cart_items = Cart.objects.filter(user=request.user)
    if cart_items.exists():
        total = sum(item.quantity * item.product.price for item in cart_items)
        order = Order.objects.create(user=request.user, total=total, paid=True)
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,
            )
        cart_items.delete()
    return render(request, "checkout/success.html")

@login_required
def cancel(request):
    return render(request, "checkout/cancel.html")
