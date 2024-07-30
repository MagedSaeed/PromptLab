# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Navigate to the project directory
cd tawjeeh

# set production settings as env variable
export DJANGO_SETTINGS_MODULE=tawjeeh.production_settings

# migrate django sites first
python manage.py migrate sites

# Run Django management commands
python manage.py migrate

# create superusers
python manage.py import_superusers ../docker/django-site/admins.yml

# setup allauth
python manage.py setup_allauth

# sync with hf
python manage.py sync_with_hf \
    --sheet_id 1kIDS-fwO5l6sH2ZBDCepOJeNyOh2j7Wb-w3W0JChi2k \
    --sheet_name final-list \
    --example_template_column example_template \
    --example_template_created_by_column example_template_created_by \
    --example_template_subset_column subset \
    --answer_choices_column answer_choices \
    --is_single_classification_column is_single_classification \
    --target_column target_column \
    --clear_datasets True

# collect static
python manage.py collectstatic --noinput

# install gunicorn
pip install gunicorn

# run celery worker
celery -A tawjeeh worker -l info &

# run celery beat
celery -A tawjeeh beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler &

# Start the Gunicorn server in the background
gunicorn tawjeeh.wsgi --workers 4 --threads 4 --bind 0.0.0.0:8080