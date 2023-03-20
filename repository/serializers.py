from rest_framework.serializers import ModelSerializer

from repository.models import Repository
from user.serializers import UserInSerializer


class RepositorySerializer(ModelSerializer):
    user = UserInSerializer(many=False, read_only=True)

    class Meta:
        fields = "__all__"
        model = Repository
        depth = 1
