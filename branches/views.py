from typing import Optional

from django.http import HttpRequest
from git.repo import Repo
from rest_framework import status, viewsets
from rest_framework.response import Response

from repositories.models import Repository
from repositories.serializers import RepositorySerializer


class BranchViewSet(viewsets.ModelViewSet):
    queryset = Repository.objects.all()
    serializer_class = RepositorySerializer

    def create(self, request: HttpRequest) -> Response:
        repository = Repository.objects.get(pk=request.data.get("repository"))
        branch_name = request.data.get("branch_name")
        message = request.data.get("message")

        if not branch_name or not message:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        repo = Repo(repository.path)
        repo.git.checkout("-b", branch_name)
        repo.index.add("*")
        repo.index.commit(message)

        return Response(status=status.HTTP_201_CREATED)

    def destroy(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        repository = Repository.objects.get(pk=pk)
        repo = Repo(repository.path)
        branch_name = request.data.get("branch_name")

        if branch_name is None or branch_name == "main":
            return Response(status=status.HTTP_400_BAD_REQUEST)

        repo.git.branch("-D", branch_name)

        return Response(status=status.HTTP_200_OK)

    def update(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
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

    def list(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        repository = Repository.objects.get(pk=request.query_params.get("repository"))
        repo = Repo(repository.path)

        branch_list = repo.git.branch().split("\n")
        branch_list = [branch.strip() for branch in branch_list]

        return Response(branch_list, status=status.HTTP_200_OK)
