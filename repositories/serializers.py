from rest_framework.serializers import ModelSerializer

from repositories.models import Repository


class RepositorySerializer(ModelSerializer):
    class Meta:
        fields = ("id", "name", "tags")
        model = Repository
        depth = 1
