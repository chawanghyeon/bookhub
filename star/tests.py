from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from repository.models import Repository
from star.models import Star
from user.models import User


class StarViewSetTestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1", password="user1_password"
        )
        self.repository = Repository.objects.create(user=self.user1)
        self.user1_token = RefreshToken.for_user(self.user1)

    def test_create_star(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}"
        )
        response = self.client.post(
            reverse("star-list"), {"repository": self.repository.id}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Star.objects.filter(user=self.user1, repository=self.repository).exists()
        )
        self.repository.refresh_from_db()
        self.assertEqual(self.repository.star_count, 1)

    def test_destroy_star(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}"
        )
        Star.objects.create(user=self.user1, repository=self.repository)
        self.repository.star_count = 1
        self.repository.save()

        response = self.client.delete(reverse("star-detail", args=[self.repository.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            Star.objects.filter(user=self.user1, repository=self.repository).exists()
        )
        self.repository.refresh_from_db()
        self.assertEqual(self.repository.star_count, 0)

    def test_retrieve_stars(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}"
        )
        Star.objects.create(user=self.user1, repository=self.repository)
        response = self.client.get(reverse("star-detail", args=[self.user1.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_star_no_auth(self):
        response = self.client.post(
            reverse("star-list"), {"repository": self.repository.id}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_destroy_star_no_auth(self):
        star = Star.objects.create(user=self.user1, repository=self.repository)
        response = self.client.delete(reverse("star-detail", args=[star.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_stars_no_auth(self):
        Star.objects.create(user=self.user1, repository=self.repository)
        response = self.client.get(reverse("star-detail", args=[self.user1.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
