import os
import shutil
from typing import Optional

from django.db import transaction
from django.http import HttpRequest
from git.repo import Repo
from rest_framework import status, viewsets
from rest_framework.response import Response

from fork.models import Fork
from fork.serializers import ForkSerializer
from project.settings import REPO_ROOT
from repository.models import Repository


class ForkViewSet(viewsets.ModelViewSet):
    queryset = Fork.objects.all()
    serializer_class = ForkSerializer

    @transaction.atomic
    def create(self, request: HttpRequest) -> Response:
        repository = Repository.objects.get(pk=request.data["repository"])

        Fork.objects.create(
            repository=repository,
            user=request.user,
        )

        source_dir = repository.path
        target_dir = os.path.join(REPO_ROOT, request.user.username, repository.name)

        shutil.copytree(source_dir, target_dir)
        shutil.rmtree(os.path.join(target_dir, ".git"))

        repo = Repo.init(target_dir)
        repo.index.add(["*"])
        repo.index.commit("initial commit")

        return Response(status=status.HTTP_201_CREATED)

    @transaction.atomic
    def destroy(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        repository = Repository.objects.get(pk=pk)
        Fork.objects.get(repository=repository, user=request.user).delete()

        target_dir = os.path.join(REPO_ROOT, request.user.username, repository.name)
        shutil.rmtree(target_dir)

        return Response(status=status.HTTP_200_OK)
