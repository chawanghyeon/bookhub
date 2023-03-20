from django.db import models
from user.models import User
from repository.models import Repository

# Create your models here.
class PullRequest(models.Model):
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    source_branch = models.CharField(max_length=255)
    destination_branch = models.CharField(max_length=255)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="pull_requests"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=20,
        choices=(
            ("open", "Open"),
            ("closed", "Closed"),
            ("merged", "Merged"),
        ),
    )


class Comment(models.Model):
    id = models.BigAutoField(primary_key=True, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    repository = models.ForeignKey(
        Repository, on_delete=models.CASCADE, related_name="comments"
    )
    commit = models.CharField(max_length=255)
    text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return self.user.first_name + " " + self.pull_request.title

    def __str__(self):
        return self.user.first_name + " " + self.pull_request.title
