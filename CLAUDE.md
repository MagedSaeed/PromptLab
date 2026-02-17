# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PromptLab** is a Django-based platform for collaborative prompt engineering and dataset curation for NLP tasks. It integrates with HuggingFace Hub to import datasets and provides tools for creating, reviewing, and testing prompt templates with LLM models.

## Architecture

### Monolithic Django Application

The project follows a standard Django multi-app architecture:

- **prompt/**: Core functionality for prompting projects, datasets, prompt templates, and review workflows
- **api/**: REST API endpoints for programmatic access
- **core/**: User management (custom PromptLabUser model) and utilities

### Tech Stack

- **Backend**: Django 5.0 + Django REST Framework
- **Frontend**: Django Templates + HTMX + Bootstrap 4 + custom JavaScript
- **Database**: PostgreSQL (production), SQLite (development)
- **Cache/Queue**: Redis + Celery + django-celery-beat
- **Web Server**: Gunicorn + Nginx (production)
- **Authentication**: django-allauth (Google OAuth)

### Key Dependencies

- `datasets~=2.19`: HuggingFace datasets integration
- `django-htmx~=1.17`: Dynamic UI updates
- `django-taggit~=5.0`: Tagging system for prompts
- `huggingface_hub~=0.23`: Dataset metadata and API
- `django-redis~=5.4`: Redis caching
- `celery`: Background task processing

## Development Setup

```bash
# 1. Install Redis
sudo apt-get install redis
sudo service redis-server restart

# 2. Create .env file (see README.md for credentials)

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements_dev.txt
pre-commit install

# 4. Run migrations
cd promptlab
python manage.py migrate sites
python manage.py migrate

# 5. Create superusers
python manage.py import_superusers admins.yml

# 6. Setup Google authentication
python manage.py setup_allauth

# 7. Run development server
python manage.py runserver

# 8. (Optional) Run Celery for background tasks
celery -A promptlab worker -l info &
celery -A promptlab beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler &
```

## Common Commands

### Running Tests
```bash
python manage.py test
```

### Database Operations
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Database shell
python manage.py dbshell
```

### Static Files
```bash
# Collect static files (production)
python manage.py collectstatic --noinput
```

### Custom Management Commands
```bash
# Sync datasets from HuggingFace via Google Sheets
python manage.py sync_with_hf \
    --sheet_id <SHEET_ID> \
    --sheet_name final-list \
    --example_template_column example_template \
    --example_template_created_by_column example_template_created_by \
    --example_template_subset_column subset \
    --answer_choices_column answer_choices \
    --is_single_classification_column is_single_classification \
    --target_column target_column \
    --clear_datasets False

# Import superusers from YAML
python manage.py import_superusers admins.yml

# Setup Google OAuth provider
python manage.py setup_allauth
```

### Code Quality
```bash
# Run pre-commit hooks manually
pre-commit run --all-files

# Individual tools
ruff check .
black .
isort .
djhtml templates/
```

## Key Architecture Patterns

### Caching Strategy

Heavy use of Redis caching via custom `@redis_cache()` decorator to avoid HuggingFace API rate limits:

```python
@redis_cache()
def get_split_samples(dataset_object, split, subset, cache_dir, ...):
    # Caches dataset samples from HuggingFace

@redis_cache()
def collect_dataset_configs_details(dataset_object):
    # Caches dataset configuration metadata
```

### Multi-tenancy via Projects

`PromptingProject` model provides isolation:
- Owner and members (prompters/reviewers)
- Project-specific datasets
- Secret key for API authentication
- Automated dataset distribution among members

### Data Model Hierarchy

```
PromptingProject
    ├─ Dataset (from HuggingFace)
    │   ├─ Prompt (template)
    │   │   └─ child prompts (AI-generated variants)
    │   └─ Tasks (ManyToMany)
    └─ PromptReviewAction (workflow tracking)
```

### Frontend Communication Patterns

1. **Server-side rendering**: Django templates with crispy-forms
2. **HTMX**: Partial template updates for dynamic lists
3. **REST API**: Token-based (project secret key) for external integrations
4. **AJAX/JS**: OpenRouter API testing, dataset validation

### Authentication Layers

1. **Django AllAuth**: Google OAuth for user login
2. **Custom permissions**: Project membership + role-based (Owner/Prompter/Reviewer)
3. **API auth**: `HasProjectSecretKey` permission class validates project secret in requests

### Background Tasks (Celery)

- Dataset metadata refresh
- HuggingFace synchronization
- Cache invalidation
- Parallel dataset processing

## Configuration

### Settings Files

- `settings.py`: Development (DEBUG=True, SQLite/PostgreSQL, local Redis)
- `production_settings.py`: Production (DEBUG=False, PostgreSQL, remote Redis, SendGrid email)

### Environment Variables

Required in `.env`:
```bash
SUPERUSER_PASSWORD=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Development database
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=

# Production (Railway/Docker)
POSTGRES_NAME=
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_HOST=
POSTGRES_PORT=
REDIS_HOST=
REDIS_PORT=
REDIS_USER=
REDIS_PASSWORD=
SENDGRID_API_KEY=
SERVER_IP=
```

## Deployment

### Docker (docker-compose.yml)
```bash
docker-compose up -d
```

Services: nginx (port 8080), server (Django+Gunicorn), db (PostgreSQL), redis

### Production (Railway)

The `deploy.sh` script handles:
1. Virtual environment setup
2. Dependencies installation
3. Database migrations
4. Superuser creation
5. Google OAuth setup
6. Static file collection
7. Celery beat startup
8. Gunicorn launch (2 workers, 2 threads, 150s timeout)

## API Usage

REST API endpoints require project secret key authentication.

### Create Prompt via API

```python
import requests

response = requests.post(
    "https://promptlab.up.railway.app/api/prompt/create",
    headers={"Content-Type": "application/json"},
    json={
        "name": "Test Prompt",
        "template": "Translate {text} to {language}",
        "dataset_huggingface_name": "arbml/watan_2004",
        "dataset_subset": "",  # optional
        "project_secret_key": "YOUR_KEY",  # from project admin
        "created_by": "username",
        "tags": ["AI generated"],  # optional
        "text_direction": "rtl",  # optional: rtl or ltr
        "answer_choices": '[{"value": "choice1"}]'  # JSON string
    }
)
```

Find project secret key in Django admin: `/admin/prompt/promptingproject`

## Important Code Locations

- **Redis caching decorator**: `prompt/utils.py` - `@redis_cache()`
- **HuggingFace integration**: `prompt/utils.py` - dataset fetching and metadata
- **API authentication**: `api/permissions.py` - `HasProjectSecretKey`
- **Custom user model**: `core/models.py` - `PromptLabUser`
- **Review workflow**: `prompt/models.py` - `PromptReviewAction`, `ReviewStatus`
- **Dataset distribution**: `prompt/models.py` - `PromptingProject.distribute_datasets_to_all_members()`
- **Management commands**: `prompt/management/commands/` and `core/management/commands/`

## Development Notes

- **Worker memory management**: Celery configured with memory limits and auto-recycling for large datasets
- **Dataset size limit**: Max 1GB enforced in validation
- **Prompt templates**: Use Jinja2 syntax with dataset column placeholders
- **RTL/LTR support**: Text direction field for Arabic and other languages
- **AI integration**: External tools (templator) for prompt generation; OpenRouter for LLM testing
- **Prompt versioning**: Modifications tracked in `PromptReviewAction.modifications_json`
