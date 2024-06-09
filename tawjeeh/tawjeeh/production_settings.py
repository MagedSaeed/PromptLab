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


CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{os.environ['REDIS_HOST']}:{os.environ['REDIS_PORT']}",  # Adjust the location as per your Redis server configuration
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SERIALIZER": "django_redis.serializers.pickle.PickleSerializer",
        },
    }
}

STATIC_ROOT = os.path.join(BASE_DIR, "static")  # noqa: F405
STATICFILES_DIRS = []
