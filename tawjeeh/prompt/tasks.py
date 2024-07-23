from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.cache import cache
from prompt.models import Dataset

logger = get_task_logger(__name__)


@shared_task
def refresh_datasets_info():
    success_datasets = []
    failed_datasets = []

    for dataset in Dataset.objects.all():
        try:
            dataset.get_columns_names()
            dataset.subsets_with_splits
            dataset.get_huggingface_info()
            dataset.load_samples()
            success_datasets.append(dataset)
        except Exception as e:
            failed_datasets.append({dataset.huggingface_name: str(e)})

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
