import os
import shutil

from django.urls import reverse
from git.repo import Repo
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from fork.models import Fork
from project.settings import REPO_ROOT
from repository.models import Repository
from user.models import User


class ForkViewSetTestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1", password="user1_password"
        )
        self.user1_token = RefreshToken.for_user(self.user1)
        contents = os.listdir(REPO_ROOT)

        for item in contents:
            item_path = os.path.join(REPO_ROOT, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        repo_dir = os.path.join(REPO_ROOT, "test_user", "test_repo")
        file_name = os.path.join(repo_dir, "README.txt")
        repo = Repo.init(repo_dir)
        open(
            file_name,
            "w",
        ).close()
        repo.index.add("*")
        repo.index.commit("initial commit")
        self.repo = Repository.objects.create(
            name="test_repo",
            superuser=self.user1,
            path=os.path.join(REPO_ROOT, "test_user", "test_repo"),
        )

    def test_create(self):
        data = {"repository": self.repo.id}
        response = self.client.post(
            reverse("fork-list"),
            data,
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}",
        )
        fork = Fork.objects.get(user=self.user1, source_repository=self.repo)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.repo.source_fork.count(), 1)
        self.assertEqual(fork.user, self.user1)
        self.assertEqual(fork.source_repository, self.repo)
        self.assertTrue(
            os.path.exists(os.path.join(REPO_ROOT, self.user1.username, "test_repo"))
        )
        self.assertEqual(Repository.objects.count(), 2)
        self.assertTrue(Repo(fork.target_repository.path).bare)
        self.assertTrue(
            Repo(fork.target_repository.path).remotes.source.url.startswith("file://")
        )

    def test_delete(self):
        data = {"repository": self.repo.id}
        response = self.client.post(
            reverse("fork-list"),
            data,
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.repo.source_fork.count(), 1)
        self.assertEqual(self.repo.source_fork.first().user, self.user1)
        self.assertEqual(self.repo.source_fork.first().source_repository, self.repo)

        response = self.client.delete(
            reverse("fork-detail", args=[self.repo.id]),
            HTTP_AUTHORIZATION=f"Bearer {self.user1_token.access_token}",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.repo.source_fork.count(), 0)
        self.assertFalse(
            os.path.exists(os.path.join(REPO_ROOT, self.user1.username, "test_repo"))
        )
