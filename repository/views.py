import json
import os
import shutil
from typing import Optional

from django.db import transaction
from django.http import Http404, HttpRequest
from git.exc import GitCommandError
from git.repo import Repo
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response

from project.settings import REPO_ROOT
from pullrequest.models import PullRequest
from repository.models import Repository
from repository.serializers import RepositorySerializer


class RepositoryViewSet(viewsets.ModelViewSet):
    queryset = Repository.objects.all()
    serializer_class = RepositorySerializer

    @transaction.atomic
    def create(self, request: HttpRequest) -> Response:
        name = request.data.get("name")
        repo_dir = os.path.join(REPO_ROOT, name)
        file_name = os.path.join(repo_dir, "README.txt")
        repo = Repo.init(repo_dir)
        open(
            file_name,
            "w",
        ).close()
        repo.index.add("*")
        repo.index.commit("initial commit")

        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", request.user.username)
        config_writer.release()

        repository = Repository.objects.create(
            name=name,
            path=repo.working_tree_dir,
            superuser=request.user,
        )
        repository.owners.set([request.user])

        tree = list(repo.iter_commits())[0].tree

        def build_tree_dict(tree):
            result = {}
            for item in tree:
                if item.type == "blob":
                    result[item.name] = "blob"
                elif item.type == "tree":
                    result[item.name] = build_tree_dict(item)
            return result

        tree_dict = build_tree_dict(tree)
        tree_json = json.dumps(tree_dict)

        data = RepositorySerializer(repository).data
        data["tree"] = tree_json

        return Response(data, status=status.HTTP_201_CREATED)

    def retrieve(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        repository = Repository.objects.get(pk=pk)
        if repository.private:
            return Response(
                status=status.HTTP_403_FORBIDDEN,
            )
        repo = Repo(repository.path)

        commits = list(repo.iter_commits())
        tree = commits[0].tree

        def build_tree_dict(tree):
            result = {}
            for item in tree:
                if item.type == "blob":
                    result[item.name] = "blob"
                elif item.type == "tree":
                    result[item.name] = build_tree_dict(item)
            return result

        tree_dict = build_tree_dict(tree)
        tree_json = json.dumps(tree_dict)

        data = RepositorySerializer(repository).data
        data["tree"] = tree_json

        if repository.fork:
            remote = repo.remotes.origin
            remote.fetch()
            remote_tree = remote.refs.main.commit.tree
            diff = remote_tree.diff(repo.head.commit.tree)
            if diff:
                data["pullrequest"] = True
            else:
                data["pullrequest"] = False

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], url_path="file", url_name="file")
    def partial_update_file(
        self, request: HttpRequest, pk: Optional[str] = None
    ) -> Response:
        repository = Repository.objects.get(pk=pk)
        if repository.superuser != request.user:
            return Response(
                status=status.HTTP_403_FORBIDDEN,
            )
        if (
            repository.fork
            and PullRequest.objects.filter(
                repository=repository, status="open"
            ).exists()
        ):
            return Response(
                status=status.HTTP_403_FORBIDDEN,
            )
        txt_file = request.data.get("file", None)
        message = request.data.get("message", None)

        if txt_file is not None:
            # read the contents of the uploaded file
            content = txt_file.read()
            file_name = txt_file.name
            file_path = None

            try:
                repo = Repo(repository.path)
                for file_path in repo.git.ls_files().split("\n"):
                    if file_path.endswith(file_name):
                        file_path = file_path
                        break

                file_path = os.path.join(repository.path, file_path)

                with open(file_path, "w") as f:
                    f.write(content.decode("utf-8"))

                index = repo.index
                index.add([file_name])
                index.commit(message)

            except GitCommandError:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], url_path="structure", url_name="structure")
    def partial_update_structure(
        self, request: HttpRequest, pk: Optional[str] = None
    ) -> Response:
        repository = Repository.objects.get(pk=pk)
        if repository.superuser != request.user:
            return Response(
                status=status.HTTP_403_FORBIDDEN,
            )
        if (
            repository.fork
            and PullRequest.objects.filter(
                repository=repository, status="open"
            ).exists()
        ):
            return Response(
                status=status.HTTP_403_FORBIDDEN,
            )
        repo = Repo(repository.path)
        structure = request.data.get("structure", None)
        message = request.data.get("message", None)

        if structure is None:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
            )

        blobs_dict = {}
        for file_path in repo.git.ls_files().split("\n"):
            file_path = os.path.join(repository.path, file_path)
            with open(file_path, "r") as f:
                blobs_dict[os.path.basename(file_path)] = f.read()

        contents = os.listdir(repository.path)
        contents.remove(".git")

        for item in contents:
            item_path = os.path.join(repository.path, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        structure = json.loads(structure)

        def build_tree(tree, path):
            for item in tree:
                if tree[item] == "blob":
                    file_path = os.path.join(path, item)
                    if item in blobs_dict:
                        with open(file_path, "w") as f:
                            f.write(blobs_dict[item])
                    else:
                        open(
                            file_path,
                            "w",
                        ).close()
                else:
                    dir_path = os.path.join(path, item)
                    os.mkdir(dir_path)
                    build_tree(tree[item], dir_path)

        build_tree(structure, repository.path)

        index = repo.index
        index.add("*")
        index.commit(message)

        return Response(status=status.HTTP_200_OK)

    def destroy(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        repository = Repository.objects.get(pk=pk)
        if repository.superuser != request.user:
            return Response(
                status=status.HTTP_403_FORBIDDEN,
            )

        repository.delete()
        shutil.rmtree(repository.path)
        return Response(status=status.HTTP_200_OK)

    def list(self, request: HttpRequest) -> Response:
        pagenator = CursorPagination()

        query = Repository.objects.all().order_by("star_count")
        query = pagenator.paginate_queryset(query, request)

        if query is None:
            raise Http404

        return pagenator.get_paginated_response(
            RepositorySerializer(query, many=True).data
        )

    @action(detail=False, methods=["get"], url_path="tag", url_name="tag")
    def search_by_tag(self, request: HttpRequest) -> Response:
        pagenator = CursorPagination()

        tag = request.query_params.get("tag")
        query = Repository.objects.filter(tags__name=tag).order_by("star_count")
        query = pagenator.paginate_queryset(query, request)

        if query is None:
            raise Http404

        return pagenator.get_paginated_response(
            RepositorySerializer(query, many=True).data
        )

    @action(detail=False, methods=["get"], url_path="name", url_name="name")
    def search_by_name(self, request: HttpRequest) -> Response:
        pagenator = CursorPagination()

        name = request.query_params.get("name")
        query = Repository.objects.filter(name__icontains=name).order_by("star_count")
        query = pagenator.paginate_queryset(query, request)

        if query is None:
            raise Http404

        return pagenator.get_paginated_response(
            RepositorySerializer(query, many=True).data
        )

    @action(detail=True, methods=["patch"], url_path="rename", url_name="rename")
    def update_name(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        repository = Repository.objects.get(pk=pk)
        repo = Repo(repository.path)
        old_name = request.data.get("old_name", None)
        new_name = request.data.get("new_name", None)
        message = request.data.get("message", None)

        if old_name is None or new_name is None:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
            )

        folder_path = os.path.join(repository.path, old_name)
        new_folder_path = os.path.join(repository.path, new_name)

        os.rename(folder_path, new_folder_path)

        index = repo.index
        index.add([new_name])
        index.commit(message)

        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="branch", url_name="branch")
    def create_branch(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        repository = Repository.objects.get(pk=pk)
        repo = Repo(repository.path)
        branch_name = request.data.get("branch_name", None)
        message = request.data.get("message", None)

        if branch_name is None:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
            )

        repo.git.checkout("-b", branch_name)
        index = repo.index
        index.add("*")
        index.commit(message)

        return Response(status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="branch", url_name="branch")
    def delete_branch(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        repository = Repository.objects.get(pk=pk)
        repo = Repo(repository.path)
        branch_name = request.data.get("branch_name", None)

        if branch_name is None:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
            )

        if branch_name == "master":
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
            )

        if branch_name not in repo.git.branch():
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
            )

        if branch_name == repo.active_branch.name:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
            )

        repo.git.branch("-D", branch_name)

        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], url_path="branch", url_name="branch")
    def update_branch(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        repository = Repository.objects.get(pk=pk)
        repo = Repo(repository.path)
        branch_name = request.data.get("branch_name", None)
        message = request.data.get("message", None)

        if branch_name is None:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
            )

        if branch_name not in repo.git.branch():
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
            )

        repo.git.checkout(branch_name)
        index = repo.index
        index.add("*")
        index.commit(message)

        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="branch", url_name="branch")
    def list_branches(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        repository = Repository.objects.get(pk=pk)
        repo = Repo(repository.path)

        branch_list = repo.git.branch().split("\n")
        branch_list = [branch.strip() for branch in branch_list]

        return Response(branch_list, status=status.HTTP_200_OK)

    @action(
        detail=True, methods=["get"], url_path="workingtree", url_name="workingtree"
    )
    def retrieve_working_tree(
        self, request: HttpRequest, pk: Optional[str] = None
    ) -> Response:
        commit_hash = request.query_params.get("commit_hash", None)
        repository = Repository.objects.get(pk=pk)
        repo = Repo(repository.path)

        if commit_hash is None:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
            )

        head_commit = repo.commit(commit_hash)
        commit_date = head_commit.committed_datetime
        head_tree = head_commit.tree
        parent_commit = head_commit.parents[0]
        parent_tree = parent_commit.tree

        diff_index = parent_tree.diff(head_tree)
        working_tree = []

        for diff in diff_index:
            a_blob = diff.a_blob
            b_blob = diff.b_blob
            if a_blob and b_blob:
                working_tree.append(repo.git.diff(a_blob.hexsha, b_blob.hexsha))

        working_tree.append(commit_date)
        return Response(working_tree, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="commit", url_name="commit")
    def list_commits(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        repository = Repository.objects.get(pk=pk)
        repo = Repo(repository.path)
        commit_list = []

        for commit in repo.iter_commits():
            commit_list.append(
                {
                    "commit_hash": commit.hexsha,
                    "commit_date": commit.committed_datetime,
                    "commit_message": commit.message,
                }
            )

        return Response(commit_list, status=status.HTTP_200_OK)

    @action(detail=True, methods=["put"], url_path="rollback", url_name="rollback")
    def rollback_to_commit(
        self, request: HttpRequest, pk: Optional[str] = None
    ) -> Response:
        repository = Repository.objects.get(pk=pk)
        repo = Repo(repository.path)
        commit_hash = request.data.get("commit_hash", None)

        if commit_hash is None:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
            )

        repo.git.reset("--hard", commit_hash)

        return Response(status=status.HTTP_200_OK)
