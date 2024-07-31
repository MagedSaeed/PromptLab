import gc

from celery import group, shared_task
from celery.utils.log import get_task_logger
from django.core.cache import cache
from prompt.models import Dataset

logger = get_task_logger(__name__)


@shared_task
def process_single_dataset(dataset_id):
    try:
        dataset = Dataset.objects.get(id=dataset_id)
        dataset.get_columns_names()
        dataset.subsets_with_splits
        dataset.get_huggingface_info()
        dataset.load_samples()
        return {"status": "success", "dataset_id": dataset_id}
    except Exception as e:
        return {"status": "failed", "dataset_id": dataset_id, "error": str(e)}
    finally:
        gc.collect()


@shared_task
def refresh_datasets_info():
    datasets = Dataset.objects.all()
    tasks = group(process_single_dataset.s(dataset.id) for dataset in datasets)
    result = tasks.apply_async()

    # Collect results
    success_datasets = []
    failed_datasets = []

    for res in result.get():
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
