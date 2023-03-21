from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from repository.models import Repository
from user.models import User


class RepositoryViewSetTestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1", password="user1_password"
        )
        self.user1_token = RefreshToken.for_user(self.user1)

    def test_create_repository(self):
        # Create a new repository
        response = self.client.post(
            "repository-list",
            data={"name": "test_repo"},
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Repository.objects.count(), 1)
        self.assertEqual(Repository.objects.first().name, "test_repo")
        self.assertEqual(Repository.objects.first().owner, self.user1)
