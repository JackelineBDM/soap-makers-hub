"""Tests for recipes: premium content stays locked until paid."""
from types import SimpleNamespace
from unittest.mock import patch

import stripe
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Recipe, RecipePurchase

CREATE = "stripe.checkout.Session.create"
RETRIEVE = "stripe.checkout.Session.retrieve"
FAKE_SESSION = SimpleNamespace(
    id="cs_test_999", url="https://checkout.stripe.com/pay/cs_test_999"
)


class RecipeTestCase(TestCase):
    """Shared set-up: a free recipe, a premium recipe and a customer."""

    def setUp(self):
        self.user = User.objects.create_user("jackie", password="pass12345")
        self.free = Recipe.objects.create(
            title="Basic Bar", description="Easy", ingredients="FREE-LYE",
            instructions="FREE-STEPS",
        )
        self.premium = Recipe.objects.create(
            title="Luxury Bar", description="Fancy", is_premium=True,
            price="3.00", ingredients="SECRET-OIL",
            instructions="SECRET-STEPS",
        )
        self.client.login(username="jackie", password="pass12345")
        self.detail = reverse("recipe-detail", args=[self.premium.pk])
        self.success = reverse("recipe-success", args=[self.premium.pk])

    def paid_session(self, **changes):
        """A pretend Stripe session that was paid by the test customer."""
        data = {
            "payment_status": "paid",
            "metadata": {"recipe_id": str(self.premium.pk),
                         "user_id": str(self.user.pk)},
        }
        data.update(changes)
        return SimpleNamespace(**data)


class RecipeAccessTests(RecipeTestCase):
    """Who can read what."""

    def test_free_recipe_is_open_to_visitors(self):
        self.client.logout()
        url = reverse("recipe-detail", args=[self.free.pk])
        response = self.client.get(url)
        self.assertContains(response, "FREE-LYE")

    def test_premium_recipe_is_hidden_until_bought(self):
        response = self.client.get(self.detail)
        self.assertNotContains(response, "SECRET-OIL")
        self.assertContains(response, "Unlock for")

    def test_visitor_is_asked_to_log_in(self):
        self.client.logout()
        response = self.client.get(self.detail)
        self.assertNotContains(response, "SECRET-OIL")
        self.assertContains(response, "Log in")

    def test_buyer_can_read_it(self):
        RecipePurchase.objects.create(
            user=self.user, recipe=self.premium, stripe_id="cs_x"
        )
        self.assertContains(self.client.get(self.detail), "SECRET-OIL")

    def test_staff_can_read_it(self):
        self.user.is_staff = True
        self.user.save()
        self.assertContains(self.client.get(self.detail), "SECRET-OIL")


class RecipePaymentTests(RecipeTestCase):
    """Paying to unlock."""

    def test_buy_sends_customer_to_stripe(self):
        with patch(CREATE, return_value=FAKE_SESSION):
            response = self.client.post(
                reverse("recipe-buy", args=[self.premium.pk])
            )
        self.assertEqual(response.url, FAKE_SESSION.url)

    def test_buy_needs_post_and_login(self):
        url = reverse("recipe-buy", args=[self.premium.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.post(url).status_code, 302)

    def test_stripe_outage_is_handled(self):
        with patch(CREATE, side_effect=stripe.StripeError("down")):
            response = self.client.post(
                reverse("recipe-buy", args=[self.premium.pk])
            )
        self.assertRedirects(response, self.detail)

    def test_paid_session_unlocks_the_recipe(self):
        with patch(RETRIEVE, return_value=self.paid_session()):
            self.client.get(self.success + "?session_id=cs_test_999")
        self.assertTrue(RecipePurchase.objects.filter(
            user=self.user, recipe=self.premium).exists())
        self.assertContains(self.client.get(self.detail), "SECRET-OIL")

    def test_visiting_success_without_paying_unlocks_nothing(self):
        self.client.get(self.success)
        self.assertEqual(RecipePurchase.objects.count(), 0)

    def test_unpaid_session_unlocks_nothing(self):
        with patch(RETRIEVE, return_value=self.paid_session(
                payment_status="unpaid")):
            self.client.get(self.success + "?session_id=cs_test_999")
        self.assertEqual(RecipePurchase.objects.count(), 0)

    def test_session_for_another_customer_unlocks_nothing(self):
        other = self.paid_session(metadata={
            "recipe_id": str(self.premium.pk), "user_id": "9999"})
        with patch(RETRIEVE, return_value=other):
            self.client.get(self.success + "?session_id=cs_test_999")
        self.assertEqual(RecipePurchase.objects.count(), 0)

    def test_session_for_a_different_recipe_unlocks_nothing(self):
        other = self.paid_session(metadata={
            "recipe_id": str(self.free.pk), "user_id": str(self.user.pk)})
        with patch(RETRIEVE, return_value=other):
            self.client.get(self.success + "?session_id=cs_test_999")
        self.assertEqual(RecipePurchase.objects.count(), 0)
