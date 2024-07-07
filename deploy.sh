# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Navigate to the project directory
cd tawjeeh


# Run Django management commands
python manage.py migrate

# create superusers
python manage.py import_superusers ../docker/django-site/admins.yml

# setup allauth
python manage.py setup_allauth

# sync with hf
python manage.py sync_with_hf --datasets-urls ./datasets.urls

# collect static
python manage.py collectstatic --noinput


export DJANGO_SETTINGS_MODULE=tawjeeh.production_settings

# Start the Gunicorn server in the background
gunicorn tawjeeh.wsgi --workers 4 --threads 4