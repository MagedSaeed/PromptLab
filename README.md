# tawjeeh
Tawjeeh is an instructions-tuning platform to create,review, and build prompts datasets.
It resembles most of the functionalities of [promptsource](https://github.com/bigscience-workshop/promptsource) while adding more features to it.

# how to run

- First, start by cloning the repo:

`
git clone https://github.com/MagedSaeed/tawjeeh.git
`

- make sure redis is installed and enabled

```bash
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
sudo apt-get update
sudo apt-get install -y redis
sudo service redis-server restart
```
- create a .env file

```bash
echo "SUPERUSER_PASSWORD=aaaa1111
GOOGLE_CLIENT_ID=110388034790-t6irvd4oel1pomr3l7l2i1v9268ornqv.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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" > .env
```

- Install the requriements

```bash
pip install -r requirements.txt
pip install -r requirements_dev.txt
```

install pre-commit hook:

```bash
pre-commit install 
```

- cd into the project dir

```bash
cd tawjeeh
```

- start project setup. First, migrate:

```bash
python manage.py migrate sites
python manage.py migrate
```
- create super user. This adds majed.alshaibani as a superuser using the password you put in the .env file.
You can add your username too if you wish.

```bash
python manage.py import_superusers admins.yml
```

- setup allauth for google authentication

```bash
python manage.py setup_allauth
```

- sync datasets from huggingface using the google sheet

```bash
python manage.py sync_with_hf \
    --sheet_id 1kIDS-fwO5l6sH2ZBDCepOJeNyOh2j7Wb-w3W0JChi2k \
    --sheet_name final-list \
    --example_template_column example_template \
    --example_template_created_by_column example_template_created_by \
    --example_template_subset_column subset \
    --answer_choices_column answer_choices \
    --is_single_classification_column is_single_classification \
    --target_column target_column \
    --clear_datasets False
```

Optional. Run celery and celery beat. These are used for background tasks

```bash
# run celery worker
celery -A tawjeeh worker -l info &

# run celery beat
celery -A tawjeeh beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler &
```


Finally, run the server:

```bash
python manage.py runserver
```

The full code of the above setup in one shot to easily copy and paste:

```bash
# install redis
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
sudo apt-get update
sudo apt-get install -y redis
sudo service redis-server restart
# setup .env
echo "SUPERUSER_PASSWORD=aaaa1111
GOOGLE_CLIENT_ID=110388034790-t6irvd4oel1pomr3l7l2i1v9268ornqv.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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" > .env
# install requirements
pip install -r requirements.txt
pip install -r requirements_dev.txt
# setup pre-commit
pre-commit install
# cd into the application dir
cd tawjeeh
# migraste
python manage.py migrate sites
python manage.py migrate
# setup superusers
python manage.py import_superusers admins.yml
# setup allauth for google auth
python manage.py setup_allauth
# sync with hf from gsheets
python manage.py sync_with_hf \
    --sheet_id 1kIDS-fwO5l6sH2ZBDCepOJeNyOh2j7Wb-w3W0JChi2k \
    --sheet_name final-list \
    --example_template_column example_template \
    --example_template_created_by_column example_template_created_by \
    --example_template_subset_column subset \
    --answer_choices_column answer_choices \
    --is_single_classification_column is_single_classification \
    --target_column target_column \
    --clear_datasets False
```

then, run the server as:
```bash
python manage.py runserver
```



