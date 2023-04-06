import os
import shutil

from django.urls import reverse
from git.repo import Repo
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from project.settings import REPO_ROOT
from repositories.models import Repository
from users.models import User


class BranchViewSetTestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create(
            username="user1@user1.com", password="user1_password"
        )
        self.user1_token = RefreshToken.for_user(self.user1).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user1_token}")

        # Remove all files and directories in REPO_ROOT
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

        self.repository = Repository.objects.create(
            name="test_repo",
            user=self.user1,
            path=os.path.join(REPO_ROOT, self.user1.username, "test_repo"),
        )

    def test_create(self):
        data = {
            "branch_name": "test_branch",
            "message": "test_create_branch",
        }
        response = self.client.post(
            reverse("repository-branches", args=[self.repository.id]),
            data,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            os.path.exists(
                os.path.join(
                    self.repository.path, ".git", "refs", "heads", "test_branch"
                )
            )
        )

    def test_destory(self):
        self.test_create()

        data = {"message": "test_delete_branch"}
        repo = Repo(self.repository.path)
        repo.git.checkout("main")

        response = self.client.delete(
            reverse("repository-branch", args=[self.repository.id, "test_branch"]), data
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self.repository.path, ".git", "refs", "heads", "test_branch"
                )
            )
        )

    def test_update(self):
        self.test_create()

        data = {"message": "test_update_branch"}

        response = self.client.put(
            reverse("repository-branch", args=[self.repository.id, "main"]), data
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Repo(self.repository.path).active_branch.name == "main")

    def test_list(self):
        self.test_create()

        response = self.client.get(
            reverse("repository-branches", args=[self.repository.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
