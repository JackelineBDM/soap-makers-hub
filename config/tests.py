"""Tests for project-wide pages."""
from django.test import TestCase

class ErrorPageTests(TestCase):
    """Unknown addresses must not show a raw error."""
    def test_unknown_url_redirects_home(self):
        with self.settings(DEBUG=False, ALLOWED_HOSTS=["testserver"]):
            response = self.client.get("/no-such-page/")
        self.assertRedirects(
            response, "/", fetch_redirect_response=False
        )
