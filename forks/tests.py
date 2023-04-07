import os
import shutil

from django.urls import reverse
from git.repo import Repo
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from forks.models import Fork
from project.settings import REPO_ROOT
from repositories.models import Repository
from users.models import User


class ForkViewSetTestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create(
            username="user1@user1.com", password="user1_password"
        )
        self.user2 = User.objects.create(
            username="user2@user2.com", password="user2_password"
        )
        self.user1_token = RefreshToken.for_user(self.user1).access_token

        for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
            for file in filenames:
                os.remove(os.path.join(dirpath, file))
            for dirname in dirnames:
                shutil.rmtree(os.path.join(dirpath, dirname))

        repo_path = os.path.join(REPO_ROOT, self.user1.username, "test_repo")
        file_path = os.path.join(repo_path, "README.txt")

        repo = Repo.init(repo_path)
        open(file_path, "w").close()
        repo.index.add("*")
        repo.index.commit("initial commit")

        self.repo = Repository.objects.create(
            name="test_repo",
            user=self.user1,
            path=os.path.join(REPO_ROOT, self.user1.username, "test_repo"),
        )

    def test_create(self):
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(reverse("repository-forks", args=[self.repo.id]))
        fork = Fork.objects.get(user=self.user2, source_repository=self.repo)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.repo.source_fork.count(), 1)
        self.assertEqual(fork.user, self.user2)
        self.assertEqual(fork.source_repository, self.repo)
        self.assertTrue(
            os.path.exists(os.path.join(REPO_ROOT, self.user2.username, "test_repo"))
        )
        self.assertEqual(Repository.objects.count(), 2)
        self.assertFalse(Repo(fork.target_repository.path).bare)
        self.assertTrue(
            Repo(fork.target_repository.path).active_branch.name, "new-branch-name"
        )

        self.assertEqual(len(Repo(fork.source_repository.path).branches), 1)

    def test_delete(self):
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(reverse("repository-forks", args=[self.repo.id]))

        response = self.client.delete(reverse("fork-detail", args=[self.repo.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.repo.source_fork.count(), 0)
        self.assertFalse(
            os.path.exists(os.path.join(REPO_ROOT, self.user2.username, "test_repo"))
        )
