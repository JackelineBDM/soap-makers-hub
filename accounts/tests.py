"""Tests for registering, logging in and logging out."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class RegisterTests(TestCase):
    """Registration rules."""

    def test_register_creates_user_and_logs_in(self):
        response = self.client.post(reverse("register"), {
            "username": "jackie",
            "email": "jackie@example.com",
            "password1": "S0apmaker!2026",
            "password2": "S0apmaker!2026",
        })
        self.assertRedirects(response, reverse("product-list"))
        self.assertTrue(User.objects.filter(username="jackie").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_duplicate_email_rejected(self):
        User.objects.create_user("a", "a@example.com", "pass12345")
        response = self.client.post(reverse("register"), {
            "username": "b",
            "email": "A@example.com",
            "password1": "S0apmaker!2026",
            "password2": "S0apmaker!2026",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="b").exists())

    def test_logged_in_user_cannot_see_register_or_login(self):
        User.objects.create_user("a", "a@example.com", "pass12345")
        self.client.login(username="a", password="pass12345")
        for name in ("register", "login"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)


class LogoutTests(TestCase):
    """Logging out."""

    def test_logout_post_ends_session(self):
        User.objects.create_user("a", "a@example.com", "pass12345")
        self.client.login(username="a", password="pass12345")
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)
