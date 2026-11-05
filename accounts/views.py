"""Views for registering new customers."""
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render
from .forms import RegisterForm

def register(request):
    """Create an account and log the new customer straight in."""
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome! Your account is ready.")
            return redirect("product-list")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})