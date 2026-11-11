"""Tests for paying: the order must never be paid unless Stripe says so."""
from types import SimpleNamespace
from unittest.mock import patch

import stripe
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from shop.models import Cart, Product

from .models import Order

CREATE = "stripe.checkout.Session.create"
RETRIEVE = "stripe.checkout.Session.retrieve"
FAKE_SESSION = SimpleNamespace(
    id="cs_test_123", url="https://checkout.stripe.com/pay/cs_test_123"
)


class CheckoutTestCase(TestCase):
    """Shared set-up: a customer with 2 soaps in the cart."""

    def setUp(self):
        self.user = User.objects.create_user("jackie", password="pass12345")
        self.product = Product.objects.create(
            name="Lavender", description="Calming", price="4.50", stock=10
        )
        Cart.objects.create(user=self.user, product=self.product, quantity=2)
        self.client.login(username="jackie", password="pass12345")

    def start_checkout(self):
        """Run the checkout view with Stripe mocked out."""
        with patch(CREATE, return_value=FAKE_SESSION):
            return self.client.post(reverse("create-checkout"))


class StartCheckoutTests(CheckoutTestCase):
    """Creating the Stripe session."""

    def test_creates_unpaid_order_and_redirects_to_stripe(self):
        response = self.start_checkout()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, FAKE_SESSION.url)
        order = Order.objects.get(user=self.user)
        self.assertFalse(order.paid)
        self.assertEqual(order.stripe_id, "cs_test_123")
        self.assertEqual(float(order.total), 9.00)
        self.assertEqual(order.items.count(), 1)

    def test_empty_cart_redirects_back(self):
        Cart.objects.all().delete()
        response = self.start_checkout()
        self.assertRedirects(response, reverse("cart"))
        self.assertEqual(Order.objects.count(), 0)

    def test_stripe_outage_shows_message_and_leaves_no_order(self):
        with patch(CREATE, side_effect=stripe.StripeError("down")):
            response = self.client.post(reverse("create-checkout"))
        self.assertRedirects(response, reverse("cart"))
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(Cart.objects.count(), 1)

    def test_get_is_not_allowed(self):
        response = self.client.get(reverse("create-checkout"))
        self.assertEqual(response.status_code, 405)


class SuccessPageTests(CheckoutTestCase):
    """The success page must not hand out free orders."""

    def setUp(self):
        super().setUp()
        self.start_checkout()
        self.url = reverse("checkout-success") + "?session_id=cs_test_123"

    def test_visiting_success_without_paying_does_nothing(self):
        response = self.client.get(reverse("checkout-success"))
        self.assertRedirects(response, reverse("cart"))
        self.assertFalse(Order.objects.get().paid)
        self.assertEqual(Cart.objects.count(), 1)

    def test_unpaid_session_is_not_marked_paid(self):
        with patch(RETRIEVE, return_value=SimpleNamespace(
                payment_status="unpaid")):
            response = self.client.get(self.url)
        self.assertRedirects(response, reverse("cart"))
        self.assertFalse(Order.objects.get().paid)

    def test_paid_session_completes_the_order(self):
        with patch(RETRIEVE, return_value=SimpleNamespace(
                payment_status="paid")):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Order.objects.get().paid)
        self.assertEqual(Cart.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)

    def test_refreshing_the_page_does_not_take_stock_twice(self):
        with patch(RETRIEVE, return_value=SimpleNamespace(
                payment_status="paid")):
            self.client.get(self.url)
            self.client.get(self.url)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)

    def test_another_user_cannot_use_my_session_id(self):
        User.objects.create_user("other", password="pass12345")
        self.client.login(username="other", password="pass12345")
        with patch(RETRIEVE, return_value=SimpleNamespace(
                payment_status="paid")):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Order.objects.get().paid)

    def test_stripe_error_while_checking_shows_message(self):
        with patch(RETRIEVE, side_effect=stripe.StripeError("down")):
            response = self.client.get(self.url)
        self.assertRedirects(response, reverse("cart"))
        self.assertFalse(Order.objects.get().paid)


class WebhookTests(CheckoutTestCase):
    """Stripe's own message that a payment finished."""

    def setUp(self):
        super().setUp()
        self.start_checkout()
        self.url = reverse("stripe-webhook")

    def test_bad_signature_is_rejected(self):
        response = self.client.post(
            self.url, data="{}", content_type="application/json",
            HTTP_STRIPE_SIGNATURE="not-valid",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.get().paid)

    def test_valid_paid_event_marks_order_paid(self):
        event = {
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_test_123",
                                "payment_status": "paid"}},
        }
        with patch("stripe.Webhook.construct_event", return_value=event):
            response = self.client.post(
                self.url, data="{}", content_type="application/json",
                HTTP_STRIPE_SIGNATURE="ok",
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Order.objects.get().paid)

class OrderHistoryTests(CheckoutTestCase):
    """Customers see their own paid orders and nobody else's."""

    def make_order(self, user, paid=True):
        """Create an order with one line."""
        product = Product.objects.get(pk=self.product.pk)
        order = Order.create_from_cart(
            user, [Cart(user=user, product=product, quantity=1)]
        )
        order.paid = paid
        order.save()
        return order

    def test_history_lists_only_my_paid_orders(self):
        mine = self.make_order(self.user)
        self.make_order(self.user, paid=False)
        other = User.objects.create_user("other", password="pass12345")
        theirs = self.make_order(other)
        response = self.client.get(reverse("order-history"))
        self.assertEqual(list(response.context["orders"]), [mine])
        self.assertNotIn(theirs, response.context["orders"])

    def test_cannot_open_another_users_order(self):
        other = User.objects.create_user("other", password="pass12345")
        theirs = self.make_order(other)
        response = self.client.get(reverse("order-detail", args=[theirs.pk]))
        self.assertEqual(response.status_code, 404)

    def test_can_open_my_own_order(self):
        mine = self.make_order(self.user)
        response = self.client.get(reverse("order-detail", args=[mine.pk]))
        self.assertContains(response, f"Order #{mine.pk}")

    def test_history_needs_login(self):
        self.client.logout()
        response = self.client.get(reverse("order-history"))
        self.assertEqual(response.status_code, 302)
