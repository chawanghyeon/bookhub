import json
import os
from typing import Optional

from django.db import transaction
from django.http import Http404, HttpRequest
from git.repo import Repo
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response

from project.settings import REPO_ROOT
from repository.models import Repository
from repository.serializers import RepositorySerializer


class RepositoryViewSet(viewsets.ModelViewSet):
    queryset = Repository.objects.all()
    serializer_class = RepositorySerializer

    @transaction.atomic
    def create(self, request: HttpRequest) -> Response:
        name = request.data.get("name")
        repo_dir = os.path.join(REPO_ROOT, name)
        repo = Repo.init(repo_dir)

        # Set the owner of the repository to the current user
        repo.config_writer().set_value("user", "name", request.user.username)
        repo.config_writer().set_value("user", "email", request.user.email)
        repo.config_writer().release()

        repository = Repository.objects.create(
            name=name,
            repo_dir=repo.working_tree_dir,
            superuser=request.user,
            owners=[request.user],
        )

        commits = list(repo.iter_commits())

        # Get the tree object for the most recent commit
        tree = commits[0].tree

        # Recursively print the structure of the tree
        def build_tree_dict(tree):
            result = {}
            for item in tree:
                if item.type == "blob":
                    result[item.name] = "blob"
                elif item.type == "tree":
                    result[item.name] = build_tree_dict(item)
            return result

        # Convert the tree dictionary to a JSON string
        tree_dict = build_tree_dict(tree)
        tree_json = json.dumps(tree_dict, indent=4)

        serializer = self.get_serializer(repository)
        data = serializer.data
        data["tree"] = tree_json

        return Response(data, status=status.HTTP_201_CREATED)

    def retrieve(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        repo = self.get_object()
        serializer = self.get_serializer(repo)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request: HttpRequest) -> Response:
        repo = self.get_object()

        # Update the repository name if it was provided in the request data
        name = request.data.get("name")
        if name:
            new_repo_dir = os.path.join(REPO_ROOT, name)
            os.rename(repo.repo_dir, new_repo_dir)
            repo.repo_dir = new_repo_dir

        # Update the owner of the repository if it was provided in the request data
        owner = request.data.get("owner")
        if owner:
            repo.owner = owner

        repo.save()

        serializer = self.get_serializer(repo)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request: HttpRequest) -> Response:
        repo = self.get_object()
        repo.repo_dir.rmtree()
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

    @action(detail=False, methods=["get"])
    def search(self, request: HttpRequest) -> Response:
        pagenator = CursorPagination()

        tag = request.query_params.get("tag")
        query = Repository.objects.filter(tags__name=tag).order_by("star_count")
        query = pagenator.paginate_queryset(query, request)

        if query is None:
            raise Http404

        return pagenator.get_paginated_response(
            RepositorySerializer(query, many=True).data
        )
