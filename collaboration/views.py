from typing import Optional

from django.db import transaction
from django.http import HttpRequest
from git.repo import Repo
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from collaboration.models import Comment, PullRequest
from collaboration.serializers import CommentSerializer, PullRequestSerializer


class CommentViewSet(viewsets.ModelViewSet):
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

        comment = Comment.objects.get(pk=pk)
        comment.text = text
        comment.save()

        return Response(
            status=status.HTTP_200_OK,
        )

    def destroy(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        Comment.objects.filter(pk=pk).delete()

        return Response(
            status=status.HTTP_200_OK,
        )


class PullRequestViewSet(viewsets.ModelViewSet):
    queryset = PullRequest.objects.all()
    serializer_class = PullRequestSerializer

    @transaction.atomic
    def create(self, request: HttpRequest) -> Response:
        serializer = PullRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        PullRequest.objects.filter(pk=pk).delete()

        return Response(
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="check", url_name="check")
    def check_difference(
        self, request: HttpRequest, pk: Optional[str] = None
    ) -> Response:
        pulllrequest = PullRequest.objects.get(pk=pk)
        source_repository = pulllrequest.source_repository
        target_repository = pulllrequest.target_repository

        source_repo = Repo(source_repository.path)
        target_repo = Repo(target_repository.path)

        source_commit = source_repo.head.commit
        source_tree = source_commit.tree
        target_commit = target_repo.commit(pulllrequest.commit)
        target_tree = target_commit.tree

        diff_index = target_tree.diff(source_tree)
        working_tree = []

        for diff in diff_index:
            a_blob = diff.a_blob
            b_blob = diff.b_blob
            if a_blob and b_blob:
                working_tree.append(target_repo.git.diff(a_blob.hexsha, b_blob.hexsha))

        return Response(
            working_tree,
            status=status.HTTP_200_OK,
        )
