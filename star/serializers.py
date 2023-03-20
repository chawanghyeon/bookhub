from rest_framework.serializers import ModelSerializer

from star.models import Star


class StarSerializer(ModelSerializer):
    class Meta:
        fields = "__all__"
        model = Star
        depth = 1
