"""Forms for the core app."""
import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm as DjangoPasswordChangeForm
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


class ProfileForm(forms.ModelForm):
    """Edit ancillary profile details for the signed-in user."""

    class Meta:
        model = User
        fields = ["name", "email", "phone", "timezone", "preferred_theme"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Full name"}),
            "email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "you@example.com"}),
            "phone": forms.TextInput(attrs={"class": "form-input", "type": "tel", "placeholder": "+1 555 0100"}),
            "timezone": forms.Select(attrs={"class": "form-input"}),
            "preferred_theme": forms.Select(attrs={"class": "form-input"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if email and qs.exists():
            raise forms.ValidationError(_("That email address is already in use."))
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if not phone:
            return ""
        if not PHONE_RE.match(normalise_phone(phone)):
            raise forms.ValidationError(_("Enter a valid phone number (7-15 digits, optional + prefix)."))
        qs = User.objects.filter(phone=phone).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_("That phone number is already in use."))
        return phone


class StyledPasswordChangeForm(DjangoPasswordChangeForm):
    """Django's password-change form with form-input styling applied."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-input"})
