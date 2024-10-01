import argparse
import csv
import os
from typing import List, Optional, Tuple

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand
from prompt.models import Dataset, Prompt, Task
from prompt.tasks import process_dataset  # Import the Celery task
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
    help = "Queue datasets for processing using Celery."

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
            "--default_subset_column",
            type=str,
            default="",
            help="Default subset to show when accessing the dataset from the left bar.",
        )

        parser.add_argument(
            "--subsets_column",
            type=str,
            default="",
            help='Subsets to download, empty for all. Split subsets by comma","',
        )
        # parser.add_argument(
        #     "--example_template_column",
        #     type=str,
        #     default="",
        #     help="Column name for example template.",
        # )
        # parser.add_argument(
        #     "--example_template_created_by_column",
        #     type=str,
        #     default="",
        #     help="Column name for example template creator.",
        # )
        # parser.add_argument(
        #     "--example_template_subset_column",
        #     type=str,
        #     default="",
        #     help="Column name for example template subset.",
        # )
        # parser.add_argument(
        #     "--answer_choices_column",
        #     type=str,
        #     default="",
        #     help="Column name for answer choices.",
        # )
        # parser.add_argument(
        #     "--example_template_tags_column",
        #     type=str,
        #     default="",
        #     help="Column name for example template tags.",
        # )

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

        # Check if the required fields are not nan
        if pd.isna(row[link_column]) or pd.isna(row[task_column]):
            return None

        info = [row[link_column].strip(), row[task_column].strip()]
        additional_columns = [
            "target_column",
            "subsets_column",
            "default_subset_column",
            "is_single_classification_column",
            # "answer_choices_column",
            # "example_template_column",
            # "example_template_tags_column",
            # "example_template_subset_column",
            # "example_template_created_by_column",
        ]

        for column in additional_columns:
            if options[column]:
                value = row.get(options[column])
                if pd.notna(value):
                    info.append(str(value).strip())
                else:
                    info.append(None)
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
        datasets_queued = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total} datasets queued"),
        ) as progress:
            progress_task = progress.add_task(
                "[cyan]Queueing datasets for processing...",
                total=len(dataset_info_list),
            )

            for dataset_info in dataset_info_list:
                dataset_url, primary_tasks, *additional_info = dataset_info
                # Queue the Celery task
                process_dataset.delay(dataset_url, primary_tasks, additional_info)
                datasets_queued += 1
                progress.advance(progress_task)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully queued {datasets_queued} datasets for processing."
            )
        )
