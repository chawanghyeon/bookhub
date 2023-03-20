from django.db import models
from user.models import User
from repository.models import Repository


class Star(models.Model):
    id = models.BigAutoField(primary_key=True, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE)

    def __unicode__(self):
        return self.user.first_name + " " + self.repository.name

    def __str__(self):
        return self.user.first_name + " " + self.repository.name
