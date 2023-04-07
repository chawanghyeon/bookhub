from typing import Optional

from django.db import transaction
from django.http import HttpRequest
from git.repo import Repo
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from pullrequests.models import PullRequest
from pullrequests.serializers import PullRequestSerializer


class PullRequestViewSet(viewsets.ModelViewSet):
    queryset = PullRequest.objects.all()
    serializer_class = PullRequestSerializer

    @transaction.atomic
    def create(self, request: HttpRequest) -> Response:
        serializer = PullRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        PullRequest.objects.filter(pk=pk).delete()

        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="check", url_name="check")
    def check_difference(
        self, request: HttpRequest, pk: Optional[str] = None
    ) -> Response:
        def get_working_tree(target_repo: Repo, source_repo: Repo) -> list:
            source_commit = source_repo.head.commit
            source_tree = source_commit.tree
            target_commit = target_repo.head.commit
            target_tree = target_commit.tree

            diff_index = source_tree.diff(target_tree)
            working_tree = []

            for diff in diff_index:
                a_blob = diff.a_blob
                b_blob = diff.b_blob
                if a_blob and b_blob:
                    working_tree.append(
                        source_repo.git.diff(a_blob.hexsha, b_blob.hexsha)
                    )

            return working_tree

        pull_request = PullRequest.objects.get(pk=pk)

        target_repo = Repo(pull_request.target_repository.path)
        source_repo = Repo(pull_request.source_repository.path)

        working_tree = get_working_tree(target_repo, source_repo)

        return Response(working_tree, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="approve", url_name="approve")
    def approve_pull_request(
        self, request: HttpRequest, pk: Optional[str] = None
    ) -> Response:
        def prepare_merging(pullrequest: PullRequest) -> tuple:
            target_repo = Repo(pullrequest.target_repository.path)
            target_repo.git.checkout(pullrequest.target_branch)

            source_repo = Repo(pullrequest.source_repository.path)
            source_repo.git.checkout(pullrequest.source_branch)

            target_remote = target_repo.create_remote(
                "source", url=f"file://{source_repo.working_dir}"
            )
            target_remote.fetch()

            source_branch = (
                f"{target_remote.name}/{source_repo.heads[pullrequest.source_branch]}"
            )

            return target_repo, target_remote, source_branch

        def merge(target_repo: Repo, source_branch: str) -> tuple:
            try:
                target_repo.git.merge(source_branch)
                return True, None
            except Exception as e:
                data = {"error": str(e)}
                temp = target_repo.index.unmerged_blobs()
                file_path = list(temp.keys())[0]
                blob_list = temp[file_path]
                path = blob_list[0][1].abspath
                with open(path, "r") as f:
                    data["file"] = f.read()
                return False, data

        def commit(target_repo: Repo) -> None:
            target_repo.index.add(["*"])
            target_repo.index.commit("Merged pull request")

        def push_and_delete(
            target_repo: Repo, target_remote: Repo, target_branch: str
        ) -> None:
            target_remote.push(refspec=f"{target_branch}:{target_branch}")
            target_repo.delete_remote(target_remote)

        pull_request = PullRequest.objects.get(pk=pk)

        if pull_request.target_repository.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)

        pull_request.status = "merged"
        pull_request.save()

        target_repo, target_remote, source_branch = prepare_merging(pull_request)
        is_merged, data = merge(target_repo, source_branch)

        if not is_merged:
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        commit(target_repo)
        push_and_delete(target_repo, target_remote, pull_request.target_branch)

        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="reject", url_name="reject")
    def reject_pull_request(
        self, request: HttpRequest, pk: Optional[str] = None
    ) -> Response:
        pull_request = PullRequest.objects.get(pk=pk)

        if pull_request.target_repository.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)

        pull_request.status = "closed"
        pull_request.save()

        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="resolve", url_name="resolve")
    def resolve_conflict(
        self, request: HttpRequest, pk: Optional[str] = None
    ) -> Response:
        def commit(target_repo: Repo, path: str) -> None:
            target_repo.index.remove([path])
            target_repo.index.add([path])
            target_repo.index.commit("Resolved conflict")

        def resolve(target_repo: Repo, filename: str, choice: str) -> None:
            unmerged_blobs = target_repo.index.unmerged_blobs()[filename]
            path = unmerged_blobs[0][1].abspath

            with open(path, "w") as f:
                if choice == "HEAD":
                    f.write(unmerged_blobs[1][1].data_stream.read().decode("utf-8"))
                elif choice == "REMOTE":
                    f.write(unmerged_blobs[2][1].data_stream.read().decode("utf-8"))

            commit(target_repo, path)

        choice = request.data.get("choice")
        filename = request.data.get("filename")

        if not choice or not filename:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        pull_request = PullRequest.objects.get(pk=pk)

        if pull_request.target_repository.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)

        target_repo = Repo(pull_request.target_repository.path)
        resolve(target_repo, filename, choice)

        return Response(status=status.HTTP_200_OK)
