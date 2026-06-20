"""Invitation acceptance flow (invitation-only signup)."""
from django.contrib.auth import get_user_model
from django.contrib.auth import login
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import timezone

from .forms import AcceptInvitationForm
from .models import Invitation

User = get_user_model()


def accept_invitation_view(request, token):
    """Let an invited person set their details and password, creating a user."""
    invitation = get_object_or_404(Invitation, token=token)

    if not invitation.is_valid:
        reason = "expired" if invitation.is_expired else "already accepted"
        return render(request, "account/invitation_invalid.html", {"reason": reason}, status=410)

    if request.method == "POST":
        form = AcceptInvitationForm(request.POST)
        if form.is_valid():
            username = invitation.email.split("@")[0]
            # Ensure a unique username derived from the email local-part.
            base, n = username, 1
            while User.objects.filter(username=username).exists():
                n += 1
                username = f"{base}{n}"

            user = User(
                username=username,
                email=invitation.email,
                name=form.cleaned_data["name"],
                phone=form.cleaned_data["phone"],
                role=invitation.role,
                is_staff=invitation.is_staff,
                invited_by=invitation.invited_by,
            )
            user.set_password(form.cleaned_data["password"])
            user.save()

            invitation.accepted_at = timezone.now()
            invitation.save(update_fields=["accepted_at"])

            login(request, user, backend="core.backends.EmailOrPhoneBackend")
            return redirect("home")
    else:
        form = AcceptInvitationForm(initial={"name": invitation.name})

    return render(request, "account/accept_invitation.html", {"form": form, "invitation": invitation})
