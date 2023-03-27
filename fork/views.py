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
        source_repository = Repository.objects.get(pk=request.data["repository"])

        source_dir = source_repository.path
        target_dir = os.path.join(
            REPO_ROOT, request.user.username, source_repository.name
        )

        repo = Repo.clone_from(source_dir, target_dir)
        branch_name = "new-branch-name"
        new_branch = repo.create_head(branch_name)
        new_branch.checkout()

        target_repository = Repository.objects.create(
            name=source_repository.name,
            user=request.user,
            path=target_dir,
            fork=True,
        )

        target_repository.owners.add(request.user)

        Fork.objects.create(
            source_repository=source_repository,
            target_repository=target_repository,
            user=request.user,
        )

        return Response(status=status.HTTP_201_CREATED)

    @transaction.atomic
    def destroy(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        source_repository = Repository.objects.get(pk=pk)
        Fork.objects.get(
            source_repository=source_repository, user=request.user
        ).delete()

        target_dir = os.path.join(
            REPO_ROOT, request.user.username, source_repository.name
        )
        shutil.rmtree(target_dir)

        return Response(status=status.HTTP_200_OK)
