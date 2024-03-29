import os

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from project.settings import REPO_ROOT
from repositories.models import Repository
from stars.models import Star
from users.models import User


class StarViewSetTestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create(
            username="user1@user1.com", password="user1_password"
        )
        self.repository = Repository.objects.create(
            name="test_reop",
            user=self.user1,
            path=os.path.join(REPO_ROOT, self.user1.username, "test_repo"),
        )
        self.user1_token = RefreshToken.for_user(self.user1).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user1_token}")

    def test_create_star(self):
        response = self.client.post(
            reverse("repositories-stars", args=[self.repository.id])
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Star.objects.filter(user=self.user1, repository=self.repository).exists()
        )
        self.repository.refresh_from_db()
        self.assertEqual(self.repository.star_count, 1)

    def test_destroy_star(self):
        Star.objects.create(user=self.user1, repository=self.repository)
        self.repository.star_count = 1
        self.repository.save()

        response = self.client.delete(
            reverse("repositories-stars", args=[self.repository.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            Star.objects.filter(user=self.user1, repository=self.repository).exists()
        )
        self.repository.refresh_from_db()
        self.assertEqual(self.repository.star_count, 0)

    def test_retrieve_stars(self):
        Star.objects.create(user=self.user1, repository=self.repository)
        response = self.client.get(reverse("users-stars", args=[self.user1.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    # no_auth
    def test_create_star_no_auth(self):
        self.client.credentials()
        response = self.client.post(
            reverse("repositories-stars", args=[self.repository.id])
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_destroy_star_no_auth(self):
        self.client.credentials()
        response = self.client.delete(
            reverse("repositories-stars", args=[self.repository.id])
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_stars_no_auth(self):
        self.client.credentials()
        response = self.client.get(reverse("users-stars", args=[self.user1.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
