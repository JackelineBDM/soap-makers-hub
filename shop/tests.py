"""Tests for the product pages and the cart."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Cart, Product


class CartTestCase(TestCase):
    """Shared set-up: one customer and one product with 10 in stock."""

    def setUp(self):
        self.user = User.objects.create_user("jackie", password="pass12345")
        self.product = Product.objects.create(
            name="Lavender", description="Calming", price="4.50", stock=10
        )
        self.client.login(username="jackie", password="pass12345")
        self.add_url = reverse("add-to-cart", args=[self.product.pk])


class AddToCartTests(CartTestCase):
    """Adding products to the cart."""

    def test_add_uses_the_quantity_that_was_posted(self):
        self.client.post(self.add_url, {"quantity": 3})
        self.assertEqual(Cart.objects.get(user=self.user).quantity, 3)

    def test_adding_twice_adds_the_quantities_together(self):
        self.client.post(self.add_url, {"quantity": 2})
        self.client.post(self.add_url, {"quantity": 3})
        self.assertEqual(Cart.objects.get(user=self.user).quantity, 5)

    def test_cannot_add_more_than_stock(self):
        self.client.post(self.add_url, {"quantity": 11})
        self.assertFalse(Cart.objects.filter(user=self.user).exists())

    def test_bad_quantities_are_rejected(self):
        for bad in ("0", "-2", "abc", ""):
            self.client.post(self.add_url, {"quantity": bad})
        self.assertFalse(Cart.objects.filter(user=self.user).exists())

    def test_anonymous_user_is_sent_to_login(self):
        self.client.logout()
        response = self.client.post(self.add_url, {"quantity": 1})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_get_request_is_not_allowed(self):
        self.assertEqual(self.client.get(self.add_url).status_code, 405)


class UpdateAndRemoveTests(CartTestCase):
    """Changing and removing cart lines."""

    def setUp(self):
        super().setUp()
        self.item = Cart.objects.create(
            user=self.user, product=self.product, quantity=2
        )

    def test_update_changes_quantity(self):
        url = reverse("update-cart-item", args=[self.item.pk])
        self.client.post(url, {"quantity": 4})
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 4)

    def test_remove_deletes_the_line(self):
        url = reverse("remove-cart-item", args=[self.item.pk])
        self.client.post(url)
        self.assertFalse(Cart.objects.filter(pk=self.item.pk).exists())

    def test_cannot_touch_another_users_cart(self):
        User.objects.create_user("other", password="pass12345")
        self.client.login(username="other", password="pass12345")
        for name in ("update-cart-item", "remove-cart-item"):
            url = reverse(name, args=[self.item.pk])
            response = self.client.post(url, {"quantity": 1})
            self.assertEqual(response.status_code, 302, name)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 2)


class CartPageTests(CartTestCase):
    """The cart page itself."""

    def test_grand_total_is_correct(self):
        Cart.objects.create(user=self.user, product=self.product, quantity=2)
        response = self.client.get(reverse("cart"))
        self.assertEqual(float(response.context["grand_total"]), 9.00)


class PageTests(CartTestCase):
    """Smoke tests: every public page loads and has the right links."""

    def test_pages_load_for_anonymous_visitors(self):
        self.client.logout()
        for name, args in (("home", []), ("product-list", []),
                           ("product-detail", [self.product.pk]),
                           ("recipe-list", []), ("login", []),
                           ("register", [])):
            response = self.client.get(reverse(name, args=args))
            self.assertEqual(response.status_code, 200, name)

    def test_menu_shows_login_links_when_logged_out(self):
        self.client.logout()
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("login"))
        self.assertContains(response, reverse("register"))

    def test_menu_shows_logout_when_logged_in(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Log out")

    def test_message_is_shown_after_adding_to_cart(self):
        response = self.client.post(
            self.add_url, {"quantity": 2}, follow=True
        )
        self.assertContains(response, "added to your cart")
