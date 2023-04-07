from typing import Optional

from django.http import HttpRequest
from rest_framework import status, viewsets
from rest_framework.response import Response

from comments.models import Comment
from comments.serializers import CommentSerializer


class CommentViewSet(viewsets.ViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer

    def create(self, request: HttpRequest) -> Response:
        text = request.data.get("text")
        commit_hash = request.data.get("commit")
        repository_id = request.data.get("repository")

        if not commit_hash or not repository_id:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
            )

        comment = Comment.objects.create(
            user=request.user,
            repository_id=repository_id,
            commit=commit_hash,
            text=text,
        )

        return Response(
            CommentSerializer(comment).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(
        self, request: HttpRequest, pk: Optional[str] = None
    ) -> Response:
        text = request.data.get("text")

        if not text:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
            )

        Comment.objects.filter(pk=pk).update(text=text)

        return Response(
            status=status.HTTP_200_OK,
        )

    def destroy(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        Comment.objects.filter(pk=pk).delete()

        return Response(
            status=status.HTTP_200_OK,
        )
