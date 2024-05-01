# pull official base image
FROM python:3.10.14-alpine

RUN apk update && apk add python3-dev gcc libc-dev


WORKDIR /app

RUN pip install --upgrade pip setuptools
RUN pip install gunicorn
ADD ./requirements.txt /app/
RUN pip install -r requirements.txt

# create static folder
RUN mkdir -p /app/tawjeeh/django_static

ADD ./tawjeeh /app/tawjeeh
ADD ./docker /app/docker


RUN chmod +x /app/docker/django-site/server-entrypoint.sh
# RUN chmod +x /app/docker/django-site/worker-entrypoint.sh