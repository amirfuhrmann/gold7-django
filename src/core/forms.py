"""Forms for the core app."""
import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _

User = get_user_model()

PHONE_RE = re.compile(r"^\+?\d{7,15}$")


def normalise_phone(value: str) -> str:
    return re.sub(r"[\s\-()\.]", "", value or "")


class AcceptInvitationForm(forms.Form):
    """Set name, optional phone, and a password when accepting an invitation."""

    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Full name"}),
    )
    phone = forms.CharField(
        max_length=20, required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "type": "tel", "placeholder": "+1 555 0100"}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "Choose a password"}),
        min_length=8,
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "Confirm password"}),
    )

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if not phone:
            return ""
        if not PHONE_RE.match(normalise_phone(phone)):
            raise forms.ValidationError(_("Enter a valid phone number (7-15 digits, optional + prefix)."))
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError(_("That phone number is already in use."))
        return phone

    def clean(self):
        cleaned = super().clean()
        pwd = cleaned.get("password")
        confirm = cleaned.get("confirm_password")
        if pwd and confirm and pwd != confirm:
            self.add_error("confirm_password", _("Passwords do not match."))
        if pwd:
            validate_password(pwd)
        return cleaned
