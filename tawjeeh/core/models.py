from django.contrib.auth.models import AbstractUser

# Create your models here.

# accounts/models.py


class TawjeehUser(AbstractUser):
    # Override any methods from AbstractUser if needed
    def __str__(self):
        return self.username
