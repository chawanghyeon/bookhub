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
        pull_request = PullRequest.objects.get(pk=pk)

        target_repo = Repo(pull_request.target_repository.path)
        source_repo = Repo(pull_request.source_repository.path)

        source_commit = source_repo.head.commit
        source_tree = source_commit.tree
        target_commit = target_repo.head.commit
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

    @action(detail=True, methods=["post"], url_path="approve", url_name="approve")
    @transaction.atomic
    def approve_pull_request(
        self, request: HttpRequest, pk: Optional[str] = None
    ) -> Response:
        pull_request = PullRequest.objects.get(pk=pk)

        if pull_request.target_repository.superuser != request.user:
            return Response(
                status=status.HTTP_403_FORBIDDEN,
            )

        pull_request.status = "merged"
        pull_request.save()

        target_repo = Repo(pull_request.target_repository.path)
        target_repo.git.checkout(pull_request.target_branch)

        source_repo = Repo(pull_request.source_repository.path)
        source_repo.git.checkout(pull_request.source_branch)

        target_remote = target_repo.create_remote(
            "source", url=f"file://{source_repo.working_dir}"
        )
        target_remote.fetch()

        target_branch = target_repo.heads[pull_request.target_branch]
        source_branch = (
            f"{target_remote.name}/{source_repo.heads[pull_request.source_branch]}"
        )
        try:
            target_repo.git.merge(source_branch)
        except Exception as e:
            data = {"error": str(e)}
            temp = target_repo.index.unmerged_blobs()
            file_path = list(temp.keys())[0]
            blob_list = temp[file_path]
            path = blob_list[0][1].abspath
            with open(path, "r") as f:
                data["file"] = f.read()
            return Response(
                data,
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_repo.index.add(["*"])
        target_repo.index.commit("Merged pull request")

        target_remote.push(refspec=f"{target_branch.name}:{target_branch.name}")
        target_repo.delete_remote(target_remote)

        return Response(
            status=status.HTTP_200_OK,
        )
