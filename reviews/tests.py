"""Tests for reviews: who can add, edit and delete them."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from shop.models import Product

from .models import Review


class ReviewTestCase(TestCase):
    """Shared set-up: two customers and one product."""

    def setUp(self):
        self.alice = User.objects.create_user("alice", password="pass12345")
        self.bob = User.objects.create_user("bob", password="pass12345")
        self.product = Product.objects.create(
            name="Lavender", description="Calming", price="4.50", stock=10
        )
        self.add_url = reverse("review-add", args=[self.product.pk])
        self.client.login(username="alice", password="pass12345")

    def make_review(self, user=None):
        """Create a saved review for the product."""
        return Review.objects.create(
            product=self.product, user=user or self.alice,
            rating=4, comment="Smells lovely and lasts well.",
        )


class CreateReviewTests(ReviewTestCase):
    """Adding reviews."""

    def test_valid_review_is_saved(self):
        response = self.client.post(
            self.add_url, {"rating": 5, "comment": "Really lovely soap."}
        )
        self.assertRedirects(
            response, reverse("product-detail", args=[self.product.pk])
        )
        review = Review.objects.get()
        self.assertEqual((review.user, review.rating), (self.alice, 5))

    def test_short_comment_is_rejected(self):
        response = self.client.post(
            self.add_url, {"rating": 5, "comment": "Nice"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "at least 10 characters")
        self.assertEqual(Review.objects.count(), 0)

    def test_rating_outside_1_to_5_is_rejected(self):
        for bad in ("0", "6", "abc"):
            self.client.post(
                self.add_url, {"rating": bad, "comment": "A fine long one."}
            )
        self.assertEqual(Review.objects.count(), 0)

    def test_only_one_review_per_user_per_product(self):
        self.make_review()
        self.client.post(
            self.add_url, {"rating": 1, "comment": "Trying to review twice."}
        )
        self.assertEqual(Review.objects.count(), 1)

    def test_anonymous_user_is_sent_to_login(self):
        self.client.logout()
        response = self.client.get(self.add_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)


class EditAndDeleteReviewTests(ReviewTestCase):
    """Changing and deleting reviews, owner only."""

    def setUp(self):
        super().setUp()
        self.review = self.make_review()
        self.edit_url = reverse("review-edit", args=[self.review.pk])
        self.delete_url = reverse("review-delete", args=[self.review.pk])

    def test_owner_can_edit(self):
        self.client.post(
            self.edit_url, {"rating": 2, "comment": "Changed my mind a bit."}
        )
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 2)

    def test_other_user_cannot_edit(self):
        self.client.login(username="bob", password="pass12345")
        response = self.client.post(
            self.edit_url, {"rating": 1, "comment": "Hijacking this review."}
        )
        self.assertContains(response, "not allowed", status_code=403)
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 4)

    def test_other_user_cannot_delete(self):
        self.client.login(username="bob", password="pass12345")
        response = self.client.post(self.delete_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Review.objects.count(), 1)

    def test_delete_asks_first_then_deletes_on_post(self):
        response = self.client.get(self.delete_url)
        self.assertContains(response, "Delete your review?")
        self.assertEqual(Review.objects.count(), 1)
        self.client.post(self.delete_url)
        self.assertEqual(Review.objects.count(), 0)


class ProductPageReviewTests(ReviewTestCase):
    """Reviews appear on the product page straight away."""

    def test_review_and_average_are_shown(self):
        self.make_review(self.alice)
        Review.objects.create(product=self.product, user=self.bob,
                              rating=2, comment="Not for me, sorry.")
        response = self.client.get(
            reverse("product-detail", args=[self.product.pk])
        )
        self.assertContains(response, "Smells lovely")
        self.assertContains(response, "3.0")
