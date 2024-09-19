import ast
import gc

import requests
from celery import chord, group, shared_task
from celery.utils.log import get_task_logger
from django.core.cache import cache
from prompt.models import Dataset, Prompt, Task

logger = get_task_logger(__name__)


@shared_task
def process_single_dataset(dataset_id):
    try:
        dataset = Dataset.objects.get(id=dataset_id)
        dataset.get_configs_details()
        dataset.get_columns_names()
        # dataset.get_huggingface_info()
        # dataset.load_split_samples()
        return {"status": "success", "dataset_id": dataset_id}
    except Exception as e:
        return {"status": "failed", "dataset_id": dataset_id, "error": str(e)}
    finally:
        gc.collect()


@shared_task
def handle_results(results):
    success_datasets = []
    failed_datasets = []

    for res in results:
        if res["status"] == "success":
            success_datasets.append(res["dataset_id"])
        else:
            failed_datasets.append(
                {"dataset_id": res["dataset_id"], "error": res["error"]}
            )

    return {
        "success datasets count": len(success_datasets),
        "failed datasets count": len(failed_datasets),
        "failed datasets": failed_datasets,
    }


@shared_task(
    time_limit=60 * 60
)  # 60 minutes maximum as it needs to loop over all datasets
def refresh_datasets_info():
    datasets = Dataset.objects.all()
    tasks = group(process_single_dataset.s(dataset.id) for dataset in datasets)
    result = chord(tasks)(handle_results.s())
    return result


@shared_task
def reset_redis_cache():
    for key in cache.keys("*"):
        cache.delete(key)
    refresh_results = refresh_datasets_info()
    return f"cache invalidation finished and datasets info are refreshed. refresh results: {refresh_results}"


# check if we are getting the timezone right:
# @shared_task
# def print_current_time():
#     from django.utils import timezone
#     import pytz

#     local_tz = pytz.timezone("Asia/Riyadh")
#     current_time = timezone.now().astimezone(local_tz)
#     print(f"Current local time: {current_time}")
#     return current_time


# tasks related to pull data during the sync_with_hf management command:


def fetch_dataset_data(author, dataset_name):
    api_url = (
        f"https://huggingface.co/api/datasets/{author}/{dataset_name}"
        if author != "datasets"
        else f"https://huggingface.co/api/datasets/{dataset_name}"
    )
    response = requests.get(api_url)
    if response.status_code != 200:
        return None
    return response.json()


def create_or_update_dataset(dataset_name, author, dataset_data, additional_info):
    huggingface_name = (
        dataset_name if author == "datasets" else f"{author}/{dataset_name}"
    )
    is_single_classification, target = additional_info[4:6]

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
    default_subset = additional_info[2]
    if default_subset:
        dataset.default_subset = default_subset
    dataset.save()
    return dataset


def manage_example_prompt(dataset, additional_info):
    (
        example_template,
        example_template_created_by,
        example_template_subset,
        answer_choices,
        _,
        _,
        example_template_tags,
    ) = additional_info[:7]

    Prompt.objects.filter(
        dataset=dataset, tags__name__icontains="Example Prompt"
    ).delete()

    if answer_choices:
        answer_choices = ast.literal_eval(answer_choices)

    prompt = dataset.create_example_prompt(
        prompt_template=example_template,
        created_by=example_template_created_by,
        subset=example_template_subset,
        answer_choices=answer_choices,
    )

    if example_template_tags and prompt:
        tags = [tag.strip() for tag in example_template_tags.split(",") if tag.strip()]
        prompt.tags.add(*tags)
        prompt.save()


def str2bool(value):
    if isinstance(value, bool):
        return value
    if value.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif value.lower() in ("no", "false", "f", "n", "0"):
        return False
    raise ValueError("Boolean value expected.")


@shared_task
def process_dataset(dataset_url, primary_tasks, additional_info):
    author, dataset_name = None, None
    path_parts = dataset_url.split("/")
    if len(path_parts) >= 2:
        author, dataset_name = path_parts[-2], path_parts[-1]
    if not author or not dataset_name:
        return False
    dataset_data = fetch_dataset_data(author, dataset_name)
    if not dataset_data:
        return False
    task_names = [task.strip() for task in primary_tasks.split(",") if task.strip()]
    tasks = [Task.objects.get_or_create(name=task_name)[0] for task_name in task_names]
    dataset = create_or_update_dataset(
        dataset_name,
        author,
        dataset_data,
        additional_info,
    )
    dataset.tasks.set(tasks)
    manage_example_prompt(dataset, additional_info)
    # fetch dataset's details
    dataset.get_columns_names()
    dataset.get_configs_details()
    dataset.get_features()
    return True
