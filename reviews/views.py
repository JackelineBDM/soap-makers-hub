"""Views for adding, editing and deleting your own reviews."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from shop.models import Product

from .forms import ReviewForm
from .models import Review


def _own_review_or_403(request, pk):
    """Return the review, or refuse if it belongs to someone else."""
    review = get_object_or_404(Review, pk=pk)
    if review.user != request.user:
        raise PermissionDenied
    return review


@login_required
def review_add(request, product_pk):
    """Let a customer review a product once."""
    product = get_object_or_404(Product, pk=product_pk)
    if Review.objects.filter(product=product, user=request.user).exists():
        messages.info(request, "You have already reviewed this soap.")
        return redirect("product-detail", pk=product.pk)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, "Thank you, your review was added.")
            return redirect("product-detail", pk=product.pk)
    else:
        form = ReviewForm()
    return render(request, "reviews/review_form.html", {
        "form": form, "product": product, "heading": "Write a review",
    })


@login_required
def review_edit(request, pk):
    """Let a customer change their own review."""
    review = _own_review_or_403(request, pk)
    if request.method == "POST":
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, "Your review was updated.")
            return redirect("product-detail", pk=review.product.pk)
    else:
        form = ReviewForm(instance=review)
    return render(request, "reviews/review_form.html", {
        "form": form, "product": review.product, "heading": "Edit your review",
    })


@login_required
def review_delete(request, pk):
    """Ask for confirmation, then delete the customer's own review."""
    review = _own_review_or_403(request, pk)
    if request.method == "POST":
        product_pk = review.product.pk
        review.delete()
        messages.success(request, "Your review was deleted.")
        return redirect("product-detail", pk=product_pk)
    return render(request, "reviews/review_confirm_delete.html",
                  {"review": review})
