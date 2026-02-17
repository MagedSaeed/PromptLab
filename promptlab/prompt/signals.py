from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

User = get_user_model()


@receiver(user_logged_in)
def user_logged_in_signal(sender, request, user, **kwargs):
    prompting_projects = (
        user.prompting_projects.all() | user.owned_prompting_projects.all()
    )

    # Distribute datasets
    for project in prompting_projects:
        project.distribute_datasets()
