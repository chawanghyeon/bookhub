from rest_framework.serializers import ModelSerializer

from pullrequests.models import PullRequest


class PullRequestSerializer(ModelSerializer):
    class Meta:
        model = PullRequest
        fields = "__all__"
