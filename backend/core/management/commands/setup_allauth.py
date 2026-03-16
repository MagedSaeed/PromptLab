import os

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from dotenv import load_dotenv


class Command(BaseCommand):
    help = "Adds a Google provider to django-allauth with client key and client secret"

    def handle(self, *args, **kwargs):
        # Load environment variables from .env file
        load_dotenv()

        client_id = os.getenv("GOOGLE_CLIENT_ID", "CLIENT_KEY_HERE")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "CLIENT_SECRET_HERE")

        # Check if the Google provider already exists
        google_provider, created = SocialApp.objects.get_or_create(
            provider="google",
            defaults={
                "name": "Google",
                "client_id": client_id,
                "secret": client_secret,
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS("Google provider created successfully.")
            )
        else:
            self.stdout.write(self.style.WARNING("Google provider already exists."))

        # Check if the Google provider already has any sites associated with it
        if not google_provider.sites.exists():
            site = Site.objects.first()
            if site:
                google_provider.sites.add(site)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Google provider assigned to site: {site.domain}."
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR("No sites found to assign the Google provider.")
                )
        else:
            self.stdout.write(
                self.style.WARNING("Google provider already has associated sites.")
            )
