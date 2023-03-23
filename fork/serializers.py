from rest_framework.serializers import ModelSerializer

from fork.models import Fork


class ForkSerializer(ModelSerializer):
    class Meta:
        model = Fork
        fields = "__all__"
        depth = 1
