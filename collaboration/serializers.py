from rest_framework.serializers import ModelSerializer

from collaboration.models import Comment, PullRequest


class PullRequestSerializer(ModelSerializer):
    class Meta:
        model = PullRequest
        fields = "__all__"


class CommentSerializer(ModelSerializer):
    class Meta:
        model = Comment
        fields = "__all__"
