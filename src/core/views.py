from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse


@login_required
def home_view(request):
    """Authenticated dashboard landing page."""
    return render(request, "home.html", {})


def login_view(request):
    """Login by email or phone number + password."""
    if request.user.is_authenticated:
        return redirect("home")

    error = None
    suspended = False

    if request.method == "POST":
        identifier = request.POST.get("identifier", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=identifier, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get("next", "")
            return redirect(next_url) if next_url else redirect("home")

        if getattr(request, "_suspended_user", None):
            suspended = True
            error = "Your account has been suspended."
        else:
            error = "Invalid credentials. Check your email/phone and password."

    return render(request, "account/login.html", {"error": error, "suspended": suspended})


def logout_view(request):
    logout(request)
    return redirect("account:login")


def permission_denied_view(request, exception=None):
    context = {
        "user_role": request.user.role_name if request.user.is_authenticated else None,
        "requested_url": request.path,
    }
    return render(request, "403.html", context, status=403)


def csrf_failure_view(request, reason=""):
    """Redirect anonymous users to login on CSRF failure (expired session)."""
    if not request.user.is_authenticated:
        login_path = reverse(settings.LOGIN_URL)
        return redirect(f"{login_path}?next={request.path}")
    return render(request, "403.html", {"message": "CSRF verification failed."}, status=403)
