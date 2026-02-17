# promptlab
PromptLab is an instructions-tuning platform to create,review, and build prompts datasets.
It resembles most of the functionalities of [promptsource](https://github.com/bigscience-workshop/promptsource) while adding more features to it.

# how to run

- First, start by cloning the repo:

`
git clone https://github.com/MagedSaeed/promptlab.git
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
echo "SUPERUSER_PASSWORD=<your-superuser-password>
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>" > .env
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
cd promptlab
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
celery -A promptlab worker -l info &

# run celery beat
celery -A promptlab beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler &
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
echo "SUPERUSER_PASSWORD=<your-superuser-password>
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>" > .env

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

# Adding prompts via APIs

The platform allows for integrating prompts through a REST API. In order to do so, the project admin needs to set a key for his project then he can share this key with members to contribute via APIs.

Sample python code:
```python
import requests
import json

# The URL for the API endpoint
url = "https://promptlab.up.railway.app/api/prompt/create"

# The headers for the request
headers = {
    "Content-Type": "application/json"
}

# The data payload
data = {
    "name": "Test Prompt from api",
    "template": "Translate {text} to {language}",
    "dataset_huggingface_name": "arbml/watan_2004",
    "dataset_subset": "",  # optional, can be removed
    "project_secret_key": "6Wirj",  # can be found in: https://promptlab.up.railway.app/admin/prompt/promptingproject , then click the name of the project
    "created_by": "majed.alshaibani",
    "tags": ["AI generated", "AI translated"],  # optional, these are just examples, can be removed
    "text_direction": "rtl",  # optional, default to rtl, choices are: rtl or ltr, can be removed
    "answer_choices": json.dumps([{"value": "choice1"}])  # Convert to JSON string
}

# Send the POST request
response = requests.post(url, headers=headers, json=data)

# Check the response
if response.status_code == 201:
    print("Prompt created successfully!")
    print("Response:", response.json())
else:
    print("Failed to create prompt")
    print("Status code:", response.status_code)
    print("Response:", response.text)
```

Another example via curl

```bash

curl -X POST https://promptlab.up.railway.app/api/prompt/create \
     -H "Content-Type: application/json" \
     -d '{
         "name": "Test Prompt from api",
         "dataset_subset": "hey",
         "template": "Translate {text} to {language}",
         "dataset_huggingface_name": "arbml/watan_2004",
         "project_secret_key": "6Wirj",
         "text_direction": "ltr",
         "created_by": "majed.alshaibani",
         "tags": ["translation", "api-test"],
         "answer_choices": "[{\"value\": \"choice1\"}]"
     }'

```
