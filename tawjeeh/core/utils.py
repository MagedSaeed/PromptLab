import hashlib
import pickle
from functools import wraps

from django.core.cache import cache


def pickle_serialize(obj):
    return pickle.dumps(obj)


def pickle_deserialize(serialized_obj):
    return pickle.loads(serialized_obj)


def redis_cache(timeout=60 * 60 * 24):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Include class name in the cache key if it exists
            class_name = ""
            if args and hasattr(args[0], "__class__"):
                class_name = f"{args[0].__class__.__name__}."

            # Serialize arguments
            serialized_args = pickle_serialize(args)
            serialized_kwargs = pickle_serialize(kwargs)

            # Generate a unique cache key based on the class name, function name, and arguments
            cache_key = f"{class_name}{func.__name__}_{hashlib.md5(serialized_args + serialized_kwargs).hexdigest()}"

            # Try to get the cached result
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return pickle_deserialize(cached_result)

            # Call the function and cache the result
            result = func(*args, **kwargs)
            serialized_result = pickle_serialize(result)
            cache.set(
                cache_key, serialized_result, timeout=timeout
            )  # Cache with the specified timeout
            return result

        return wrapper

    return decorator
