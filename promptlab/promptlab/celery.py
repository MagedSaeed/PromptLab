import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
# if not set for production, use the development settings
if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "promptlab.settings")

app = Celery("promptlab")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Set timezone for Celery
app.conf.timezone = "Asia/Riyadh"  # Set to Riyadh timezone
app.conf.enable_utc = True  # Ensure UTC is enabled for proper timezone conversion


# Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.update(
    worker_max_memory_per_child=1048576 // 5,  # 0.2 GB in kilobytes
    task_time_limit=60 * 30,  # 30 minutes
    task_soft_time_limit=60 * 40,  # 40 minutes
    worker_max_tasks_per_child=5,
    worker_prefetch_multiplier=2,
    worker_concurrency=2,  # set one concurrent worker(s)
)
