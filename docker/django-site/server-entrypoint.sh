#!/bin/bash

until cd /app/promptlab
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

# setup django allauth
until python3 manage.py setup_allauth
do
    echo "Waiting for setup allauth to finish..."
    sleep 2
done

# sync datastes with huggingface
until python3 manage.py sync_with_hf --datasets-urls datasets.urls
do
    echo "Waiting for huggingface sync to finish..."
    sleep 2
done

# collect static
python3 manage.py collectstatic --noinput


DJANGO_SETTINGS_MODULE=promptlab.production_settings

# create logs dir
mkdir -p /var/log/gunicorn

gunicorn promptlab.wsgi -c promptlab/gunicorn.conf.py

# for debug
#python3 manage.py runserver 0.0.0.0:8000