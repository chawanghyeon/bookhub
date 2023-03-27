import os
import shutil
from typing import Optional

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.http import HttpRequest
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from project.settings import REPO_ROOT
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
            user = User.objects.get(id=user_id)

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    @transaction.atomic
    def destroy(self, request: HttpRequest, pk: Optional[str] = None) -> Response:
        user = authenticate(
            username=request.user.username, password=request.data.get("password")
        )

        if user is None:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        user.delete()

        shutil.rmtree(os.path.join(REPO_ROOT, request.user.username))

        return Response(status=status.HTTP_200_OK)


class AuthViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = tuple()

    @action(detail=False, methods=["post"], url_name="signup")
    def signup(self, request: HttpRequest) -> Response:
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save(password=make_password(request.data.get("password")))

        start_dir = os.path.join(REPO_ROOT, request.data.get("username"))
        os.mkdir(start_dir)

        return Response(status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_name="signin")
    def signin(self, request: HttpRequest) -> Response:
        data = {
            "username": request.data.get("username"),
            "password": request.data.get("password"),
        }

        token = TokenObtainPairSerializer().validate(data)
        user = authenticate(**data)
        serializer = UserSerializer(user)

        return Response(
            {
                "user": serializer.data,
                "message": "Login successfully",
                "token": {"refresh": token["refresh"], "access": token["access"]},
            },
            status=status.HTTP_200_OK,
        )
