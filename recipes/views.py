"""Views for reading recipes and paying to unlock premium ones."""
import stripe
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import Recipe, RecipePurchase


def can_read(user, recipe):
    """Free recipes are open to all. Premium ones need a purchase."""
    if not recipe.is_premium or user.is_staff:
        return True
    return (
        user.is_authenticated
        and RecipePurchase.objects.filter(user=user, recipe=recipe).exists()
    )


def recipe_list(request):
    """List every recipe and show which ones are premium."""
    recipes = Recipe.objects.select_related("category")
    unlocked_ids = set()
    if request.user.is_authenticated:
        unlocked_ids = set(
            RecipePurchase.objects.filter(user=request.user)
            .values_list("recipe_id", flat=True)
        )
    return render(request, "recipes/list.html", {
        "recipes": recipes, "unlocked_ids": unlocked_ids,
    })


def recipe_detail(request, pk):
    """Show a recipe, or a teaser if it is premium and not yet bought."""
    recipe = get_object_or_404(Recipe, pk=pk)
    return render(request, "recipes/detail.html", {
        "recipe": recipe, "can_read": can_read(request.user, recipe),
    })


@login_required
@require_POST
def recipe_buy(request, pk):
    """Send the customer to Stripe to pay for a premium recipe."""
    recipe = get_object_or_404(Recipe, pk=pk, is_premium=True)
    if can_read(request.user, recipe):
        messages.info(request, "You already have access to this recipe.")
        return redirect("recipe-detail", pk=recipe.pk)
    if recipe.price <= 0:
        messages.error(request, "This recipe cannot be bought right now.")
        return redirect("recipe-detail", pk=recipe.pk)

    success_url = request.build_absolute_uri(
        reverse("recipe-success", args=[recipe.pk])
    )
    try:
        session = stripe.checkout.Session.create(
            line_items=[{
                "price_data": {
                    "currency": "gbp",
                    "product_data": {"name": recipe.title},
                    "unit_amount": int(recipe.price * 100),
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.build_absolute_uri(
                reverse("recipe-detail", args=[recipe.pk])
            ),
            metadata={"recipe_id": recipe.pk, "user_id": request.user.pk},
        )
    except stripe.StripeError:
        messages.error(
            request,
            "Sorry, we could not reach the payment service. "
            "You have not been charged. Please try again in a moment.",
        )
        return redirect("recipe-detail", pk=recipe.pk)
    return redirect(session.url)


@login_required
def recipe_success(request, pk):
    """Unlock the recipe only if Stripe says this customer paid for it."""
    recipe = get_object_or_404(Recipe, pk=pk, is_premium=True)
    session_id = request.GET.get("session_id", "")
    if not session_id:
        messages.warning(request, "No payment was found for that page.")
        return redirect("recipe-detail", pk=recipe.pk)
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.StripeError:
        messages.error(
            request,
            "We could not confirm your payment just now. "
            "Please try this page again in a few minutes.",
        )
        return redirect("recipe-detail", pk=recipe.pk)

    metadata = session.metadata or {}
    paid_for_this = (
        session.payment_status == "paid"
        and metadata.get("recipe_id") == str(recipe.pk)
        and metadata.get("user_id") == str(request.user.pk)
    )
    if not paid_for_this:
        messages.warning(request, "Your payment has not been completed.")
        return redirect("recipe-detail", pk=recipe.pk)

    RecipePurchase.objects.get_or_create(
        user=request.user, recipe=recipe, defaults={"stripe_id": session_id}
    )
    messages.success(request, "Payment received. Your recipe is unlocked!")
    return redirect("recipe-detail", pk=recipe.pk)
