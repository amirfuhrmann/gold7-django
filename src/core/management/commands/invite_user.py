"""Create an invitation and print its acceptance URL.

Usage:
    python manage.py invite_user alice@example.com --name "Alice" --role manager --staff
"""
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from core.models import Invitation
from core.models import User


class Command(BaseCommand):
    help = "Create an invitation for a new user (invitation-only signup)."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("--name", default="")
        parser.add_argument("--phone", default="")
        parser.add_argument("--role", default="", choices=["", *dict(User.ROLE_CHOICES)])
        parser.add_argument("--staff", action="store_true", help="Grant staff access on acceptance.")

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError(f"A user with email {email} already exists.")

        invitation = Invitation.objects.create(
            email=email,
            name=options["name"],
            phone=options["phone"],
            role=options["role"],
            is_staff=options["staff"],
        )
        path = f"/account/invite/{invitation.token}/"
        self.stdout.write(self.style.SUCCESS(f"Invitation created for {email}"))
        self.stdout.write(f"Acceptance URL: {path}")
