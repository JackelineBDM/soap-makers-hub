"""Views for paying with Stripe and looking at past orders."""
import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from shop.models import Cart

from .models import Order

stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
@require_POST
def create_checkout_session(request):
    """Save an unpaid order, then send the customer to Stripe to pay."""
    cart_items = list(
        Cart.objects.filter(user=request.user).select_related("product")
    )
    if not cart_items:
        messages.info(request, "Your cart is empty.")
        return redirect("cart")
    for item in cart_items:
        if item.quantity > item.product.stock:
            messages.error(
                request,
                f"Only {item.product.stock} of {item.product.name} left. "
                "Please update your cart.",
            )
            return redirect("cart")

    order = Order.create_from_cart(request.user, cart_items)
    # Prices come from our database, never from the browser
    line_items = [{
        "price_data": {
            "currency": "gbp",
            "product_data": {"name": item.product.name},
            "unit_amount": int(item.product.price * 100),
        },
        "quantity": item.quantity,
    } for item in cart_items]
    success_url = request.build_absolute_uri(reverse("checkout-success"))
    try:
        session = stripe.checkout.Session.create(
            line_items=line_items,
            mode="payment",
            shipping_address_collection={
                "allowed_countries": ["GB", "IE", "US", "CA"]
            },
            # Stripe swaps in the real session id when it redirects back
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.build_absolute_uri(reverse("checkout-cancel")),
            metadata={"order_id": order.pk},
        )
    except stripe.StripeError:
        order.delete()
        messages.error(
            request,
            "Sorry, we could not reach the payment service. "
            "You have not been charged. Please try again in a moment.",
        )
        return redirect("cart")

    order.stripe_id = session.id
    order.save(update_fields=["stripe_id"])
    return redirect(session.url)


@login_required
def success(request):
    """Check with Stripe that the payment really happened, then confirm."""
    session_id = request.GET.get("session_id", "")
    if not session_id:
        messages.warning(request, "No payment was found for that page.")
        return redirect("cart")

    order = get_object_or_404(Order, stripe_id=session_id, user=request.user)
    if not order.paid:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
        except stripe.StripeError:
            messages.error(
                request,
                "We could not confirm your payment just now. "
                "Please check your order history in a few minutes.",
            )
            return redirect("cart")
        if session.payment_status != "paid":
            messages.warning(request, "Your payment has not been completed.")
            return redirect("cart")
        order.mark_as_paid()
        messages.success(request, "Payment received. Thank you!")
    return render(request, "checkout/success.html", {"order": order})


@login_required
def cancel(request):
    """Tell the customer nothing was charged and keep their cart."""
    messages.info(request, "Payment cancelled. Your cart is still saved.")
    return render(request, "checkout/cancel.html")


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Let Stripe tell us about payments even if the customer closes the tab.

    Stripe signs every message. A message without a valid signature is
    rejected, so nobody can fake a payment by calling this URL.
    """
    signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        event = stripe.Webhook.construct_event(
            request.body, signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.SignatureVerificationError):
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        if session.get("payment_status") == "paid":
            order = Order.objects.filter(stripe_id=session["id"]).first()
            if order:
                order.mark_as_paid()
    return HttpResponse(status=200)

@login_required
def order_history(request):
    """List the logged-in customer's paid orders, newest first."""
    orders = Order.objects.filter(user=request.user, paid=True)
    return render(request, "checkout/order_history.html", {"orders": orders})


@login_required
def order_detail(request, pk):
    """Show one of the customer's own paid orders."""
    order = get_object_or_404(Order, pk=pk, user=request.user, paid=True)
    return render(request, "checkout/order_detail.html", {"order": order})
