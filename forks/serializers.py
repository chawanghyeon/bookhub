from rest_framework.serializers import ModelSerializer

from forks.models import Fork


class ForkSerializer(ModelSerializer):
    class Meta:
        model = Fork
        fields = "__all__"
        depth = 1
