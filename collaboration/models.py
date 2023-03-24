from django.db import models

from repository.models import Repository
from user.models import User


class PullRequest(models.Model):
    title = models.CharField(max_length=255)
    text = models.CharField(max_length=255)
    source_branch = models.CharField(max_length=255)
    source_repository = models.ForeignKey(
        Repository, on_delete=models.CASCADE, related_name="source_pr"
    )
    target_branch = models.CharField(max_length=255)
    target_repository = models.ForeignKey(
        Repository, on_delete=models.CASCADE, related_name="target_pr"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=20,
        choices=(
            ("open", "Open"),
            ("closed", "Closed"),
            ("merged", "Merged"),
        ),
    )

    def __str__(self):
        return self.title


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
