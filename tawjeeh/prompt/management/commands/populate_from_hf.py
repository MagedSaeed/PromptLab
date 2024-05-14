import requests
from django.core.management.base import BaseCommand
from prompt.models import Task, Dataset
from rich.progress import Progress


class Command(BaseCommand):
    help = "Populate datasets and tasks from Hugging Face"

    def handle(self, *args, **options):
        # Fetch datasets from Hugging Face
        response = requests.get("https://huggingface.co/api/datasets")
        datasets = response.json()

        tasks_created = 0
        datasets_created = 0

        with Progress() as progress:
            progress_task = progress.add_task(
                "[cyan]Processing datasets...", total=len(datasets)
            )

            # Iterate over datasets and populate the models
            for dataset in datasets:
                tags = dataset.get("tags", [])
                dataset_name = dataset.get("id")
                huggingface_name = dataset_name
                description = dataset.get("description", "")
                huggingface_raw = dataset

                task_categories = []
                for tag in tags:
                    if tag.startswith("task_categories:"):
                        task_names = tag.replace("task_categories:", "").split(",")
                        task_categories.extend(task_names)

                for task_name in task_categories:
                    task_name = task_name.strip()
                    task, created = Task.objects.get_or_create(name=task_name)

                    # Count newly created tasks
                    if created:
                        tasks_created += 1

                    # Create or update the dataset
                    dataset, dataset_created = Dataset.objects.update_or_create(
                        name=dataset_name,
                        defaults={
                            "task": task,
                            "huggingface_name": huggingface_name,
                            "description": description,
                            "huggingface_raw": huggingface_raw,
                        },
                    )

                    # Count newly created datasets
                    if dataset_created:
                        datasets_created += 1

                progress.advance(progress_task)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully populated datasets and tasks from Hugging Face. "
                f"{tasks_created} new tasks created and {datasets_created} new datasets created."
            )
        )
