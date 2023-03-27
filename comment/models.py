from django.db import models

from repository.models import Repository
from user.models import User


class Comment(models.Model):
    id = models.BigAutoField(primary_key=True, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    repository = models.ForeignKey(
        Repository, on_delete=models.CASCADE, related_name="comments"
    )
    commit = models.CharField(max_length=255)
    text = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.first_name + " " + self.pull_request.title
