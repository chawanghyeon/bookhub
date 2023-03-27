import os
import shutil

from django.urls import reverse
from git.repo import Repo
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from fork.models import Fork
from project.settings import REPO_ROOT
from pullrequest.models import PullRequest
from repository.models import Repository
from user.models import User


class PullRequestViewSetTestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1", password="user1_password"
        )
        self.user2 = User.objects.create_user(
            username="user2", password="user2_password"
        )
        self.user1_token = RefreshToken.for_user(self.user1).access_token
        self.user2_token = RefreshToken.for_user(self.user2).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user2_token}")

        # Remove all files and directories in REPO_ROOT
        for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
            for file in filenames:
                os.remove(os.path.join(dirpath, file))
            for dirname in dirnames:
                shutil.rmtree(os.path.join(dirpath, dirname))

        repo_path = os.path.join(REPO_ROOT, self.user1.username, "test_repo")
        file_path = os.path.join(repo_path, "README.txt")

        # Create a repository
        repo = Repo.init(repo_path)
        open(file_path, "w").close()
        repo.index.add(["*"])
        repo.index.commit("initial commit")
        self.repository = Repository.objects.create(
            name="test_repo",
            superuser=self.user1,
            path=os.path.join(REPO_ROOT, self.user1.username, "test_repo"),
        )

        # Create a fork
        repo = Repo.clone_from(
            self.repository.path,
            os.path.join(REPO_ROOT, self.user2.username, "test_repo"),
        )
        branch_name = "new-branch-name"
        new_branch = repo.create_head(branch_name)
        new_branch.checkout()
        repo.index.add(["*"])
        repo.index.commit("initial commit")
        self.repository2 = Repository.objects.create(
            name="test_repo",
            superuser=self.user2,
            path=os.path.join(REPO_ROOT, self.user2.username, "test_repo"),
        )

        self.fork = Fork.objects.create(
            user=self.user1,
            source_repository=self.repository2,
            target_repository=self.repository,
        )

        self.data = {
            "source_branch": "new-branch-name",
            "target_branch": "main",
            "source_repository": self.fork.source_repository.id,
            "target_repository": self.fork.target_repository.id,
            "title": "test pull request",
            "text": "test pull request",
            "status": "open",
            "user": self.user2.id,
        }

    def test_create_pull_request(self):
        path = self.repository2.path
        with open(os.path.join(path, "README.txt"), "w") as f:
            f.write("test")

        repo = Repo(path)
        repo.index.add(["*"])
        repo.index.commit("test commit")

        response = self.client.post(reverse("pullrequest-list"), self.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PullRequest.objects.count(), 1)
        self.assertEqual(PullRequest.objects.first().title, "test pull request")

    def test_create_pull_request_without_source_branch(self):
        self.data["source_branch"] = ""
        response = self.client.post(reverse("pullrequest-list"), self.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_destory_pull_request(self):
        response = self.client.post(reverse("pullrequest-list"), self.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.delete(reverse("pullrequest-detail", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(PullRequest.objects.count(), 0)

    def test_check_difference(self):
        path = self.repository2.path
        with open(os.path.join(path, "README.txt"), "w") as f:
            f.write("test")

        repo = Repo(path)
        repo.index.add(["*"])
        repo.index.commit("test commit")

        response = self.client.post(reverse("pullrequest-list"), self.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PullRequest.objects.count(), 1)
        self.assertEqual(PullRequest.objects.first().title, "test pull request")

        response = self.client.post(reverse("pullrequest-check", args=[1]), self.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue("test" in str(response.data))

    def test_approve_pull_request(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user1_token}")
        path = self.repository2.path

        with open(os.path.join(path, "README.txt"), "w") as f:
            f.write("test")

        repo = Repo(path)
        repo.index.add(["*"])
        repo.index.commit("test commit")

        response = self.client.post(reverse("pullrequest-list"), self.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PullRequest.objects.count(), 1)
        self.assertEqual(PullRequest.objects.first().title, "test pull request")

        response = self.client.post(reverse("pullrequest-approve", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(PullRequest.objects.first().status, "merged")
        with open(os.path.join(self.repository.path, "README.txt"), "r") as f:
            self.assertEqual(f.read(), "test")

    def test_approve_pull_request_with_another_user(self):
        response = self.client.post(reverse("pullrequest-list"), self.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.post(reverse("pullrequest-approve", args=[1]), data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_approve_pull_request_with_conflict(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user1_token}")

        response = self.client.post(reverse("pullrequest-list"), self.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        path = self.repository2.path
        with open(os.path.join(path, "README.txt"), "w") as f:
            f.write("test")

        repo = Repo(path)
        repo.index.add(["*"])
        repo.index.commit("test commit")

        with open(os.path.join(self.repository.path, "README.txt"), "w") as f:
            f.write("asdfasdf")
        reop = Repo(self.repository.path)
        reop.index.add(["*"])
        reop.index.commit("test commit")

        response = self.client.post(reverse("pullrequest-approve", args=[1]), data={})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_pull_request(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user1_token}")

        response = self.client.post(reverse("pullrequest-list"), self.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.post(reverse("pullrequest-reject", args=[1]), data={})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(PullRequest.objects.first().status, "closed")

    def test_resolve_conflict(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user1_token}")

        response = self.client.post(reverse("pullrequest-list"), self.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        with open(os.path.join(self.repository2.path, "README.txt"), "w") as f:
            f.write("test")
        repo = Repo(self.repository2.path)
        repo.index.add(["*"])
        repo.index.commit("test commit")

        with open(os.path.join(self.repository.path, "README.txt"), "w") as f:
            f.write("asdfasdf")
        reop = Repo(self.repository.path)
        reop.index.add(["*"])
        reop.index.commit("test commit")

        response = self.client.post(reverse("pullrequest-approve", args=[1]), data={})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(
            reverse("pullrequest-resolve", args=[1]),
            data={"choice": "REMOTE", "filename": "README.txt"},
        )
        self.assertEqual(response.data["file"], "asdfasdf")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
