from typing import Optional

from django.contrib.auth import authenticate
from django.db import transaction
from django.http import HttpRequest
from rest_framework import status, viewsets
from rest_framework.response import Response

from user.models import User
from user.serializers import UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def retrieve(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        user_id = request.query_params.get("user", pk) or request.user.id
        if user_id is None:
            user = request.user
        else:
            user = User.objects.get_or_404(id=user_id)

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    @transaction.atomic
    def destroy(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        user = authenticate(
            username=request.user.username, password=request.data.get("password")
        )

        if user is None:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        user.delete()

        return Response(status=status.HTTP_200_OK)
