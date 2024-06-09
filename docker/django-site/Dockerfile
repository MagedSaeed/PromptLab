# pull official base image
FROM ubuntu:noble

SHELL ["/bin/bash", "-c"]

RUN set -xe \
    && apt-get update \
    && apt-get install -y python3-pip

WORKDIR /app

# Upgrade pip and setuptools with --break-system-packages flag
RUN pip install --upgrade pip setuptools --break-system-packages
RUN pip install gunicorn psycopg2-binary --break-system-packages

# for redis cache
RUN apt-get -y install redis-server

# when connecting to the application shell in the container for debugging
RUN pip install --upgrade ipython --break-system-packages

ADD ./requirements.txt /app/
RUN pip install -r requirements.txt --break-system-packages

# create static folder
RUN mkdir -p /app/tawjeeh/tawjeeh/static

ADD ./tawjeeh /app/tawjeeh
ADD ./docker /app/docker

RUN chmod +x /app/docker/django-site/server-entrypoint.sh
# RUN chmod +x /app/docker/django-site/worker-entrypoint.sh
