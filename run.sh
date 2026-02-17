# install redis
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
sudo apt-get update
sudo apt-get install -y redis
sudo service redis-server restart

# setup .env
echo "DJANGO_SECRET_KEY=<your-django-secret-key>
SUPERUSER_PASSWORD=<your-superuser-password>
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>
DB_PASSWORD=<your-db-password>
DB_USER=postgres
DB_NAME=<your-db-name>
DB_HOST=localhost
DB_PORT=5432
# Optional: required for AI-powered prompt generation
chatgpt_key=<your-openai-api-key>
claude_key=<your-anthropic-api-key>
gemini_key=<your-gemini-api-key>" > .env

# install requirements
pip install -r requirements.txt
pip install -r requirements_dev.txt

# setup pre-commit
pre-commit install

# cd into the application dir
cd promptlab

# migraste
python manage.py migrate sites
python manage.py migrate

# setup superusers
python manage.py import_superusers admins.yml

# setup allauth for google auth
python manage.py setup_allauth

# sync with hf from gsheets
# python manage.py sync_with_hf \
#     --sheet_id 1kIDS-fwO5l6sH2ZBDCepOJeNyOh2j7Wb-w3W0JChi2k \
#     --sheet_name final-list \
#     --example_template_column example_template \
#     --example_template_created_by_column example_template_created_by \
#     --example_template_subset_column subset \
#     --answer_choices_column answer_choices \
#     --is_single_classification_column is_single_classification \
#     --target_column target_column \
#     --clear_datasets False