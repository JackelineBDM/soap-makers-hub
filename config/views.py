"""Project-wide error views."""
from django.contrib import messages
from django.shortcuts import redirect

def page_not_found(request, exception):
    """Send visitors home with a friendly message instead of a 404."""
    messages.info(request, "Sorry, that page does not exist.")
    return redirect("home")
