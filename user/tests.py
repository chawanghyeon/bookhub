from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from user.models import User
from user.serializers import UserSerializer


class UserViewSetTestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1", password="user1_password"
        )

        self.user1_token = RefreshToken.for_user(self.user1)

    def test_retrieve_user(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}"
        )
        response = self.client.get(reverse("user-detail", args=[self.user1.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        serializer = UserSerializer(self.user1)
        self.assertEqual(response.data, serializer.data)

    def test_retrieve_user_no_auth(self):
        response = self.client.get(reverse("user-detail", args=[self.user1.id]))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_destroy_user(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}"
        )
        response = self.client.delete(
            reverse("user-detail", args=[self.user1.id]), {"password": "user1_password"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(username="testuser").exists())

    def test_destroy_user_wrong_password(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}"
        )
        response = self.client.delete(
            reverse("user-detail", args=[self.user1.id]), {"password": "wrongpassword"}
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_destroy_user_no_auth(self):
        response = self.client.delete(
            reverse("user-detail", args=[self.user1.id]), {"password": "user1_password"}
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
