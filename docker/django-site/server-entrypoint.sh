#!/bin/sh

until cd /app/tawjeeh
do
    echo "Waiting for server volume..."
done


until python manage.py migrate
do
    echo "Waiting for db to be ready..."
    sleep 2
done


# create superusers
until python manage.py import_superusers ../docker/django-site/admins.yml
do
    echo "Waiting for superusers to be created..."
    sleep 2
done


python manage.py collectstatic --noinput

gunicorn tawjeeh.wsgi --bind 0.0.0.0:8000 --workers 4 --threads 4

# for debug
#python manage.py runserver 0.0.0.0:8000