import ast
import csv
import os

import pandas as pd
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from prompt.models import Dataset, Prompt, Task
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn


class Command(BaseCommand):
    help = (
        "Populate datasets and tasks from Hugging Face.\n"
        "The CSV file or Google Sheet should have at least two columns: 'link' and 'task_name'.\n"
        "You can optionally specify the column names using --link-column and --task-column."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--datasets_file",
            type=str,
            default="./datasets.csv",
            help="Path to the CSV file containing dataset URLs and primary tasks. Path should be passed relative to settings.BASE_DIR/tawjeeh directory. Default is './datasets.csv'.",
        )
        parser.add_argument(
            "--sheet_id",
            type=str,
            help="ID of the Google Sheet containing dataset URLs and primary tasks.",
        )
        parser.add_argument(
            "--sheet_name",
            type=str,
            help="Name of the sheet in the Google Sheet. If not provided, the first sheet will be used.",
        )
        parser.add_argument(
            "--link_column",
            type=str,
            default="link",
            help="Name of the column in the CSV or Google Sheet that contains the dataset URLs. Default is 'link'.",
        )
        parser.add_argument(
            "--task_column",
            type=str,
            default="task_name",
            help="Name of the column in the CSV or Google Sheet that contains the dataset primary tasks. Default is 'task_name'.",
        )
        parser.add_argument(
            "--example_template_column",
            type=str,
            default="",
            help="If the source contains an example template, give the column name here. This is useful to add an example prompt to the dataset IF IT DOES NOT HAVE ONE ALREADY.",
        )
        parser.add_argument(
            "--example_template_created_by_column",
            type=str,
            default="",
            help="If the source contains an example template, it should also contain a column for the creator.",
        )
        parser.add_argument(
            "--example_template_subset_column",
            type=str,
            default="",
            help="If the source contains an example template, it can also contain a column for the subset (config). If this is empty, it will take the default subset then.",
        )

        parser.add_argument(
            "--answer_choices_column",
            type=str,
            default="",
            help="If the source contains answer choices, give the column name here.",
        )

        parser.add_argument(
            "--clear_datasets",
            type=bool,
            default=False,
            help="BE CAREFUL! If this is set to True, it will clear any existing datasets, prompts, and tasks in the database. Default is False.",
        )

    def handle(self, *args, **options):
        file_path = options.get("datasets_file")
        sheet_id = options.get("sheet_id")
        sheet_name = options.get("sheet_name")
        link_column = options.get("link_column")
        task_column = options.get("task_column")
        example_template_column = options.get("example_template_column")
        example_template_created_by_column = options.get(
            "example_template_created_by_column"
        )
        example_template_subset_column = options.get("example_template_subset_column")
        answer_choices_column = options.get("answer_choices_column")
        clear_datasets = options.get("clear_datasets")

        dataset_info_list = None

        if sheet_id:
            dataset_info_list = self.fetch_from_google_sheet(
                sheet_id,
                sheet_name,
                link_column,
                task_column,
                example_template_column,
                example_template_created_by_column,
                example_template_subset_column,
                answer_choices_column,
            )
        elif file_path:
            file_path = os.path.join(f"{settings.BASE_DIR}/tawjeeh", file_path)
            if os.path.exists(file_path):
                with open(file_path, "r") as file:
                    reader = csv.DictReader(file)
                    if (
                        link_column not in reader.fieldnames
                        or task_column not in reader.fieldnames
                    ):
                        self.stdout.write(
                            self.style.ERROR(
                                f"CSV file must contain columns '{link_column}' and '{task_column}'."
                            )
                        )
                        return

                    dataset_info_list = []
                    for row in reader:
                        info = (
                            row[link_column].strip(),
                            row[task_column].strip(),
                        )
                        if example_template_column:
                            assert example_template_created_by_column, (
                                "If the source contains an example template, "
                                "it should also contain a column for the creator."
                            )
                            info.append(
                                row[example_template_column].strip()
                                if row[example_template_column]
                                else None
                            )
                            info.append(
                                row[example_template_created_by_column].strip()
                                if row[example_template_created_by_column]
                                else None
                            )
                            if example_template_subset_column:
                                info.append(
                                    row[example_template_subset_column].strip()
                                    if row[example_template_subset_column]
                                    else None
                                )
                            else:
                                info.append(None)
                            if answer_choices_column:
                                info.append(
                                    row[answer_choices_column].strip()
                                    if row[answer_choices_column]
                                    else None
                                )
                            else:
                                info.append(None)
                        else:
                            info.append([None] * 4)
                        dataset_info_list.append(info)
            else:
                self.stdout.write(
                    self.style.ERROR(
                        "No valid dataset CSV file provided or file not found."
                    )
                )
                return
        else:
            self.stdout.write(
                self.style.ERROR(
                    "Either --datasets_file or --sheet-id option must be provided."
                )
            )
            return

        if dataset_info_list is None:
            return

        tasks_created = 0
        datasets_created = 0

        if clear_datasets:
            print("Clearing existing datasets...")
            Dataset.objects.all().delete()
            Task.objects.all().delete()
            Prompt.objects.all().delete()
            print("All datasets, prompts, and tasks cleared.")

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
            for (
                dataset_url,
                primary_tasks,
                example_template,
                example_template_created_by,
                example_template_subset,
                answer_choices,
            ) in dataset_info_list:
                path_parts = dataset_url.split("/")
                if len(path_parts) >= 2:
                    author = path_parts[-2]
                    dataset_name = path_parts[-1]
                else:
                    self.stdout.write(
                        self.style.ERROR(f"Invalid URL format: {dataset_url}")
                    )
                    progress.advance(progress_task)
                    continue

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
                if author == "datasets":
                    huggingface_name = dataset_name
                else:
                    huggingface_name = f"{author}/{dataset_name}"
                description = dataset.get("description", "")
                huggingface_raw = dataset

                # Split tasks by comma and create or get each task
                task_names = [
                    task.strip() for task in primary_tasks.split(",") if task.strip()
                ]
                tasks = []
                for task_name in task_names:
                    task, created = Task.objects.get_or_create(name=task_name)
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

                # Set the primary tasks to the dataset
                dataset.tasks.set(tasks)

                # manage the created templates examples
                if example_template_column:
                    if answer_choices:
                        # convert string to list, "['answer1', 'answer2']" -> ["answer1", "answer2"]
                        answer_choices = ast.literal_eval(answer_choices)
                    # delete any example prompt for this dataset
                    Prompt.objects.filter(
                        dataset=dataset,
                        tags__name__icontains="Example Prompt",
                    ).delete()
                    dataset.create_example_prompt(
                        prompt_template=example_template,
                        created_by=example_template_created_by,
                        subset=example_template_subset,
                        answer_choices=answer_choices,
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

    def fetch_from_google_sheet(
        self,
        sheet_id,
        sheet_name,
        link_column,
        task_column,
        example_template_column=None,
        example_template_created_by_column=None,
        example_template_subset_column=None,
        answer_choices_column=None,
    ):
        try:
            if sheet_name:
                # Construct the export CSV URL using sheet name
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
            else:
                # Default to the first sheet
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
                print("No sheet name provided. Using the first sheet by default.")

            # Read the data from the CSV export URL
            sheet = pd.read_csv(csv_url, header=0)
            # Convert to list of records
            records = sheet.to_dict(orient="records")
        except Exception as e:
            print(f"Failed to fetch data from Google Sheet: {e}")
            raise e
            return None

        if link_column not in sheet.columns or task_column not in sheet.columns:
            print(
                f"Google Sheet must contain columns '{link_column}' and '{task_column}'."
            )
            return None

        dataset_info_list = []

        for row in records:
            info = [
                row[link_column].strip(),
                row[task_column].strip(),
            ]
            if example_template_column:
                assert example_template_created_by_column, (
                    "If the source contains an example template, "
                    "it should also contain a column for the creator."
                )
                info.append(
                    row.get(example_template_column, "").strip()
                    if not pd.isna(row[example_template_column])
                    else None
                )
                info.append(
                    row.get(example_template_created_by_column, "").strip()
                    if not pd.isna(row[example_template_created_by_column])
                    else None
                )
                if example_template_subset_column:
                    info.append(
                        row.get(example_template_subset_column, "").strip()
                        if not pd.isna(row[example_template_subset_column])
                        else None
                    )
                else:
                    info.append(None)
                if answer_choices_column:
                    info.append(
                        row.get(answer_choices_column, "").strip()
                        if not pd.isna(row[answer_choices_column])
                        else None
                    )
                else:
                    info.append(None)
            else:
                info.extend([None] * 4)
            dataset_info_list.append(tuple(info))

        return dataset_info_list
