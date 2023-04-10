from django.db import models

from repositories.models import Repository
from users.models import User


class Star(models.Model):
    id = models.BigAutoField(primary_key=True, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    repository = models.ForeignKey(
        Repository, on_delete=models.CASCADE, related_name="star"
    )

    def __str__(self):
        return self.user.first_name + " " + self.repository.name
