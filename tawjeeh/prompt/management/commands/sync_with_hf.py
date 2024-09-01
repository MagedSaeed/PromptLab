import argparse
import ast
import csv
import os
from typing import List, Optional, Tuple

import pandas as pd
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from prompt.models import Dataset, Prompt, Task
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn


def str2bool(value: str) -> bool:
    if isinstance(value, bool):
        return value
    if value.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif value.lower() in ("no", "false", "f", "n", "0"):
        return False
    raise argparse.ArgumentTypeError("Boolean value expected.")


class Command(BaseCommand):
    help = "Populate datasets and tasks from Hugging Face or CSV file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--datasets_file",
            type=str,
            default="./datasets.csv",
            help="Path to the CSV file containing dataset URLs and primary tasks.",
        )
        parser.add_argument(
            "--sheet_id",
            type=str,
            help="ID of the Google Sheet containing dataset URLs and primary tasks.",
        )
        parser.add_argument(
            "--sheet_name", type=str, help="Name of the sheet in the Google Sheet."
        )
        parser.add_argument(
            "--link_column",
            type=str,
            default="link",
            help="Name of the column containing dataset URLs.",
        )
        parser.add_argument(
            "--task_column",
            type=str,
            default="task_name",
            help="Name of the column containing dataset primary tasks.",
        )
        parser.add_argument(
            "--example_template_column",
            type=str,
            default="",
            help="Column name for example template.",
        )
        parser.add_argument(
            "--example_template_created_by_column",
            type=str,
            default="",
            help="Column name for example template creator.",
        )
        parser.add_argument(
            "--example_template_subset_column",
            type=str,
            default="",
            help="Column name for example template subset.",
        )
        parser.add_argument(
            "--answer_choices_column",
            type=str,
            default="",
            help="Column name for answer choices.",
        )
        parser.add_argument(
            "--is_single_classification_column",
            type=str,
            default="",
            help="Column name for single classification flag.",
        )
        parser.add_argument(
            "--target_column",
            type=str,
            default="",
            help="Column name for dataset target.",
        )
        parser.add_argument(
            "--clear_datasets",
            type=str2bool,
            default=False,
            help="Clear existing datasets, prompts, and tasks.",
        )
        parser.add_argument(
            "--default_subset",
            type=str,
            default="",
            help="Default subset for this dataset.",
        )

    def handle(self, *args, **options):
        dataset_info_list = self.get_dataset_info(options)
        if not dataset_info_list:
            return

        if options["clear_datasets"]:
            self.clear_existing_data()

        self.process_datasets(dataset_info_list, options)

    def get_dataset_info(self, options) -> Optional[List[Tuple]]:
        if options["sheet_id"]:
            return self.fetch_from_google_sheet(options)
        elif options["datasets_file"]:
            return self.fetch_from_csv(options)
        else:
            self.stdout.write(
                self.style.ERROR(
                    "Either --datasets_file or --sheet_id option must be provided."
                )
            )
            return None

    def fetch_from_csv(self, options) -> List[Tuple]:
        file_path = os.path.join(
            f"{settings.BASE_DIR}/tawjeeh", options["datasets_file"]
        )
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR("CSV file not found."))
            return []

        with open(file_path, "r") as file:
            reader = csv.DictReader(file)
            return self.parse_rows(reader, options)

    def fetch_from_google_sheet(self, options) -> List[Tuple]:
        sheet_id = options["sheet_id"]
        sheet_name = options["sheet_name"]
        csv_url = (
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
            if sheet_name
            else f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        )

        try:
            df = pd.read_csv(csv_url)
            return self.parse_rows(df.to_dict("records"), options)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to fetch data from Google Sheet: {e}")
            )
            return []

    def parse_rows(self, rows, options) -> List[Tuple]:
        dataset_info_list = []
        for row in rows:
            info = self.extract_row_info(row, options)
            if info:
                dataset_info_list.append(tuple(info))
        return dataset_info_list

    def extract_row_info(self, row, options) -> List:
        link_column = options["link_column"]
        task_column = options["task_column"]

        if link_column not in row or task_column not in row:
            self.stdout.write(
                self.style.ERROR(
                    f"CSV must contain columns '{link_column}' and '{task_column}'."
                )
            )
            return None
        info = [row[link_column].strip(), row[task_column].strip()]
        additional_columns = [
            "example_template_column",
            "example_template_created_by_column",
            "example_template_subset_column",
            "answer_choices_column",
            "is_single_classification_column",
            "target_column",
            "default_subset",
        ]

        for column in additional_columns:
            if options[column]:
                info.append(
                    str(row.get(options[column], "")).strip()
                    if row.get(options[column])
                    else None
                )
            else:
                info.append(None)

        return info

    def clear_existing_data(self):
        self.stdout.write("Clearing existing datasets...")
        Dataset.objects.all().delete()
        Task.objects.all().delete()
        Prompt.objects.all().delete()
        self.stdout.write("All datasets, prompts, and tasks cleared.")

    def process_datasets(self, dataset_info_list, options):
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

            for dataset_info in dataset_info_list:
                dataset_url, primary_tasks, *additional_info = dataset_info
                tasks_created += self.process_dataset(
                    dataset_url,
                    primary_tasks,
                    additional_info,
                    options,
                )
                datasets_created += 1
                progress.advance(progress_task)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully populated datasets and tasks. {tasks_created} new tasks created and {datasets_created} new datasets created."
            )
        )

    def process_dataset(self, dataset_url, primary_tasks, additional_info, options):
        author, dataset_name = self.parse_dataset_url(dataset_url)
        if not author or not dataset_name:
            return 0

        dataset_data = self.fetch_dataset_data(author, dataset_name)
        if not dataset_data:
            return 0

        tasks = self.create_tasks(primary_tasks)
        dataset = self.create_or_update_dataset(
            dataset_name,
            author,
            dataset_data,
            additional_info,
        )
        dataset.tasks.set(tasks)
        self.manage_example_prompt(dataset, additional_info, options)
        # fetch dataset's details
        dataset.get_columns_names()
        dataset.get_configs_details()
        dataset.get_features()
        return len(tasks)

    def parse_dataset_url(self, dataset_url):
        path_parts = dataset_url.split("/")
        if len(path_parts) >= 2:
            return path_parts[-2], path_parts[-1]
        self.stdout.write(self.style.ERROR(f"Invalid URL format: {dataset_url}"))
        return None, None

    def fetch_dataset_data(self, author, dataset_name):
        api_url = (
            f"https://huggingface.co/api/datasets/{author}/{dataset_name}"
            if author != "datasets"
            else f"https://huggingface.co/api/datasets/{dataset_name}"
        )
        response = requests.get(api_url)
        if response.status_code != 200:
            self.stdout.write(
                self.style.ERROR(f"Failed to fetch dataset: {author}/{dataset_name}")
            )
            return None
        return response.json()

    def create_tasks(self, primary_tasks):
        task_names = [task.strip() for task in primary_tasks.split(",") if task.strip()]
        return [
            Task.objects.get_or_create(name=task_name)[0] for task_name in task_names
        ]

    def create_or_update_dataset(
        self,
        dataset_name,
        author,
        dataset_data,
        additional_info,
    ):
        huggingface_name = (
            dataset_name if author == "datasets" else f"{author}/{dataset_name}"
        )
        is_single_classification, target = additional_info[4:6]
        default_subset = additional_info[-1]

        dataset, created = Dataset.objects.update_or_create(
            name=dataset_name,
            defaults={
                "huggingface_name": huggingface_name,
                "description": dataset_data.get("description", ""),
                "huggingface_raw": dataset_data,
                "target_column": target,
                "is_single_classification": (
                    str2bool(is_single_classification)
                    if is_single_classification
                    else False
                ),
            },
        )
        if default_subset:
            dataset.default_subset = default_subset
        dataset.save()
        return dataset

    def manage_example_prompt(self, dataset, additional_info, options):
        (
            example_template,
            example_template_created_by,
            example_template_subset,
            answer_choices,
        ) = additional_info[:4]

        if options["example_template_column"]:
            Prompt.objects.filter(
                dataset=dataset, tags__name__icontains="Example Prompt"
            ).delete()

            if answer_choices:
                answer_choices = ast.literal_eval(answer_choices)

            dataset.create_example_prompt(
                prompt_template=example_template,
                created_by=example_template_created_by,
                subset=example_template_subset,
                answer_choices=answer_choices,
            )
