import json
import os
import shutil
from typing import Any, Optional

from django.http import Http404, HttpRequest
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

    def build_tree_dict(self, tree: Any) -> dict:
        result = {}
        for item in tree:
            if item.type == "blob":
                result[item.name] = "blob"
            elif item.type == "tree":
                result[item.name] = self.build_tree_dict(item)
        return result

    def get_tree_json(self, repo: Repo) -> str:
        tree = list(repo.iter_commits())[0].tree
        tree_dict = self.build_tree_dict(tree)
        tree_json = json.dumps(tree_dict)
        return tree_json

    def check_is_pullrequest_open(self, repository: Repository) -> bool:
        if PullRequest.objects.filter(
            source_repository=repository, status="open"
        ).exists():
            return True
        return False

    def create(self, request: HttpRequest) -> Response:
        def set_user_name(repo: Repo) -> None:
            config_writer = repo.config_writer()
            config_writer.set_value("user", "name", request.user.username)
            config_writer.release()

        def init_repo(repo_path: str, file_path: str) -> Repo:
            repo = Repo.init(repo_path)
            open(file_path, "w").close()
            repo.index.add("*")
            repo.index.commit("initial commit")
            set_user_name(repo)
            return repo

        def prepare_data(request: HttpRequest) -> tuple:
            name = request.data.get("name")
            repo_path = os.path.join(REPO_ROOT, request.user.username, name)
            file_path = os.path.join(repo_path, "README.txt")

            if not name:
                raise Http404

            return name, repo_path, file_path

        name, repo_path, file_path = prepare_data(request)

        repo = init_repo(repo_path, file_path)

        repository = Repository.objects.create(
            name=name,
            path=repo.working_tree_dir,
            user=request.user,
        )
        repository.owners.set([request.user])

        data = RepositorySerializer(repository).data
        data["tree"] = self.get_tree_json(repo)

        return Response(data, status=status.HTTP_201_CREATED)

    def retrieve(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        def check_readable(repository: Repository, request: HttpRequest) -> bool:
            if repository.private:
                if request.user in repository.owners.all():
                    return True
                return False

        def check_is_possible_to_pullrequest(
            repository: Repository, repo: Repo
        ) -> bool:
            if repository.fork:
                remote = repo.remotes.origin
                remote.fetch()
                remote_tree = remote.refs.main.commit.tree
                diff = remote_tree.diff(repo.head.commit.tree)
                if diff:
                    return True
                return False
            return False

        repository = Repository.objects.get(pk=pk)

        if check_readable(repository, request) is False:
            return Response(status=status.HTTP_403_FORBIDDEN)

        repo = Repo(repository.path)

        data = RepositorySerializer(repository).data
        data["tree"] = self.get_tree_json(repo)

        if check_is_possible_to_pullrequest(repository, repo):
            data["pullrequest"] = True
        else:
            data["pullrequest"] = False

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], url_path="file", url_name="file")
    def partial_update_file(
        self, request: HttpRequest, pk: Optional[str] = None
    ) -> Response:
        def prepare_data(request: HttpRequest) -> tuple:
            txt_file = request.data.get("file")
            message = request.data.get("message")
            path = request.data.get("path")

            if not txt_file or not message or not path:
                raise Http404

            return txt_file, message, path

        def write_file(txt_file: Any, path: str) -> None:
            content = txt_file.read()
            with open(path, "w") as f:
                f.write(content.decode("utf-8"))

        repository = Repository.objects.get(pk=pk)

        if self.check_is_pullrequest_open(repository):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        txt_file, message, path = prepare_data(request)

        path = os.path.join(REPO_ROOT, path)
        write_file(txt_file, path)

        repo = Repo(repository.path)
        repo.index.add([path])
        repo.index.commit(message)

        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], url_path="structure", url_name="structure")
    def partial_update_structure(
        self, request: HttpRequest, pk: Optional[str] = None
    ) -> Response:
        def prepare_data(request: HttpRequest) -> tuple:
            structure = request.data.get("structure")
            message = request.data.get("message")

            if not structure or not message:
                raise Http404

            return structure, message

        def get_blobs_dict(repo: Repo) -> dict:
            blobs_dict = {}
            for file_path in repo.git.ls_files().split("\n"):
                file_path = os.path.join(repository.path, file_path)
                with open(file_path, "r") as f:
                    blobs_dict[os.path.basename(file_path)] = f.read()
            return blobs_dict

        def reset_directory(repository: Repository) -> None:
            contents = os.listdir(repository.path)
            contents.remove(".git")

            for item in contents:
                item_path = os.path.join(repository.path, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)

        def build_directory(tree, path):
            for item in tree:
                item_path = os.path.join(path, item)
                if tree[item] == "blob":
                    content = blobs_dict.get(item, "")
                    with open(item_path, "w") as f:
                        f.write(content)
                else:
                    os.makedirs(item_path)
                    build_directory(tree[item], item_path)

        repository = Repository.objects.get(pk=pk)

        if self.check_is_pullrequest_open(repository):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        structure, message = prepare_data(request)

        repo = Repo(repository.path)
        blobs_dict = get_blobs_dict(repo)
        reset_directory(repository)

        structure = json.loads(structure)

        build_directory(structure, repository.path)

        repo.index.add("*")
        repo.index.commit(message)

        return Response(status=status.HTTP_200_OK)

    def destroy(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        repository = Repository.objects.get(pk=pk)

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

    @action(detail=True, methods=["patch"], url_path="rename", url_name="rename")
    def update_name(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        repository = Repository.objects.get(pk=pk)
        old_name = request.data.get("old_name")
        new_name = request.data.get("new_name")
        message = request.data.get("message")

        if not old_name or not new_name or not message:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        old_name = os.path.join(repository.path, old_name)
        new_name = os.path.join(repository.path, new_name)

        os.rename(old_name, new_name)

        repo = Repo(repository.path)
        repo.index.add([new_name])
        repo.index.commit(message)

        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="branch", url_name="branch")
    def create_branch(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        repository = Repository.objects.get(pk=pk)
        branch_name = request.data.get("branch_name")
        message = request.data.get("message")

        if not branch_name or not message:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        repo = Repo(repository.path)
        repo.git.checkout("-b", branch_name)
        repo.index.add("*")
        repo.index.commit(message)

        return Response(status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="branch", url_name="branch")
    def delete_branch(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        repository = Repository.objects.get(pk=pk)
        repo = Repo(repository.path)
        branch_name = request.data.get("branch_name")

        if branch_name is None or branch_name == "main":
            return Response(status=status.HTTP_400_BAD_REQUEST)

        repo.git.branch("-D", branch_name)

        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], url_path="branch", url_name="branch")
    def update_branch(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        repository = Repository.objects.get(pk=pk)
        branch_name = request.data.get("branch_name")
        message = request.data.get("message")

        if branch_name is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        repo = Repo(repository.path)
        repo.git.checkout(branch_name)
        repo.index.add("*")
        repo.index.commit(message)

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
        def get_working_tree(repo: Repo, commit_hash: str) -> list:
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

            return working_tree

        commit_hash = request.query_params.get("commit_hash", None)
        repository = Repository.objects.get(pk=pk)
        repo = Repo(repository.path)

        if commit_hash is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        working_tree = get_working_tree(repo, commit_hash)

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
        commit_hash = request.data.get("commit_hash")

        if commit_hash is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        repo = Repo(repository.path)
        repo.git.reset("--hard", commit_hash)

        return Response(status=status.HTTP_200_OK)
