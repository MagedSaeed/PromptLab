#!/bin/bash

until cd /app/tawjeeh
do
    echo "Waiting for server volume..."
done

# setup huggingface cache
mkdir -p /cache/huggingface

export HF_HOME=/cache/huggingface

until python3 manage.py migrate
do
    echo "Waiting for db to be ready..."
    sleep 2
done


# create superusers
until python3 manage.py import_superusers ../docker/django-site/admins.yml
do
    echo "Waiting for superusers to be created..."
    sleep 2
done

# collect static
python3 manage.py collectstatic --noinput

# get datasets from huggingface
python3 manage.py sync_with_hf

DJANGO_SETTINGS_MODULE=tawjeeh.production_settings

# create logs dir
mkdir -p /var/log/gunicorn

gunicorn tawjeeh.wsgi -c tawjeeh/gunicorn.conf.py

# for debug
#python3 manage.py runserver 0.0.0.0:8000