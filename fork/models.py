from django.db import models

from repository.models import Repository
from user.models import User


class Fork(models.Model):
    id = models.BigAutoField(primary_key=True, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    source_repository = models.ForeignKey(
        Repository, on_delete=models.CASCADE, related_name="source_fork"
    )
    target_repository = models.ForeignKey(
        Repository, on_delete=models.CASCADE, related_name="target_fork"
    )

    def __str__(self):
        return self.user.first_name + " " + self.repository.name
