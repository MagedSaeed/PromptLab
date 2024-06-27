import os

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from prompt.models import Dataset, Task
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn


class Command(BaseCommand):
    help = "Populate datasets and tasks from Hugging Face"

    def add_arguments(self, parser):
        parser.add_argument(
            "--datasets-urls",
            type=str,
            help="Path to the file containing dataset URLs (tab, comma, or newline separated). Path should be passed relative to settings.BASE_DIR/tawjeeh directory. If not provided, datasets will be fetched from Hugging Face.",
        )

    def handle(self, *args, **options):
        file_path = options.get("datasets_urls")
        if file_path:
            file_path = os.path.join(f"{settings.BASE_DIR}/tawjeeh", file_path)

        if file_path and os.path.exists(file_path):
            with open(file_path, "r") as file:
                content = file.read()
                if "\t" in content:
                    delimiter = "\t"
                elif "," in content:
                    delimiter = ","
                else:
                    delimiter = "\n"
                dataset_urls = [line.strip() for line in content.split(delimiter)]
        else:
            self.stdout.write(
                self.style.ERROR("No valid dataset URLs provided or file not found.")
            )
            return

        dataset_info_list = self.extract_dataset_info(dataset_urls)

        tasks_created = 0
        datasets_created = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total} datasets processed"),
        ) as progress:
            progress_task = progress.add_task(
                "[cyan]Processing datasets...", total=len(dataset_info_list)
            )

            # Iterate over dataset URLs and fetch their details
            for author, dataset_name in dataset_info_list:
                # catch the case where the url does not provide the author
                if author == "datasets":
                    response = requests.get(
                        f"https://huggingface.co/api/datasets/{dataset_name}"
                    )
                else:
                    response = requests.get(
                        f"https://huggingface.co/api/datasets/{author}/{dataset_name}"
                    )
                if response.status_code != 200:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Failed to fetch dataset: {author}/{dataset_name}"
                        )
                    )
                    progress.advance(progress_task)
                    continue

                dataset = response.json()
                tags = dataset.get("tags", [])
                if author == "datasets":
                    huggingface_name = dataset_name
                else:
                    huggingface_name = f"{author}/{dataset_name}"
                description = dataset.get("description", "")
                huggingface_raw = dataset

                task_categories = []
                for tag in tags:
                    if tag.startswith("task_categories:"):
                        task_names = tag.replace("task_categories:", "").split(",")
                        task_categories.extend(task_names)

                tasks = []
                for task_name in task_categories:
                    task_name = task_name.strip()
                    task, created = Task.objects.get_or_create(name=task_name)

                    # Count newly created tasks
                    if created:
                        tasks_created += 1

                    tasks.append(task)

                # Create or update the dataset
                dataset, dataset_created = Dataset.objects.update_or_create(
                    name=dataset_name,
                    defaults={
                        "huggingface_name": huggingface_name,
                        "description": description,
                        "huggingface_raw": huggingface_raw,
                    },
                )

                # Add tasks to the dataset
                dataset.tasks.set(tasks)

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

    def extract_dataset_info(self, dataset_urls):
        dataset_info_list = []
        for url in dataset_urls:
            path_parts = url.split("/")
            if len(path_parts) >= 2:
                author = path_parts[-2]
                dataset_name = path_parts[-1]
                dataset_info_list.append((author, dataset_name))
            else:
                self.stdout.write(self.style.ERROR(f"Invalid URL format: {url}"))
        return dataset_info_list

    def fetch_all_datasets(self, max_to_fetch=10_000):
        datasets = []
        url = "https://huggingface.co/api/datasets"
        params = {"limit": 1000, "offset": 0}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.fields[total_datasets]} datasets fetched"),
        ) as progress:
            progress_task = progress.add_task(
                f"[cyan]Fetching datasets (maximum {max_to_fetch} datasets)...",
                total=None,
                total_datasets="0",
            )

            while True:
                response = requests.get(url, params=params)
                if response.status_code != 200:
                    break
                data = response.json()
                if not data:
                    break
                datasets.extend(dataset["id"] for dataset in data)
                if len(datasets) >= max_to_fetch:
                    break
                params["offset"] += params["limit"]
                progress.update(
                    progress_task,
                    advance=params["limit"],
                    total_datasets=str(len(datasets)),
                )

        progress.remove_task(progress_task)
        return datasets
