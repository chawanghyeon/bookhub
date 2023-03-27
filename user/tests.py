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

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}"
        )

    def test_retrieve_user(self):
        response = self.client.get(reverse("user-detail", args=[self.user1.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        serializer = UserSerializer(self.user1)
        self.assertEqual(response.data, serializer.data)

    def test_destroy_user(self):
        response = self.client.delete(
            reverse("user-detail", args=[self.user1.id]), {"password": "user1_password"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(username="testuser").exists())

    def test_destroy_user_wrong_password(self):
        response = self.client.delete(
            reverse("user-detail", args=[self.user1.id]), {"password": "wrongpassword"}
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_user_no_auth(self):
        self.client.credentials()
        response = self.client.get(reverse("user-detail", args=[self.user1.id]))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_destroy_user_no_auth(self):
        self.client.credentials()
        response = self.client.delete(
            reverse("user-detail", args=[self.user1.id]), {"password": "user1_password"}
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthViewSetTestCase(APITestCase):
    def setUp(self):
        self.user_data = {
            "username": "testuser@test.com",
            "password": "testuserpassword",
        }

    def test_signup(self):
        response = self.client.post(reverse("auth-signup"), self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            User.objects.filter(username=self.user_data["username"]).exists()
        )

    def test_signin(self):
        User.objects.create_user(**self.user_data)
        signin_data = {
            "username": self.user_data["username"],
            "password": self.user_data["password"],
        }
        response = self.client.post(reverse("auth-signin"), signin_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertIn("access", response.data["token"])
        self.assertIn("refresh", response.data["token"])

    def test_signin_wrong_credentials(self):
        User.objects.create_user(**self.user_data)
        signin_data = {
            "username": self.user_data["username"],
            "password": "wrongpassword",
        }
        response = self.client.post(reverse("auth-signin"), signin_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
