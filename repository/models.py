from django.db import models

from user.models import User


class Tag(models.Model):
    id = models.BigAutoField(primary_key=True, unique=True)
    name = models.CharField(max_length=100, unique=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name


class Repository(models.Model):
    id = models.BigAutoField(primary_key=True, unique=True)
    name = models.CharField(max_length=100)
    user = models.ForeignKey(
        User, related_name="repositories_superuser", on_delete=models.CASCADE
    )
    owners = models.ManyToManyField(User, related_name="repositories")
    members = models.ManyToManyField(
        User, related_name="repositories_member", blank=True
    )
    path = models.CharField(max_length=100, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(Tag, blank=True)
    star_count = models.IntegerField(default=0)
    fork_count = models.IntegerField(default=0)
    private = models.BooleanField(default=False)
    fork = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name
