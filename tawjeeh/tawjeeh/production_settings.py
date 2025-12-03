import os

from tawjeeh.settings import *  # noqa: F403

DEBUG = True

SITE_ID = 1

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": f"{os.environ['POSTGRES_NAME']}",
        "USER": f"{os.environ['POSTGRES_USER']}",
        "PASSWORD": f"{os.environ['POSTGRES_PASSWORD']}",
        "HOST": f"{os.environ['POSTGRES_HOST']}",
        "PORT": f"{os.environ['POSTGRES_PORT']}",
    }
}

# pop 'django_toolbar' from INSTALLED_APPS if it exists
if "django_toolbar" in INSTALLED_APPS:  # noqa: F405
    INSTALLED_APPS.remove("django_toolbar")  # noqa: F405

# pop 'debug_toolbar.middleware.DebugToolbarMiddleware' from MIDDLEWARE if it exists
if "debug_toolbar.middleware.DebugToolbarMiddleware" in MIDDLEWARE:  # noqa: F405
    MIDDLEWARE.remove("debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{os.environ['REDIS_HOST']}:{os.environ['REDIS_PORT']}",  # Adjust the location as per your Redis server configuration
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SERIALIZER": "django_redis.serializers.pickle.PickleSerializer",
            "USERNAME": f"{os.environ['REDIS_USER']}",
            "PASSWORD": f"{os.environ['REDIS_PASSWORD']}",
        },
    }
}

CELERY_BROKER_URL = f"redis://{os.environ['REDIS_USER']}:{os.environ['REDIS_PASSWORD']}@{os.environ['REDIS_HOST']}:{os.environ['REDIS_PORT']}"
CELERY_RESULT_BACKEND = f"redis://{os.environ['REDIS_USER']}:{os.environ['REDIS_PASSWORD']}@{os.environ['REDIS_HOST']}:{os.environ['REDIS_PORT']}"

CSRF_TRUSTED_ORIGINS = [
    "https://tawjeeh-production.up.railway.app",
    "https://*.railway.app",
    "https://*.127.0.0.1",
]

SECURE_PROXY_SSL_HEADER = None

EMAIL_BACKEND = "sendgrid_backend.SendgridBackend"
SENDGRID_API_KEY = os.environ["SENDGRID_API_KEY"]
SENDGRID_SANDBOX_MODE_IN_DEBUG = False

server_ip = os.getenv("SERVER_IP")
if server_ip:
    ALLOWED_HOSTS.append(server_ip)  # noqa: F405


CELERY_BROKER_URL = f"redis://{os.environ['REDIS_USER']}:{os.environ['REDIS_PASSWORD']}@{os.environ['REDIS_HOST']}:{os.environ['REDIS_PORT']}"


# suppress system checks for debug_toolbar
SILENCED_SYSTEM_CHECKS = ["debug_toolbar.W001"]
