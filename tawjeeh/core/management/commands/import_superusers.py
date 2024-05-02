import os
import yaml
from dotenv import load_dotenv

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

load_dotenv()


class Command(BaseCommand):
    help = "Import superusers from a YAML file"

    def add_arguments(self, parser):
        parser.add_argument(
            "file",
            type=str,
            help="YAML file containing superuser data",
        )

    def handle(self, *args, **kwargs):
        file_path = kwargs["file"]
        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)
                for admin in data["admins"]:
                    username = admin["username"]
                    email = admin["email"]
                    if not User.objects.filter(username=username).exists():
                        superuser = User.objects.create_superuser(
                            username=username, email=email
                        )
                        superuser.set_password(os.getenv("SUPERUSER_PASSWORD"))
                        superuser.save()
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Superuser {username} created successfully"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"Superuser {username} already exists")
                        )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
