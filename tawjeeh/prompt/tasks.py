from celery import shared_task
from celery.utils.log import get_task_logger
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
