import os
import shutil

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Counts and deletes __pycache__ folders, then verifies deletion"

    def handle(self, *args, **kwargs):
        # Path to the project root
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        # Function to count __pycache__ folders
        def count_pycache_folders():
            pycache_count = 0
            for root, dirs, files in os.walk(project_root):
                if "__pycache__" in dirs:
                    pycache_count += 1
            return pycache_count

        # Function to delete __pycache__ folders
        def delete_pycache_folders():
            for root, dirs, files in os.walk(project_root):
                if "__pycache__" in dirs:
                    shutil.rmtree(os.path.join(root, "__pycache__"))

        # Count initial __pycache__ folders
        initial_count = count_pycache_folders()
        self.stdout.write(f"Initial __pycache__ folder count: {initial_count}")

        # Delete __pycache__ folders
        delete_pycache_folders()

        # Count __pycache__ folders after deletion
        final_count = count_pycache_folders()
        self.stdout.write(f"Final __pycache__ folder count: {final_count}")


# Save this file as management/commands/clean_pycache.py in one of your Django apps
