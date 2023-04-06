from typing import Optional

from django.db import transaction
from django.db.models import F
from django.http import Http404, HttpRequest
from rest_framework import status, viewsets
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response

from repositories.models import Repository
from repositories.serializers import RepositorySerializer
from stars.models import Star
from stars.serializers import StarSerializer


class StarViewSet(viewsets.ModelViewSet):
    queryset = Star.objects.all()
    serializer_class = StarSerializer

    @transaction.atomic
    def create(self, request: HttpRequest) -> Response:
        repository_id = request.data.get("repository")
        serializer = StarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(repository_id=repository_id, user_id=request.user.id)

        Repository.objects.filter(id=repository_id).update(
            star_count=F("star_count") + 1
        )

        return Response(status=status.HTTP_201_CREATED)

    @transaction.atomic
    def destroy(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        Repository.objects.filter(id=pk).update(star_count=F("star_count") - 1)
        Star.objects.filter(repository__id=pk, user__id=request.user.id).delete()

        return Response(status=status.HTTP_200_OK)

    def retrieve(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        user_id = request.query_params.get("user", pk) or request.user.id
        pagenator = CursorPagination()

        query = Repository.objects.filter(star__user__id=user_id)
        query = pagenator.paginate_queryset(query, request)

        if query is None:
            raise Http404

        return pagenator.get_paginated_response(
            RepositorySerializer(query, many=True).data
        )
