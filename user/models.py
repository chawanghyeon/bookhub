from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id = models.BigAutoField(primary_key=True, unique=True)
    username = models.EmailField(unique=True)

    def __str__(self):
        return self.first_name

    class Meta:
        app_label = "user"
