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


# CACHES = {
#     "default": {
#         "BACKEND": "django_redis.cache.RedisCache",
#         "LOCATION": f"redis://{os.environ['REDIS_HOST']}:{os.environ['REDIS_PORT']}",  # Adjust the location as per your Redis server configuration
#         "OPTIONS": {
#             "CLIENT_CLASS": "django_redis.client.DefaultClient",
#             "SERIALIZER": "django_redis.serializers.pickle.PickleSerializer",
#         },
#     }
# }

CSRF_TRUSTED_ORIGINS = [
    "https://tawjeeh-production.up.railway.app",
    "https://*.127.0.0.1",
]

server_ip = os.getenv("SERVER_IP")
if server_ip:
    ALLOWED_HOSTS.append(server_ip)  # noqa: F405
