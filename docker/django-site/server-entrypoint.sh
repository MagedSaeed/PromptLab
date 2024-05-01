#!/bin/sh

until cd /app/tawjeeh
do
    echo "Waiting for server volume..."
done


until python3 manage.py migrate
do
    echo "Waiting for db to be ready..."
    sleep 2
done


python3 manage.py collectstatic --noinput

# python manage.py createsuperuser --noinput

gunicorn tawjeeh.wsgi --bind 0.0.0.0:8000 --workers 4 --threads 4

# for debug
#python manage.py runserver 0.0.0.0:8000