import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tawjeeh.settings")

app = Celery("tawjeeh")

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
    worker_max_memory_per_child=1048576,  # 1 GB in kilobytes
    task_time_limit=60 * 30,  # 0.5 hours
    task_soft_time_limit=60 * 60,  # 1 hours
    worker_max_tasks_per_child=1,
    worker_prefetch_multiplier=1,
)
