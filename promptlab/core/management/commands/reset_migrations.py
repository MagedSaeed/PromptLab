import os

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Deletes all migration files for a specified app or all user-created apps and runs makemigrations"

    def add_arguments(self, parser):
        parser.add_argument(
            "app_label",
            nargs="?",
            help="App label of the application to delete migrations for. Use --all for all user-created apps.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Delete migration files for all user-created apps",
        )

    def handle(self, *args, **options):
        app_label = options["app_label"]
        delete_all = options["all"]

        if not app_label and not delete_all:
            raise CommandError("You must specify an app label or use the --all option.")

        if delete_all and app_label:
            raise CommandError("You cannot use both an app label and the --all option.")

        project_root = str(settings.BASE_DIR)

        if delete_all:
            apps_to_process = [
                app.name
                for app in apps.get_app_configs()
                if app.path.startswith(project_root)
            ]
        else:
            if not apps.is_installed(app_label):
                raise CommandError(f"App '{app_label}' is not installed.")
            apps_to_process = [app_label]

        # Ask for confirmation
        confirm = input(
            f"Are you sure you want to delete migrations for the following app(s): {', '.join(apps_to_process)}? (yes/no): "
        )
        if confirm.lower() != "yes":
            self.stdout.write("Operation cancelled.")
            return

        def delete_migration_files(app_label):
            migration_count = 0
            app_path = apps.get_app_config(app_label).path
            migration_dir = os.path.join(app_path, "migrations")
            if os.path.exists(migration_dir):
                for file in os.listdir(migration_dir):
                    if file != "__init__.py" and file.endswith(".py"):
                        os.remove(os.path.join(migration_dir, file))
                        migration_count += 1
            return migration_count

        total_migrations_deleted = 0
        for app in apps_to_process:
            deleted_count = delete_migration_files(app)
            total_migrations_deleted += deleted_count
            self.stdout.write(f"Deleted {deleted_count} migration files for app {app}")

        self.stdout.write(f"Total migration files deleted: {total_migrations_deleted}")

        # Run makemigrations
        self.stdout.write("Running makemigrations...")
        call_command("makemigrations")
