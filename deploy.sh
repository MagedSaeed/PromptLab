#!/bin/bash

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Navigate to the project directory
cd tawjeeh

# Set production settings as env variable
export DJANGO_SETTINGS_MODULE=tawjeeh.production_settings

# Migrate Django sites first
python manage.py migrate sites

# Run Django management commands
python manage.py migrate

# Create superusers
python manage.py import_superusers ../docker/django-site/admins.yml

# Setup allauth
python manage.py setup_allauth

# Sync with HF
python manage.py sync_with_hf \
    --sheet_id 1kIDS-fwO5l6sH2ZBDCepOJeNyOh2j7Wb-w3W0JChi2k \
    --sheet_name final-list \
    --example_template_column example_template \
    --example_template_created_by_column example_template_created_by \
    --example_template_subset_column subset \
    --answer_choices_column answer_choices \
    --clear_datasets False

# Collect static
python manage.py collectstatic --noinput

# Install Gunicorn
pip install gunicorn

# Create a non-root user
useradd -m -d /home/tawjeeh tawjeeh

# Set permissions for the virtual environment and project directory
chown -R tawjeeh:tawjeeh /app/venv /app/tawjeeh

# Run Celery worker as the non-root user
sudo -u tawjeeh -E bash -c "source /app/venv/bin/activate && celery -A tawjeeh worker -l info &"

# Run Celery beat as the non-root user
sudo -u tawjeeh -E bash -c "source /app/venv/bin/activate && celery -A tawjeeh beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler &"

# Start the Gunicorn server in the background
gunicorn tawjeeh.wsgi --workers 4 --threads 4 --bind 0.0.0.0:8080
